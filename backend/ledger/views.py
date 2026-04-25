import json

from datetime import timedelta

from django.db import transaction
from django.db.models import Sum, Q
from django.utils import timezone
from rest_framework import status
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Merchant, BankAccount, LedgerEntry, Payout, IdempotencyRecord
from .serializers import (
    MerchantSerializer, LedgerEntrySerializer, PayoutSerializer,
    PayoutRequestSerializer, BalanceSerializer, BankAccountSerializer,
)


def get_merchant_from_request(request):
    merchant_id = request.headers.get('X-Merchant-Id')
    if not merchant_id:
        return None
    try:
        return Merchant.objects.get(id=merchant_id)
    except Merchant.DoesNotExist:
        return None


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


def serialize_to_json_safe(serializer_data):
    json_bytes = JSONRenderer().render(serializer_data)
    return json.loads(json_bytes)


class MerchantListView(APIView):
    def get(self, request):
        merchants = Merchant.objects.all()
        serializer = MerchantSerializer(merchants, many=True)
        return Response(serializer.data)


class MerchantBalanceView(APIView):
    def get(self, request):
        merchant = get_merchant_from_request(request)
        if not merchant:
            return Response(
                {'error': 'Merchant not found. Provide X-Merchant-Id header.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        balance = compute_balance(merchant)
        serializer = BalanceSerializer(balance)
        return Response(serializer.data)


class LedgerView(APIView):
    def get(self, request):
        merchant = get_merchant_from_request(request)
        if not merchant:
            return Response(
                {'error': 'Merchant not found. Provide X-Merchant-Id header.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        entries = LedgerEntry.objects.filter(merchant=merchant)[:50]
        serializer = LedgerEntrySerializer(entries, many=True)
        return Response(serializer.data)


class PayoutCreateView(APIView):
    def post(self, request):
        merchant = get_merchant_from_request(request)
        if not merchant:
            return Response(
                {'error': 'Merchant not found. Provide X-Merchant-Id header.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        idempotency_key = request.headers.get('Idempotency-Key')
        if not idempotency_key:
            return Response(
                {'error': 'Idempotency-Key header is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

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

        serializer = PayoutRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        amount_paise = serializer.validated_data['amount_paise']
        bank_account_id = serializer.validated_data['bank_account_id']

        try:
            bank_account = BankAccount.objects.get(id=bank_account_id, merchant=merchant)
        except BankAccount.DoesNotExist:
            return Response(
                {'error': 'Bank account not found or does not belong to this merchant.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            with transaction.atomic():
                merchant_locked = Merchant.objects.select_for_update().get(id=merchant.id)

                balance = compute_balance(merchant_locked)
                available = balance['available_balance_paise']

                if amount_paise > available:
                    response_body = {
                        'error': 'Insufficient balance.',
                        'available_balance_paise': available,
                        'requested_amount_paise': amount_paise,
                    }
                    response_status = status.HTTP_400_BAD_REQUEST

                    IdempotencyRecord.objects.create(
                        merchant=merchant,
                        idempotency_key=idempotency_key,
                        response_status_code=response_status,
                        response_body=response_body,
                        expires_at=timezone.now() + timedelta(hours=24),
                    )
                    return Response(response_body, status=response_status)

                payout = Payout.objects.create(
                    merchant=merchant_locked,
                    amount_paise=amount_paise,
                    bank_account=bank_account,
                    status=Payout.PENDING,
                    idempotency_key=idempotency_key,
                )

                LedgerEntry.objects.create(
                    merchant=merchant_locked,
                    entry_type=LedgerEntry.HOLD,
                    amount_paise=amount_paise,
                    description=f'Hold for payout {payout.id}',
                    payout=payout,
                )

                payout_data = PayoutSerializer(payout).data
                response_body = serialize_to_json_safe(payout_data)
                response_status = status.HTTP_201_CREATED

                IdempotencyRecord.objects.create(
                    merchant=merchant,
                    idempotency_key=idempotency_key,
                    response_status_code=response_status,
                    response_body=response_body,
                    expires_at=timezone.now() + timedelta(hours=24),
                )

        except Exception as e:
            return Response(
                {'error': f'Failed to create payout: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(response_body, status=response_status)


class PayoutListView(APIView):
    def get(self, request):
        merchant = get_merchant_from_request(request)
        if not merchant:
            return Response(
                {'error': 'Merchant not found. Provide X-Merchant-Id header.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        payouts = Payout.objects.filter(merchant=merchant)[:50]
        serializer = PayoutSerializer(payouts, many=True)
        return Response(serializer.data)


class PayoutDetailView(APIView):
    def get(self, request, payout_id):
        merchant = get_merchant_from_request(request)
        if not merchant:
            return Response(
                {'error': 'Merchant not found. Provide X-Merchant-Id header.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            payout = Payout.objects.get(id=payout_id, merchant=merchant)
        except Payout.DoesNotExist:
            return Response(
                {'error': 'Payout not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = PayoutSerializer(payout)
        return Response(serializer.data)


class BankAccountListView(APIView):
    def get(self, request):
        merchant = get_merchant_from_request(request)
        if not merchant:
            return Response(
                {'error': 'Merchant not found. Provide X-Merchant-Id header.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        accounts = BankAccount.objects.filter(merchant=merchant)
        serializer = BankAccountSerializer(accounts, many=True)
        return Response(serializer.data)


class BalanceIntegrityCheckView(APIView):
    def get(self, request):
        merchant = get_merchant_from_request(request)
        if not merchant:
            return Response(
                {'error': 'Merchant not found.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        balance = compute_balance(merchant)

        completed_payouts_total = Payout.objects.filter(
            merchant=merchant,
            status=Payout.COMPLETED,
        ).aggregate(total=Sum('amount_paise'))['total'] or 0

        credits = balance['total_credits_paise']
        debits = balance['total_debits_paise']
        held = balance['held_balance_paise']
        available = balance['available_balance_paise']

        invariant_holds = available + held + debits == credits
        invariant_debits_match = debits == completed_payouts_total

        return Response({
            'credits': credits,
            'debits': debits,
            'held': held,
            'available': available,
            'invariant_balance_equation': invariant_holds,
            'invariant_debits_match_completed': invariant_debits_match,
            'all_ok': invariant_holds and invariant_debits_match,
        })