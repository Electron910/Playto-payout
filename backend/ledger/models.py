import uuid
from django.db import models
from django.utils import timezone


class Merchant(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'merchants'

    def __str__(self):
        return self.name


class BankAccount(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    merchant = models.ForeignKey(Merchant, on_delete=models.CASCADE, related_name='bank_accounts')
    account_number = models.CharField(max_length=20)
    ifsc_code = models.CharField(max_length=11)
    account_holder_name = models.CharField(max_length=255)
    bank_name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'bank_accounts'

    def __str__(self):
        return f"{self.bank_name} - {self.account_number[-4:]}"


class LedgerEntry(models.Model):
    CREDIT = 'credit'
    DEBIT = 'debit'
    HOLD = 'hold'
    RELEASE = 'release'

    ENTRY_TYPES = [
        (CREDIT, 'Credit'),
        (DEBIT, 'Debit'),
        (HOLD, 'Hold'),
        (RELEASE, 'Release'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    merchant = models.ForeignKey(Merchant, on_delete=models.CASCADE, related_name='ledger_entries')
    entry_type = models.CharField(max_length=10, choices=ENTRY_TYPES)
    amount_paise = models.BigIntegerField()
    description = models.CharField(max_length=500, blank=True)
    payout = models.ForeignKey(
        'Payout', on_delete=models.SET_NULL, null=True, blank=True, related_name='ledger_entries'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ledger_entries'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['merchant', 'entry_type']),
            models.Index(fields=['merchant', '-created_at']),
        ]

    def __str__(self):
        return f"{self.entry_type}: {self.amount_paise} paise"


class Payout(models.Model):
    PENDING = 'pending'
    PROCESSING = 'processing'
    COMPLETED = 'completed'
    FAILED = 'failed'

    STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (PROCESSING, 'Processing'),
        (COMPLETED, 'Completed'),
        (FAILED, 'Failed'),
    ]

    VALID_TRANSITIONS = {
        PENDING: {PROCESSING},
        PROCESSING: {COMPLETED, FAILED},
    }

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    merchant = models.ForeignKey(Merchant, on_delete=models.CASCADE, related_name='payouts')
    amount_paise = models.BigIntegerField()
    bank_account = models.ForeignKey(BankAccount, on_delete=models.PROTECT, related_name='payouts')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)
    idempotency_key = models.CharField(max_length=255, db_index=True)
    retry_count = models.IntegerField(default=0)
    max_retries = models.IntegerField(default=3)
    processing_started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    failure_reason = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'payouts'
        constraints = [
            models.UniqueConstraint(
                fields=['merchant', 'idempotency_key'],
                name='unique_merchant_idempotency_key',
            ),
        ]
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'processing_started_at']),
            models.Index(fields=['merchant', '-created_at']),
        ]

    def can_transition_to(self, new_status):
        allowed = self.VALID_TRANSITIONS.get(self.status, set())
        return new_status in allowed

    def __str__(self):
        return f"Payout {self.id} - {self.status}"


class IdempotencyRecord(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    merchant = models.ForeignKey(Merchant, on_delete=models.CASCADE, related_name='idempotency_records')
    idempotency_key = models.CharField(max_length=255)
    response_status_code = models.IntegerField()
    response_body = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        db_table = 'idempotency_records'
        constraints = [
            models.UniqueConstraint(
                fields=['merchant', 'idempotency_key'],
                name='unique_idempotency_per_merchant',
            ),
        ]
        indexes = [
            models.Index(fields=['expires_at']),
        ]

    def is_expired(self):
        return timezone.now() > self.expires_at