import React from 'react'
import StatusBadge from './StatusBadge'

function formatPaise(paise) {
  if (paise == null) return '—'
  const rupees = paise / 100
  return `₹${rupees.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

function formatDate(dateStr) {
  if (!dateStr) return '—'
  const d = new Date(dateStr)
  return d.toLocaleDateString('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function truncateId(id) {
  if (!id) return ''
  return id.slice(0, 8) + '…'
}

export default function PayoutHistory({ payouts, loading }) {
  if (loading) {
    return (
      <div className="bg-white rounded-2xl shadow-sm border border-playto-light p-6">
        <div className="h-6 bg-playto-light rounded w-1/3 mb-4 animate-pulse"></div>
        <div className="space-y-3">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-12 bg-playto-light rounded animate-pulse"></div>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-playto-light overflow-hidden">
      <div className="px-6 py-4 border-b border-playto-light">
        <h2 className="text-playto-dark text-lg font-bold flex items-center gap-2">
          <svg className="w-5 h-5 text-playto-blue" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
          </svg>
          Payout History
          {payouts && (
            <span className="ml-auto text-xs font-normal text-playto-blue bg-playto-light px-2 py-0.5 rounded-full">
              {payouts.length} payouts
            </span>
          )}
        </h2>
      </div>

      <div className="overflow-x-auto scrollbar-thin max-h-96">
        {!payouts || payouts.length === 0 ? (
          <div className="px-6 py-12 text-center">
            <svg className="w-12 h-12 text-playto-light mx-auto mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
            </svg>
            <p className="text-playto-blue text-sm">No payouts yet</p>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-playto-light/40">
                <th className="text-left px-6 py-3 text-playto-blue font-semibold text-xs uppercase tracking-wider">ID</th>
                <th className="text-left px-6 py-3 text-playto-blue font-semibold text-xs uppercase tracking-wider">Amount</th>
                <th className="text-left px-6 py-3 text-playto-blue font-semibold text-xs uppercase tracking-wider">Bank</th>
                <th className="text-left px-6 py-3 text-playto-blue font-semibold text-xs uppercase tracking-wider">Status</th>
                <th className="text-left px-6 py-3 text-playto-blue font-semibold text-xs uppercase tracking-wider">Retries</th>
                <th className="text-left px-6 py-3 text-playto-blue font-semibold text-xs uppercase tracking-wider">Created</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-playto-light">
              {payouts.map((p) => (
                <tr key={p.id} className="hover:bg-playto-light/20 transition-colors">
                  <td className="px-6 py-3 font-mono text-playto-dark text-xs">{truncateId(p.id)}</td>
                  <td className="px-6 py-3 text-playto-dark font-semibold">{formatPaise(p.amount_paise)}</td>
                  <td className="px-6 py-3 text-playto-blue text-xs">
                    {p.bank_account_details
                      ? `${p.bank_account_details.bank_name} ••••${p.bank_account_details.account_number.slice(-4)}`
                      : '—'}
                  </td>
                  <td className="px-6 py-3"><StatusBadge status={p.status} /></td>
                  <td className="px-6 py-3 text-playto-blue text-center">{p.retry_count}/{p.max_retries}</td>
                  <td className="px-6 py-3 text-playto-blue text-xs">{formatDate(p.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}