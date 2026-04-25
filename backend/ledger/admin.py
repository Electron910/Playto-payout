from django.contrib import admin
from .models import Merchant, BankAccount, LedgerEntry, Payout, IdempotencyRecord

@admin.register(Merchant)
class MerchantAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'created_at']

@admin.register(BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    list_display = ['merchant', 'bank_name', 'account_number', 'ifsc_code']

@admin.register(LedgerEntry)
class LedgerEntryAdmin(admin.ModelAdmin):
    list_display = ['merchant', 'entry_type', 'amount_paise', 'created_at']
    list_filter = ['entry_type']

@admin.register(Payout)
class PayoutAdmin(admin.ModelAdmin):
    list_display = ['id', 'merchant', 'amount_paise', 'status', 'retry_count', 'created_at']
    list_filter = ['status']

@admin.register(IdempotencyRecord)
class IdempotencyRecordAdmin(admin.ModelAdmin):
    list_display = ['merchant', 'idempotency_key', 'response_status_code', 'created_at', 'expires_at']