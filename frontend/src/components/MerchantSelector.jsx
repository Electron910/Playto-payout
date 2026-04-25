import React from 'react'

export default function MerchantSelector({ merchants, selected, onChange }) {
  return (
    <div className="flex items-center gap-2">
      <label className="text-playto-blue text-sm font-medium">Merchant:</label>
      <select
        className="bg-playto-dark border border-playto-blue/30 text-white text-sm rounded-lg px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-playto-gold focus:border-transparent cursor-pointer"
        value={selected?.id || ''}
        onChange={(e) => {
          const m = merchants.find((m) => m.id === e.target.value)
          if (m) onChange(m)
        }}
      >
        {merchants.map((m) => (
          <option key={m.id} value={m.id}>
            {m.name}
          </option>
        ))}
      </select>
    </div>
  )
}