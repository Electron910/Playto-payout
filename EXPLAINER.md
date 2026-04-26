

### `EXPLAINER.md`


## 1. The Ledger

### Balance Calculation Query

```python
def compute_balance(merchant):
    aggregation = LedgerEntry.objects.filter(merchant=merchant).aggregate(
        total_credits=Sum('amount_paise', filter=Q(entry_type=LedgerEntry.CREDIT)),
        total_debits=Sum('amount_paise', filter=Q(entry_type=LedgerEntry.DEBIT)),
        total_holds=Sum('amount_paise', filter=Q(entry_type=LedgerEntry.HOLD)),
        total_releases=Sum('amount_paise', filter=Q(entry_type=LedgerEntry.RELEASE)),
    )
    total_credits = aggregation['total_credits'] or 0
    total_debits = aggregation['total_debits'] or 0
    total_holds = aggregation['total_holds'] or 0
    total_releases = aggregation['total_releases'] or 0

    held_balance = total_holds - total_releases
    available_balance = total_credits - total_debits - held_balance

    return {
        'available_balance_paise': available_balance,
        'held_balance_paise': held_balance,
        'total_credits_paise': total_credits,
        'total_debits_paise': total_debits,
    }
```

This translates to a single SQL query:

```sql
SELECT
  SUM(amount_paise) FILTER (WHERE entry_type = 'credit') AS total_credits,
  SUM(amount_paise) FILTER (WHERE entry_type = 'debit') AS total_debits,
  SUM(amount_paise) FILTER (WHERE entry_type = 'hold') AS total_holds,
  SUM(amount_paise) FILTER (WHERE entry_type = 'release') AS total_releases
FROM ledger_entries
WHERE merchant_id = %s;
```

### Why four entry types instead of just credit and debit?

    With only credit and debit a pending payout has no value in the ledger. Two requests
arriving at the same time and both see the full balance and both pass the check. The hold
entry solves this. When a payout is requested, a hold entry is created immediately inside
the same transaction. The next request's balance query sees that hold and gets a reduced
available balance.

The release entry removes the hold when the payout finishes either completed or failed.
If completed, a debit entry is also written. If failed, just the release, so the money
goes back to available.

I have never stored balance in a column. It's always derived from the ledger. One source of truth.
No sync issues. The integrity check endpoint verifies `credits - debits - held = available`
on every call.

---

## 2. The Lock

```python
# From views.py — PayoutCreateView.post

with transaction.atomic():
    merchant_locked = Merchant.objects.select_for_update().get(id=merchant.id)

    balance = compute_balance(merchant_locked)
    available = balance['available_balance_paise']

    if amount_paise > available:
        # reject
        return Response(...)

    payout = Payout.objects.create(...)

    LedgerEntry.objects.create(
        merchant=merchant_locked,
        entry_type=LedgerEntry.HOLD,
        amount_paise=amount_paise,
        ...
    )
```

`select_for_update()` issues a `SELECT ... FOR UPDATE` in PostgreSQL. This acquires a
row level exclusive lock on the row. Any other transaction trying to
`select_for_update` on the same merchant row blocks until the first one commits or
rolls back.

So if merchant has ₹100 and two ₹60 requests arrive at the same time:

1. Request A locks the merchant row, reads balance = ₹100, creates hold of ₹60, commits. Balance is now ₹40.
2. Request B was blocked at `select_for_update`. Now it proceeds, reads balance = ₹40, tries ₹60, gets rejected.

The key detail: the balance check and the hold write are inside the same `transaction.atomic()`.
The lock is held for the entire block. There's no gap between "check" and "deduct" where
another request could sneak in.

I use the merchant row as the lock target rather than trying to lock ledger entries.
Simpler and every payout for a merchant goes through the same lock.

---

## 3. The Idempotency

### How does the system know it has seen a key before?

There's an `IdempotencyRecord` table with a unique constraint on `(merchant_id, idempotency_key)`.

```python
existing_record = IdempotencyRecord.objects.filter(
    merchant=merchant,
    idempotency_key=idempotency_key,
).first()

if existing_record:
    if existing_record.is_expired():
        existing_record.delete()
    else:
        return Response(
            existing_record.response_body,
            status=existing_record.response_status_code,
        )
```

