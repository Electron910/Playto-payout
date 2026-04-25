
# Playto Payout Engine

A minimal payout engine for Indian agencies and freelancers to collect international
payments. Merchants accumulate balance from customer payments (USD → INR), request
payouts to their Indian bank accounts, and track payout status in real time.

Built for the Playto engineering challenge.

---

## Live Demo

| Service | URL |
|---|---|
| Dashboard | https://playto-payout-lndv.onrender.com |
| API | https://playto-backend-dsql.onrender.com/api/v1/merchants/ |

> First request may take ~30 seconds. Render free tier sleeps after 15 min of inactivity.

---

## Tech Stack

| Layer | Tech |
|---|---|
| Backend | Django 5.1 + Django REST Framework |
| Frontend | React 18 + Tailwind CSS |
| Database | PostgreSQL 16 (Neon) |
| Background Jobs | Celery 5.4 (SQLAlchemy broker, no Redis) |
| Scheduler | Celery Beat with django-celery-beat |
| Hosting | Render (Web Service + Static Site) |

---

## Features

- **Merchant Ledger** — Balance derived from ledger entries (credits, debits, holds, releases). Never stored as a column. Always computed from the database.
- **Payout Request API** — `POST /api/v1/payouts/` with idempotency key header. Creates payout, holds funds atomically.
- **Payout Processor** — Celery worker picks up pending payouts, simulates bank settlement (70% success, 20% fail, 10% hang).
- **Retry Logic** — Stuck payouts retried with exponential backoff. Max 3 attempts, then auto-fail with fund release.
- **State Machine** — `pending → processing → completed/failed`. Backward transitions blocked.
- **Concurrency Safe** — PostgreSQL row-level locking prevents double-spend on simultaneous requests.
- **Idempotent API** — Duplicate requests with same key return cached response. Keys scoped per merchant, expire after 24 hours.
- **Merchant Dashboard** — React UI with live polling. Balance cards, payout form, payout history, ledger table, integrity check.

---

## Payout Lifecycle

```
Customer pays merchant (seeded/simulated)
         │
         ▼
   ┌─────────────┐
   │   CREDIT     │  Ledger entry: credit
   │   recorded   │
   └─────┬───────┘
         │
         ▼
   Merchant requests payout
         │
         ▼
   ┌─────────────┐
   │   HOLD       │  Ledger entry: hold
   │   created    │  Payout status: pending
   └─────┬───────┘
         │
         ▼  (Celery picks up)
   ┌─────────────┐
   │  PROCESSING  │  Payout status: processing
   └─────┬───────┘
         │
    ┌────┴─────┐
    ▼          ▼
 SUCCESS    FAILURE
    │          │
    ▼          ▼
 RELEASE    RELEASE     Ledger entry: release (both paths)
 + DEBIT      │         Ledger entry: debit (success only)
    │          │
    ▼          ▼
 completed   failed     Payout final status
```

---

## Run Locally

### Prerequisites

- Docker and Docker Compose installed
- Ports 3000, 5432, 8000 available

### Start

```bash
git clone https://github.com/your-username/playto-payout-engine.git
cd playto-payout-engine
docker-compose up --build
```

Docker handles everything:
- PostgreSQL starts
- Django runs migrations and seeds 3 merchants
- Celery worker + beat starts processing payouts
- React frontend starts on Vite dev server

### Open

| Service | URL |
|---|---|
| Dashboard | http://localhost:3000 |
| API | http://localhost:8000/api/v1/ |

---

## Deploy to Render (Free)

Total cost: **$0**. Two Render services + one Neon database.

### Architecture

```
Render
├── playto-backend    → Web Service (free)    → Django + Gunicorn + Celery
└── playto-frontend   → Static Site (free)    → React build

Neon
└── playto            → PostgreSQL (free)     → single database for everything
```

### Step 1: Create Database on Neon

1. Go to https://neon.tech → Sign up → **New Project**
2. Name: `playto`, Region: `US East`
3. Copy the connection string

### Step 2: Generate Django Secret Key

