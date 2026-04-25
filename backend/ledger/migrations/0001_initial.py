import uuid
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Merchant',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
                ('email', models.EmailField(max_length=254, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'db_table': 'merchants',
            },
        ),
        migrations.CreateModel(
            name='BankAccount',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('account_number', models.CharField(max_length=20)),
                ('ifsc_code', models.CharField(max_length=11)),
                ('account_holder_name', models.CharField(max_length=255)),
                ('bank_name', models.CharField(max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('merchant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='bank_accounts', to='ledger.merchant')),
            ],
            options={
                'db_table': 'bank_accounts',
            },
        ),
        migrations.CreateModel(
            name='Payout',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('amount_paise', models.BigIntegerField()),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('processing', 'Processing'), ('completed', 'Completed'), ('failed', 'Failed')], default='pending', max_length=20)),
                ('idempotency_key', models.CharField(db_index=True, max_length=255)),
                ('retry_count', models.IntegerField(default=0)),
                ('max_retries', models.IntegerField(default=3)),
                ('processing_started_at', models.DateTimeField(blank=True, null=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('failed_at', models.DateTimeField(blank=True, null=True)),
                ('failure_reason', models.CharField(blank=True, max_length=500)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('bank_account', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='payouts', to='ledger.bankaccount')),
                ('merchant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='payouts', to='ledger.merchant')),
            ],
            options={
                'db_table': 'payouts',
                'ordering': ['-created_at'],
                'indexes': [
                    models.Index(fields=['status', 'processing_started_at'], name='payouts_status_proc_idx'),
                    models.Index(fields=['merchant', '-created_at'], name='payouts_merchant_created_idx'),
                ],
                'constraints': [
                    models.UniqueConstraint(fields=['merchant', 'idempotency_key'], name='unique_merchant_idempotency_key'),
                ],
            },
        ),
        migrations.CreateModel(
            name='LedgerEntry',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('entry_type', models.CharField(choices=[('credit', 'Credit'), ('debit', 'Debit'), ('hold', 'Hold'), ('release', 'Release')], max_length=10)),
                ('amount_paise', models.BigIntegerField()),
                ('description', models.CharField(blank=True, max_length=500)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('merchant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ledger_entries', to='ledger.merchant')),
                ('payout', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='ledger_entries', to='ledger.payout')),
            ],
            options={
                'db_table': 'ledger_entries',
                'ordering': ['-created_at'],
                'indexes': [
                    models.Index(fields=['merchant', 'entry_type'], name='ledger_merchant_type_idx'),
                    models.Index(fields=['merchant', '-created_at'], name='ledger_merchant_created_idx'),
                ],
            },
        ),
        migrations.CreateModel(
            name='IdempotencyRecord',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('idempotency_key', models.CharField(max_length=255)),
                ('response_status_code', models.IntegerField()),
                ('response_body', models.JSONField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('expires_at', models.DateTimeField()),
                ('merchant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='idempotency_records', to='ledger.merchant')),
            ],
            options={
                'db_table': 'idempotency_records',
                'indexes': [
                    models.Index(fields=['expires_at'], name='idempotency_expires_idx'),
                ],
                'constraints': [
                    models.UniqueConstraint(fields=['merchant', 'idempotency_key'], name='unique_idempotency_per_merchant'),
                ],
            },
        ),
    ]