When a payout is created successfully it store the full response 
in this table. Next time the same key comes in, it will return the cached response without
creating anything.

Keys are scoped per merchant. Keys expire after 24 hours. A Celery task cleans up
expired ones every hour.

### What if the first request is still in flight?

The `Payout` model also has a unique constraint on `(merchant_id, idempotency_key)`:

```python
class Meta:
    constraints = [
        models.UniqueConstraint(
            fields=['merchant', 'idempotency_key'],
            name='unique_merchant_idempotency_key',
        ),
    ]
```

If request A is inside the `transaction.atomic()` block and
request B arrives with the same key:

- Request B won't find an `IdempotencyRecord` because A hasn't committed.
- Request B enters the atomic block, hits `select_for_update` on the merchant and blocks because A holds the lock.
- A commits. The idempotency record and payout are now visible.
- B unblocks, goes back to check the idempotency table, but waits as B already passed that check.
- B tries to create a payout with the same idempotency key. The unique constraint on the Payout table stops it. The transaction rolls back. The exception handler returns a 500.

In practice, the `select_for_update` serializes all payout requests for the same merchant
so the second request almost always finds the idempotency record from the first. The DB
constraint is the safety net.

---

## 4. The State Machine

### Where is failed-to-completed blocked?

In the `Payout` model:

```python
VALID_TRANSITIONS = {
    PENDING: {PROCESSING},
    PROCESSING: {COMPLETED, FAILED},
}

def can_transition_to(self, new_status):
    allowed = self.VALID_TRANSITIONS.get(self.status, set())
    return new_status in allowed
```

`FAILED` is not a key in `VALID_TRANSITIONS`. So `self.VALID_TRANSITIONS.get('failed', set())`
returns an empty set. `'completed' in set()` is `False`. Transition denied.

Every state change function checks this before proceeding:

```python
# From tasks.py — complete_payout
def complete_payout(payout_id):
    with transaction.atomic():
        payout = Payout.objects.select_for_update().get(id=payout_id)

        if not payout.can_transition_to(Payout.COMPLETED):
            logger.warning(f"Cannot complete payout {payout_id} from state {payout.status}.")
            return
        ...
```

Same check is there in `fail_payout` and `process_single_payout`. The payout row is locked
with `select_for_update` before the check, so no two workers can transition the same
payout simultaneously.

Illegal transitions that are blocked:
- `failed → completed` — VALID_TRANSITIONS has no entry for `failed`
- `completed → pending` — VALID_TRANSITIONS has no entry for `completed`
- `completed → failed` — same reason
- `pending → completed` — `PENDING` only allows `{PROCESSING}`

---

## 5. The AI Audit

### Bug 1: Balance check without database locking

When I asked it to write the payout creation logic, it gave me this:

```python
# What it gave
def post(self, request):
    merchant = get_merchant(request)
    balance = compute_balance(merchant)

    if balance['available_balance_paise'] >= amount_paise:
        payout = Payout.objects.create(...)
        LedgerEntry.objects.create(entry_type='hold', ...)
        return Response(...)
    else:
        return Response({'error': 'Insufficient balance'}, status=400)
```

No `transaction.atomic()`. No `select_for_update()`. The balance check and the hold
creation are not in the same transaction.

Two requests hit this at the same time. Both read balance = ₹100. Both see enough for
₹60. Both create holds. Merchant now has ₹120 held against ₹100. Money came from nowhere.

What I replaced it with:

```python
# What I wrote
with transaction.atomic():
    merchant_locked = Merchant.objects.select_for_update().get(id=merchant.id)
    balance = compute_balance(merchant_locked)

    if amount_paise > balance['available_balance_paise']:
        return Response(...)

    Payout.objects.create(...)
    LedgerEntry.objects.create(entry_type='hold', ...)
```

Three things changed:
1. Wrapped in `transaction.atomic()` so the read and write are one unit.
2. Added `select_for_update()` to lock the merchant row. Second request waits.
3. Moved the balance check inside the lock so it reads after acquiring the lock, not before.

