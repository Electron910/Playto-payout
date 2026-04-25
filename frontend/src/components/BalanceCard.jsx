import React from 'react'

function formatPaise(paise) {
  if (paise == null) return '—'
  const rupees = Math.abs(paise) / 100
  const sign = paise < 0 ? '-' : ''
  return `${sign}₹${rupees.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

export default function BalanceCard({ balance, loading, integrity }) {
  if (loading || !balance) {
    return (
      <div className="bg-white rounded-2xl shadow-sm border border-playto-light p-6 animate-pulse">
        <div className="h-6 bg-playto-light rounded w-1/3 mb-4"></div>
        <div className="h-10 bg-playto-light rounded w-1/2 mb-6"></div>
        <div className="grid grid-cols-3 gap-4">
          <div className="h-16 bg-playto-light rounded"></div>
          <div className="h-16 bg-playto-light rounded"></div>
          <div className="h-16 bg-playto-light rounded"></div>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-playto-light overflow-hidden">
      <div className="bg-gradient-to-r from-playto-dark to-playto-blue p-6">
        <p className="text-playto-light/70 text-sm font-medium mb-1">Available Balance</p>
        <p className="text-white text-4xl font-bold tracking-tight">
          {formatPaise(balance.available_balance_paise)}
        </p>
      </div>

      <div className="p-6">
        <div className="grid grid-cols-3 gap-4">
          <div className="bg-playto-light/50 rounded-xl p-4">
            <p className="text-playto-blue text-xs font-medium uppercase tracking-wider mb-1">Held</p>
            <p className="text-playto-dark text-lg font-semibold">
              {formatPaise(balance.held_balance_paise)}
            </p>
          </div>
          <div className="bg-playto-light/50 rounded-xl p-4">
            <p className="text-playto-blue text-xs font-medium uppercase tracking-wider mb-1">Total Credits</p>
            <p className="text-playto-dark text-lg font-semibold">
              {formatPaise(balance.total_credits_paise)}
            </p>
          </div>
          <div className="bg-playto-light/50 rounded-xl p-4">
            <p className="text-playto-blue text-xs font-medium uppercase tracking-wider mb-1">Total Debits</p>
            <p className="text-playto-dark text-lg font-semibold">
              {formatPaise(balance.total_debits_paise)}
            </p>
          </div>
        </div>

        {integrity && (
          <div className={`mt-4 flex items-center gap-2 px-3 py-2 rounded-lg text-sm ${
            integrity.all_ok
              ? 'bg-emerald-50 text-emerald-700'
              : 'bg-red-50 text-red-700'
          }`}>
            <span className={`w-2 h-2 rounded-full ${integrity.all_ok ? 'bg-emerald-500' : 'bg-red-500'}`}></span>
            {integrity.all_ok
              ? 'Ledger integrity verified'
              : 'Ledger integrity check failed'}
          </div>
        )}
      </div>
    </div>
  )
}