import uuid
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from ledger.models import Merchant, BankAccount, LedgerEntry


class Command(BaseCommand):
    help = 'Seed merchants with bank accounts and credit history'

    def handle(self, *args, **options):
        if Merchant.objects.exists():
            self.stdout.write(self.style.WARNING('Merchants already exist. Skipping seed.'))
            return

        merchants_data = [
            {
                'name': 'Priya Design Studio',
                'email': 'priya@designstudio.in',
                'bank': {
                    'account_number': '1234567890123456',
                    'ifsc_code': 'HDFC0001234',
                    'account_holder_name': 'Priya Sharma',
                    'bank_name': 'HDFC Bank',
                },
                'credits': [
                    (5000000, 'Payment from Acme Corp - Logo Design', 30),
                    (3500000, 'Payment from TechStart Inc - Website Redesign', 20),
                    (2000000, 'Payment from GlobalFin - Branding Package', 10),
                    (1500000, 'Payment from MediaHouse - Social Media Kit', 5),
                    (800000, 'Payment from StartupXYZ - Icon Set', 2),
                ],
            },
            {
                'name': 'Raj Software Solutions',
                'email': 'raj@softwaresolutions.in',
                'bank': {
                    'account_number': '9876543210987654',
                    'ifsc_code': 'ICIC0005678',
                    'account_holder_name': 'Raj Patel',
                    'bank_name': 'ICICI Bank',
                },
                'credits': [
                    (10000000, 'Payment from Enterprise Co - API Integration', 45),
                    (7500000, 'Payment from FinTech Ltd - Payment Gateway', 30),
                    (4500000, 'Payment from HealthTech - Dashboard Development', 15),
                    (3000000, 'Payment from EduPlatform - Mobile App Backend', 7),
                ],
            },
            {
                'name': 'Ananya Content Agency',
                'email': 'ananya@contentagency.in',
                'bank': {
                    'account_number': '5678901234567890',
                    'ifsc_code': 'SBIN0009012',
                    'account_holder_name': 'Ananya Krishnan',
                    'bank_name': 'State Bank of India',
                },
                'credits': [
                    (2500000, 'Payment from TravelCo - Blog Content Package', 25),
                    (1800000, 'Payment from FoodBrand - Recipe Content', 18),
                    (1200000, 'Payment from FitnessPro - Newsletter Copy', 12),
                    (900000, 'Payment from StyleMag - Fashion Articles', 6),
                    (600000, 'Payment from TechBlog - Technical Writing', 3),
                    (400000, 'Payment from NewsPortal - Editorial Content', 1),
                ],
            },
        ]

        for data in merchants_data:
            merchant = Merchant.objects.create(
                name=data['name'],
                email=data['email'],
            )

            BankAccount.objects.create(
                merchant=merchant,
                **data['bank'],
            )

            for amount, description, days_ago in data['credits']:
                entry = LedgerEntry.objects.create(
                    merchant=merchant,
                    entry_type=LedgerEntry.CREDIT,
                    amount_paise=amount,
                    description=description,
                )
                LedgerEntry.objects.filter(id=entry.id).update(
                    created_at=timezone.now() - timedelta(days=days_ago)
                )

            self.stdout.write(
                self.style.SUCCESS(f'Created merchant: {data["name"]}')
            )

        self.stdout.write(self.style.SUCCESS('Seeding complete.'))