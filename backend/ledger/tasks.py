import random
import logging
from datetime import timedelta

from celery import shared_task
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from .models import Payout, LedgerEntry, Merchant, IdempotencyRecord

logger = logging.getLogger(__name__)


def simulate_bank_settlement():
    roll = random.random()
    if roll < 0.70:
        return 'completed'
    elif roll < 0.90:
        return 'failed'
    else:
        return 'processing'


@shared_task(name='ledger.tasks.process_pending_payouts')
def process_pending_payouts():
    pending_payouts = list(Payout.objects.filter(status=Payout.PENDING))

    if not pending_payouts:
        return

    logger.info(f"Found {len(pending_payouts)} pending payouts to process.")

    for payout in pending_payouts:
        process_single_payout.delay(str(payout.id))


@shared_task(name='ledger.tasks.process_single_payout', bind=True, max_retries=0)
def process_single_payout(self, payout_id):
    try:
        with transaction.atomic():
            payout = Payout.objects.select_for_update().get(id=payout_id)

            if payout.status != Payout.PENDING:
                return

            if not payout.can_transition_to(Payout.PROCESSING):
                logger.warning(f"Invalid transition for payout {payout_id} from {payout.status} to processing.")
                return

            payout.status = Payout.PROCESSING
            payout.processing_started_at = timezone.now()
            payout.save(update_fields=['status', 'processing_started_at', 'updated_at'])

        logger.info(f"Payout {payout_id} moved to processing. Simulating bank settlement...")

        settlement_result = simulate_bank_settlement()
        logger.info(f"Payout {payout_id} settlement result: {settlement_result}")

        if settlement_result == 'completed':
            complete_payout(payout_id)
        elif settlement_result == 'failed':
            fail_payout(payout_id, 'Bank rejected the transaction.')
        else:
            logger.info(f"Payout {payout_id} is hanging in processing (simulated timeout).")

    except Payout.DoesNotExist:
        logger.error(f"Payout {payout_id} not found.")
    except Exception as e:
        logger.error(f"Error processing payout {payout_id}: {e}")


def complete_payout(payout_id):
    with transaction.atomic():
        payout = Payout.objects.select_for_update().get(id=payout_id)

        if not payout.can_transition_to(Payout.COMPLETED):
            logger.warning(f"Cannot complete payout {payout_id} from state {payout.status}.")
            return

        merchant = Merchant.objects.select_for_update().get(id=payout.merchant_id)

        LedgerEntry.objects.create(
            merchant=merchant,
            entry_type=LedgerEntry.RELEASE,
            amount_paise=payout.amount_paise,
            description=f'Release hold for completed payout {payout.id}',
            payout=payout,
        )

        LedgerEntry.objects.create(
            merchant=merchant,
            entry_type=LedgerEntry.DEBIT,
            amount_paise=payout.amount_paise,
            description=f'Payout {payout.id} completed',
            payout=payout,
        )

        payout.status = Payout.COMPLETED
        payout.completed_at = timezone.now()
        payout.save(update_fields=['status', 'completed_at', 'updated_at'])

    logger.info(f"Payout {payout_id} completed successfully.")


def fail_payout(payout_id, reason=''):
    with transaction.atomic():
        payout = Payout.objects.select_for_update().get(id=payout_id)

        if not payout.can_transition_to(Payout.FAILED):
            logger.warning(f"Cannot fail payout {payout_id} from state {payout.status}.")
            return

        merchant = Merchant.objects.select_for_update().get(id=payout.merchant_id)

        LedgerEntry.objects.create(
            merchant=merchant,
            entry_type=LedgerEntry.RELEASE,
            amount_paise=payout.amount_paise,
            description=f'Release hold for failed payout {payout.id}: {reason}',
            payout=payout,
        )

        payout.status = Payout.FAILED
        payout.failed_at = timezone.now()
        payout.failure_reason = reason
        payout.save(update_fields=['status', 'failed_at', 'failure_reason', 'updated_at'])

    logger.info(f"Payout {payout_id} failed: {reason}")


@shared_task(name='ledger.tasks.retry_stuck_payouts')
def retry_stuck_payouts():
    stuck_threshold = timezone.now() - timedelta(seconds=30)

    stuck_payouts = list(Payout.objects.filter(
        status=Payout.PROCESSING,
        processing_started_at__lt=stuck_threshold,
    ))

    if not stuck_payouts:
        return

    logger.info(f"Found {len(stuck_payouts)} stuck payouts to retry.")

    for payout in stuck_payouts:
        retry_single_payout.delay(str(payout.id))


@shared_task(name='ledger.tasks.retry_single_payout', bind=True, max_retries=0)
def retry_single_payout(self, payout_id):
    try:
        with transaction.atomic():
            payout = Payout.objects.select_for_update().get(id=payout_id)

            if payout.status != Payout.PROCESSING:
                return

            stuck_threshold = timezone.now() - timedelta(seconds=30)
            if payout.processing_started_at and payout.processing_started_at >= stuck_threshold:
                return

            if payout.retry_count >= payout.max_retries:
                logger.info(f"Payout {payout_id} exceeded max retries ({payout.max_retries}). Failing permanently.")
                merchant = Merchant.objects.select_for_update().get(id=payout.merchant_id)

                LedgerEntry.objects.create(
                    merchant=merchant,
                    entry_type=LedgerEntry.RELEASE,
                    amount_paise=payout.amount_paise,
                    description=f'Release hold for payout {payout.id} after max retries exhausted',
                    payout=payout,
                )

                payout.status = Payout.FAILED
                payout.failed_at = timezone.now()
                payout.failure_reason = 'Max retries exceeded. Bank settlement timed out.'
                payout.save(update_fields=['status', 'failed_at', 'failure_reason', 'updated_at'])
                return

            backoff_seconds = (2 ** payout.retry_count) * 5
            next_retry_after = payout.processing_started_at + timedelta(seconds=30 + backoff_seconds)

            if timezone.now() < next_retry_after:
                logger.info(f"Payout {payout_id} in backoff period. Next retry after {next_retry_after}.")
                return

            payout.retry_count = F('retry_count') + 1
            payout.processing_started_at = timezone.now()
            payout.save(update_fields=['retry_count', 'processing_started_at', 'updated_at'])

        payout.refresh_from_db()
        logger.info(f"Retrying payout {payout_id} (attempt #{payout.retry_count})...")

        settlement_result = simulate_bank_settlement()
        logger.info(f"Payout {payout_id} retry settlement result: {settlement_result}")

        if settlement_result == 'completed':
            complete_payout(payout_id)
        elif settlement_result == 'failed':
            fail_payout(payout_id, f'Bank rejected on retry #{payout.retry_count}.')
        else:
            logger.info(f"Payout {payout_id} still hanging after retry #{payout.retry_count}.")

    except Payout.DoesNotExist:
        logger.error(f"Payout {payout_id} not found for retry.")
    except Exception as e:
        logger.error(f"Error retrying payout {payout_id}: {e}")


@shared_task(name='ledger.tasks.cleanup_expired_idempotency_keys')
def cleanup_expired_idempotency_keys():
    deleted_count, _ = IdempotencyRecord.objects.filter(
        expires_at__lt=timezone.now()
    ).delete()
    if deleted_count > 0:
        logger.info(f"Cleaned up {deleted_count} expired idempotency records.")