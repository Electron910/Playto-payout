from rest_framework import serializers
from .models import Merchant, BankAccount, LedgerEntry, Payout


class BankAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankAccount
        fields = ['id', 'account_number', 'ifsc_code', 'account_holder_name', 'bank_name']


class MerchantSerializer(serializers.ModelSerializer):
    bank_accounts = BankAccountSerializer(many=True, read_only=True)

    class Meta:
        model = Merchant
        fields = ['id', 'name', 'email', 'bank_accounts', 'created_at']


class LedgerEntrySerializer(serializers.ModelSerializer):
    payout_id = serializers.UUIDField(source='payout.id', read_only=True, allow_null=True)

    class Meta:
        model = LedgerEntry
        fields = ['id', 'entry_type', 'amount_paise', 'description', 'payout_id', 'created_at']


class PayoutSerializer(serializers.ModelSerializer):
    bank_account_details = BankAccountSerializer(source='bank_account', read_only=True)

    class Meta:
        model = Payout
        fields = [
            'id', 'merchant_id', 'amount_paise', 'bank_account_id',
            'bank_account_details', 'status', 'retry_count', 'max_retries',
            'processing_started_at', 'completed_at', 'failed_at',
            'failure_reason', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'status', 'retry_count', 'processing_started_at',
            'completed_at', 'failed_at', 'failure_reason', 'created_at', 'updated_at',
        ]


class PayoutRequestSerializer(serializers.Serializer):
    amount_paise = serializers.IntegerField(min_value=100)
    bank_account_id = serializers.UUIDField()

    def validate_amount_paise(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be positive.")
        return value


class BalanceSerializer(serializers.Serializer):
    available_balance_paise = serializers.IntegerField()
    held_balance_paise = serializers.IntegerField()
    total_credits_paise = serializers.IntegerField()
    total_debits_paise = serializers.IntegerField()