Run in any terminal:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(50))"
```

Save the output.

### Step 3: Create Backend on Render

1. Go to https://dashboard.render.com
2. **New** → **Web Service** → Connect GitHub repo
3. Configure:

```
Name:            playto-backend
Root Directory:  backend
Runtime:         Python 3
Build Command:   chmod +x build.sh start.sh && ./build.sh
Start Command:   bash start.sh
Plan:            Free
```

4. Environment Variables:

| Key | Value |
|---|---|
| `DJANGO_SECRET_KEY` | Your generated key from Step 2 |
| `DEBUG` | `False` |
| `DATABASE_URL` | Your Neon connection string from Step 1 |
| `ALLOWED_HOSTS` | `.onrender.com` |
| `PYTHON_VERSION` | `3.12.0` |

5. Click **Create Web Service**
6. Wait for deploy. Copy the URL (like `https://playto-backend-xxxx.onrender.com`)

### Step 4: Create Frontend on Render

1. **New** → **Static Site** → Connect same repo
2. Configure:

```
Name:              playto-frontend
Root Directory:    frontend
Build Command:     npm install && npm run build
Publish Directory: dist
```

3. Environment Variable:

| Key | Value |
|---|---|
| `VITE_API_URL` | `https://playto-backend-xxxx.onrender.com` (your backend URL) |

4. Go to **Redirects/Rewrites** and add:

```
Source:      /*
Destination: /index.html
Action:      Rewrite
```

5. Click **Create Static Site**

### Step 5: Verify

```bash
curl https://playto-backend-xxxx.onrender.com/api/v1/merchants/
```

Should return 3 merchants. Open the frontend URL in browser.

---

## Seeded Merchants

The seed command creates 3 merchants with credit history:

| Merchant | Balance | Bank |
|---|---|---|
| Priya Design Studio | ₹1,28,000.00 | HDFC Bank |
| Raj Software Solutions | ₹2,50,000.00 | ICICI Bank |
| Ananya Content Agency | ₹74,000.00 | State Bank of India |

---

## API Reference

All endpoints require `X-Merchant-Id` header (UUID of the merchant).

### List Merchants

```
GET /api/v1/merchants/
```

No headers required. Returns all merchants with bank accounts.

### Get Balance

```
GET /api/v1/balance/
X-Merchant-Id: <merchant-uuid>
```

Returns available balance, held balance, total credits, total debits. All in paise.

### Get Ledger

```
GET /api/v1/ledger/
X-Merchant-Id: <merchant-uuid>
```

Returns last 50 ledger entries.

### Create Payout

```
POST /api/v1/payouts/
X-Merchant-Id: <merchant-uuid>
Idempotency-Key: <unique-uuid>
Content-Type: application/json

{
  "amount_paise": 100000,
  "bank_account_id": "<bank-account-uuid>"
}
```

Creates payout in pending state. Holds funds immediately.
Second call with same idempotency key returns same response. No duplicate.

### List Payouts

```
GET /api/v1/payouts/list/
X-Merchant-Id: <merchant-uuid>
```

### Get Single Payout

```
GET /api/v1/payouts/<payout-uuid>/
X-Merchant-Id: <merchant-uuid>
```

### List Bank Accounts

```
GET /api/v1/bank-accounts/
X-Merchant-Id: <merchant-uuid>
```

### Integrity Check

```
GET /api/v1/integrity/
X-Merchant-Id: <merchant-uuid>
```

Verifies `credits - debits - held = available`. Returns `all_ok: true/false`.

---

## Testing Concurrency

Two simultaneous ₹60 payouts against ₹100 balance. Only one should succeed.

```bash
export MERCHANT_ID="<merchant-uuid>"
export BANK_ACCOUNT_ID="<bank-account-uuid>"
export API="https://playto-backend-xxxx.onrender.com"

curl -X POST $API/api/v1/payouts/ \
  -H "Content-Type: application/json" \
  -H "X-Merchant-Id: $MERCHANT_ID" \
  -H "Idempotency-Key: $(python3 -c 'import uuid; print(uuid.uuid4())')" \
  -d "{\"amount_paise\": 6000, \"bank_account_id\": \"$BANK_ACCOUNT_ID\"}" &

curl -X POST $API/api/v1/payouts/ \
  -H "Content-Type: application/json" \
  -H "X-Merchant-Id: $MERCHANT_ID" \
  -H "Idempotency-Key: $(python3 -c 'import uuid; print(uuid.uuid4())')" \
  -d "{\"amount_paise\": 6000, \"bank_account_id\": \"$BANK_ACCOUNT_ID\"}" &

wait
```

One returns 201, the other returns 400.

---

