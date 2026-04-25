import React, { useCallback } from 'react'
import { fetchBalance, fetchLedger, fetchPayouts, fetchIntegrity } from '../api/client'
import usePolling from '../hooks/usePolling'
import BalanceCard from './BalanceCard'
import PayoutForm from './PayoutForm'
import PayoutHistory from './PayoutHistory'
import LedgerTable from './LedgerTable'

export default function Dashboard({ merchant }) {
  const balanceFetcher = useCallback(() => fetchBalance(), [merchant.id])
  const ledgerFetcher = useCallback(() => fetchLedger(), [merchant.id])
  const payoutsFetcher = useCallback(() => fetchPayouts(), [merchant.id])
  const integrityFetcher = useCallback(() => fetchIntegrity(), [merchant.id])

  const { data: balance, loading: balanceLoading, refresh: refreshBalance } = usePolling(balanceFetcher, 4000)
  const { data: ledger, loading: ledgerLoading, refresh: refreshLedger } = usePolling(ledgerFetcher, 4000)
  const { data: payouts, loading: payoutsLoading, refresh: refreshPayouts } = usePolling(payoutsFetcher, 3000)
  const { data: integrity } = usePolling(integrityFetcher, 8000)

  function handlePayoutCreated() {
    refreshBalance()
    refreshLedger()
    refreshPayouts()
  }

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <BalanceCard balance={balance} loading={balanceLoading} integrity={integrity} />
        </div>
        <div>
          <PayoutForm merchant={merchant} onPayoutCreated={handlePayoutCreated} />
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <PayoutHistory payouts={payouts} loading={payoutsLoading} />
        <LedgerTable entries={ledger} loading={ledgerLoading} />
      </div>
    </div>
  )
}