This is a textbook time of check to time of use bug. The AI treated it like
normal application logic. In a payment system, the gap between checking and writing
is where money gets created or destroyed.

---

### Bug 2: UUID objects not JSON serializable in idempotency storage

AI wrote the idempotency record creation like this:

```python
# What it generated
payout_data = PayoutSerializer(payout).data
response_body = payout_data  # contains UUID objects

IdempotencyRecord.objects.create(
    merchant=merchant,
    idempotency_key=idempotency_key,
    response_status_code=201,
    response_body=response_body,  # crashes here
    ...
)
```

`PayoutSerializer(payout).data` returns a `ReturnDict` where fields like `id`,
`merchant_id`, `bank_account_id` are Python `UUID` objects. When Django tries to
save this into PostgreSQL's `JSONField`, the JSON encoder doesn't know how to
serialize `UUID`. The request blows up with `Object of type UUID is not JSON serializable`.

This didn't show up until I actually submitted a payout from the frontend. The AI
tested nothing it just assumed serializer output was safe and it's not.

What I replaced it with:

```python
# What I gave
from rest_framework.renderers import JSONRenderer
import json

def serialize_to_json_safe(serializer_data):
    json_bytes = JSONRenderer().render(serializer_data)
    return json.loads(json_bytes)

# In the view:
payout_data = PayoutSerializer(payout).data
response_body = serialize_to_json_safe(payout_data)
```

`JSONRenderer` knows how to handle UUIDs, datetimes and all the DRF field types.
It converts everything to a JSON byte string. `json.loads` turns it back into a
plain dict with all values as basic Python types — strings, ints, nulls. That dict
is safe for `JSONField`.

---

### Bug 3: Celery tasks flooding logs even with no work to do

AI wrote the periodic tasks without any early exit logic:

```python
# What AI generated (noisy)
@shared_task(name='ledger.tasks.process_pending_payouts')
def process_pending_payouts():
    pending_payouts = Payout.objects.filter(status=Payout.PENDING)
    for payout in pending_payouts:
        process_single_payout.delay(str(payout.id))
```

With beat running every 5 seconds, Celery logged `Task succeeded` every 5 seconds
even when there were zero payouts. The terminal was a full of noise. I couldn't
spot real events in the log. On top of that each empty run still hit the database
with a query for nothing.

What I replaced it with:

```python
@shared_task(name='ledger.tasks.process_pending_payouts')
def process_pending_payouts():
    pending_payouts = list(Payout.objects.filter(status=Payout.PENDING))

    if not pending_payouts:
        return

    logger.info(f"Found {len(pending_payouts)} pending payouts to process.")

    for payout in pending_payouts:
        process_single_payout.delay(str(payout.id))
```

Three changes:
1. Added `if not pending_payouts: return` so it exits silently when there's nothing.
2. Wrapped queryset in `list()` to evaluate it once and check the length.
3. Only logs when there's actual work to do.

Also changed the schedule from 5s to 10s for pending payouts and 10s to 30s for retry
checks. Fast enough to feel responsive, slow enough to not spam.

Same fix applied to `retry_stuck_payouts` and `cleanup_expired_idempotency_keys`.

---

### Bug 4: Vite proxy pointing to localhost instead of Docker service name

AI configured the frontend proxy like this:

```javascript
proxy: {
  '/api': {
    target: 'http://localhost:8000',
    changeOrigin: true,
  },
},
```

This works on bare metal where everything runs on the same machine. Inside Docker,
each service is its own container with its own network namespace. `localhost` inside
the frontend container points to the frontend container itself, not the backend.
Every API call failed with `ECONNREFUSED`.

What I replaced it with:

```javascript
// What gave
proxy: {
  '/api': {
    target: 'http://backend:8000',
    changeOrigin: true,
  },
},
```

Docker Compose puts all services on the same network and sets up DNS so that the
service name resolves to the correct container IP. `backend` is the service name from
`docker-compose.yml`, so `http://backend:8000` reaches the Django container.

This is the kind of bug that works perfectly on the developer's laptop and breaks
in every other environment. AI defaults to localhost because most tutorials use it.
Docker networking is a different world.
```
