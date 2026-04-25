import React from 'react'

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
    hour: '2-digit',
    minute: '2-digit',
  })
}

const ENTRY_STYLES = {
  credit: {
    icon: '↓',
    color: 'text-emerald-600',
    bg: 'bg-emerald-50',
    label: 'Credit',
  },
  debit: {
    icon: '↑',
    color: 'text-red-600',
    bg: 'bg-red-50',
    label: 'Debit',
  },
  hold: {
    icon: '⏸',
    color: 'text-amber-600',
    bg: 'bg-amber-50',
    label: 'Hold',
  },
  release: {
    icon: '▶',
    color: 'text-blue-600',
    bg: 'bg-blue-50',
    label: 'Release',
  },
}

export default function LedgerTable({ entries, loading }) {
  if (loading) {
    return (
      <div className="bg-white rounded-2xl shadow-sm border border-playto-light p-6">
        <div className="h-6 bg-playto-light rounded w-1/3 mb-4 animate-pulse"></div>
        <div className="space-y-3">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-10 bg-playto-light rounded animate-pulse"></div>
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
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 10h16M4 14h16M4 18h16" />
          </svg>
          Ledger
          {entries && (
            <span className="ml-auto text-xs font-normal text-playto-blue bg-playto-light px-2 py-0.5 rounded-full">
              {entries.length} entries
            </span>
          )}
        </h2>
      </div>

      <div className="overflow-x-auto scrollbar-thin max-h-96">
        {!entries || entries.length === 0 ? (
          <div className="px-6 py-12 text-center">
            <p className="text-playto-blue text-sm">No ledger entries</p>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-playto-light/40">
                <th className="text-left px-6 py-3 text-playto-blue font-semibold text-xs uppercase tracking-wider">Type</th>
                <th className="text-left px-6 py-3 text-playto-blue font-semibold text-xs uppercase tracking-wider">Amount</th>
                <th className="text-left px-6 py-3 text-playto-blue font-semibold text-xs uppercase tracking-wider">Description</th>
                <th className="text-left px-6 py-3 text-playto-blue font-semibold text-xs uppercase tracking-wider">Date</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-playto-light">
              {entries.map((entry) => {
                const style = ENTRY_STYLES[entry.entry_type] || ENTRY_STYLES.credit
                return (
                  <tr key={entry.id} className="hover:bg-playto-light/20 transition-colors">
                    <td className="px-6 py-3">
                      <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold ${style.bg} ${style.color}`}>
                        <span>{style.icon}</span>
                        {style.label}
                      </span>
                    </td>
                    <td className={`px-6 py-3 font-semibold ${
                      entry.entry_type === 'credit' || entry.entry_type === 'release'
                        ? 'text-emerald-600'
                        : 'text-red-600'
                    }`}>
                      {entry.entry_type === 'credit' || entry.entry_type === 'release' ? '+' : '-'}
                      {formatPaise(entry.amount_paise)}
                    </td>
                    <td className="px-6 py-3 text-playto-dark text-xs max-w-[200px] truncate" title={entry.description}>
                      {entry.description}
                    </td>
                    <td className="px-6 py-3 text-playto-blue text-xs">{formatDate(entry.created_at)}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}