## Testing Idempotency

Same key twice. Same response both times. No duplicate payout.

```bash
export KEY="550e8400-e29b-41d4-a716-446655440000"

curl -X POST $API/api/v1/payouts/ \
  -H "Content-Type: application/json" \
  -H "X-Merchant-Id: $MERCHANT_ID" \
  -H "Idempotency-Key: $KEY" \
  -d "{\"amount_paise\": 5000, \"bank_account_id\": \"$BANK_ACCOUNT_ID\"}"

# Same request again
curl -X POST $API/api/v1/payouts/ \
  -H "Content-Type: application/json" \
  -H "X-Merchant-Id: $MERCHANT_ID" \
  -H "Idempotency-Key: $KEY" \
  -d "{\"amount_paise\": 5000, \"bank_account_id\": \"$BANK_ACCOUNT_ID\"}"
```

---

## Project Structure

```
playto-payout-engine/
├── docker-compose.yml
├── README.md
├── EXPLAINER.md
├── AI_AUDIT.md
│
├── backend/
│   ├── Dockerfile.local        ← for local Docker dev
│   ├── manage.py
│   ├── requirements.txt
│   ├── build.sh                ← Render build script
│   ├── start.sh                ← Render start script (Django + Celery)
│   ├── wait_for_db.py          ← local Docker helper
│   ├── entrypoint.sh           ← local Docker entrypoint
│   ├── worker_entrypoint.sh    ← local Docker celery worker
│   ├── beat_entrypoint.sh      ← local Docker celery beat
│   ├── playto/
│   │   ├── __init__.py
│   │   ├── celery.py
│   │   ├── settings.py
│   │   ├── urls.py
│   │   └── wsgi.py
│   └── ledger/
│       ├── __init__.py
│       ├── models.py
│       ├── serializers.py
│       ├── views.py
│       ├── urls.py
│       ├── admin.py
│       ├── tasks.py
│       ├── migrations/
│       │   ├── __init__.py
│       │   └── 0001_initial.py
│       └── management/
│           ├── __init__.py
│           └── commands/
│               ├── __init__.py
│               └── seed_merchants.py
│
└── frontend/
    ├── Dockerfile
    ├── package.json
    ├── vite.config.js
    ├── tailwind.config.js
    ├── postcss.config.js
    ├── index.html
    └── src/
        ├── main.jsx
        ├── App.jsx
        ├── index.css
        ├── api/
        │   └── client.js
        ├── components/
        │   ├── Dashboard.jsx
        │   ├── BalanceCard.jsx
        │   ├── PayoutForm.jsx
        │   ├── PayoutHistory.jsx
        │   ├── LedgerTable.jsx
        │   ├── MerchantSelector.jsx
        │   └── StatusBadge.jsx
        └── hooks/
            └── usePolling.js
```

---

## Design Decisions

| Decision | Why |
|---|---|
| Balance derived, not stored | Single source of truth. No stale cache. Integrity check is trivial. |
| Paise as BigIntegerField | No floating point. No rounding. Exact integer math at DB level. |
| Hold/release pattern | Makes pending payouts visible to balance calculation inside transactions. |
| select_for_update on Merchant row | Serializes all payouts per merchant. Simple, correct. |
| Idempotency record inside transaction | If payout creation rolls back, idempotency record rolls back too. |
| F-expression for retry_count | `F('retry_count') + 1` is atomic at DB level. No race between workers. |
| SQLAlchemy broker instead of Redis | One less service. Free deployment. Same correctness guarantees. |
| Combined Celery + Django in one process | Free tier deployment. No separate worker service needed. |

---

## What I'd Add in Production

- JWT authentication instead of X-Merchant-Id header
- Webhook callbacks for payout status changes
- Rate limiting on payout endpoint
- Audit log with IP, user agent, timestamp for every state change
- Dead letter queue for permanently failed payouts
- Redis broker for better Celery performance
- Prometheus metrics for payout success/failure rates
- Sentry for error tracking
- Separate Celery worker service

---

## Useful Commands (Local Docker)

```bash
# Start everything
docker-compose up --build

# Stop everything
docker-compose down

# Full reset (wipes database)
docker-compose down -v
docker-compose up --build

# View logs
docker-compose logs -f backend
docker-compose logs -f celery_worker

# Django shell
docker-compose exec backend python manage.py shell
```
```
