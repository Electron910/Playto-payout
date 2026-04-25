from django.urls import path
from . import views

urlpatterns = [
    path('merchants/', views.MerchantListView.as_view(), name='merchant-list'),
    path('balance/', views.MerchantBalanceView.as_view(), name='merchant-balance'),
    path('ledger/', views.LedgerView.as_view(), name='ledger'),
    path('payouts/', views.PayoutCreateView.as_view(), name='payout-create'),
    path('payouts/list/', views.PayoutListView.as_view(), name='payout-list'),
    path('payouts/<uuid:payout_id>/', views.PayoutDetailView.as_view(), name='payout-detail'),
    path('bank-accounts/', views.BankAccountListView.as_view(), name='bank-account-list'),
    path('integrity/', views.BalanceIntegrityCheckView.as_view(), name='integrity-check'),
]