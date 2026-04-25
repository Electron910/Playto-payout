import React, { useState, useEffect } from 'react'
import { createPayout, fetchBankAccounts } from '../api/client'

function generateUUID() {
  return crypto.randomUUID()
}

export default function PayoutForm({ merchant, onPayoutCreated }) {
  const [amountRupees, setAmountRupees] = useState('')
  const [bankAccountId, setBankAccountId] = useState('')
  const [bankAccounts, setBankAccounts] = useState([])
  const [submitting, setSubmitting] = useState(false)
  const [result, setResult] = useState(null)

  useEffect(() => {
    fetchBankAccounts()
      .then((data) => {
        setBankAccounts(data)
        if (data.length > 0) setBankAccountId(data[0].id)
      })
      .catch(console.error)
  }, [merchant.id])

  async function handleSubmit(e) {
    e.preventDefault()
    setSubmitting(true)
    setResult(null)

    const amountPaise = Math.round(parseFloat(amountRupees) * 100)
    if (isNaN(amountPaise) || amountPaise <= 0) {
      setResult({ type: 'error', message: 'Enter a valid amount.' })
      setSubmitting(false)
      return
    }

    const idempotencyKey = generateUUID()

    try {
      const res = await createPayout(idempotencyKey, amountPaise, bankAccountId)
      setResult({
        type: 'success',
        message: `Payout of ₹${(amountPaise / 100).toFixed(2)} created successfully.`,
      })
      setAmountRupees('')
      onPayoutCreated()
    } catch (err) {
      const msg = err.response?.data?.error || 'Something went wrong.'
      setResult({ type: 'error', message: msg })
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-playto-light p-6 h-full flex flex-col">
      <h2 className="text-playto-dark text-lg font-bold mb-4 flex items-center gap-2">
        <svg className="w-5 h-5 text-playto-gold" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2zm7-5a2 2 0 11-4 0 2 2 0 014 0z" />
        </svg>
        Request Payout
      </h2>

      <form onSubmit={handleSubmit} className="flex flex-col flex-1 gap-4">
        <div>
          <label className="block text-playto-dark text-sm font-medium mb-1.5">
            Amount (₹)
          </label>
          <div className="relative">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-playto-blue font-medium">₹</span>
            <input
              type="number"
              step="0.01"
              min="1"
              placeholder="0.00"
              value={amountRupees}
              onChange={(e) => setAmountRupees(e.target.value)}
              className="w-full pl-8 pr-4 py-2.5 border border-playto-light rounded-xl text-playto-dark placeholder-playto-blue/40 focus:outline-none focus:ring-2 focus:ring-playto-gold focus:border-transparent transition-all"
              required
            />
          </div>
        </div>

        <div>
          <label className="block text-playto-dark text-sm font-medium mb-1.5">
            Bank Account
          </label>
          <select
            value={bankAccountId}
            onChange={(e) => setBankAccountId(e.target.value)}
            className="w-full px-4 py-2.5 border border-playto-light rounded-xl text-playto-dark focus:outline-none focus:ring-2 focus:ring-playto-gold focus:border-transparent transition-all cursor-pointer"
            required
          >
            {bankAccounts.map((acc) => (
              <option key={acc.id} value={acc.id}>
                {acc.bank_name} — ••••{acc.account_number.slice(-4)}
              </option>
            ))}
          </select>
        </div>

        <div className="flex-1" />

        {result && (
          <div className={`px-4 py-3 rounded-xl text-sm font-medium ${
            result.type === 'success'
              ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
              : 'bg-red-50 text-red-700 border border-red-200'
          }`}>
            {result.message}
          </div>
        )}

        <button
          type="submit"
          disabled={submitting}
          className="w-full py-3 bg-playto-gold text-playto-dark font-bold rounded-xl hover:bg-playto-gold/90 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 shadow-sm hover:shadow-md active:scale-[0.98]"
        >
          {submitting ? (
            <span className="flex items-center justify-center gap-2">
              <svg className="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none">
                <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" className="opacity-25" />
                <path d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" fill="currentColor" className="opacity-75" />
              </svg>
              Processing…
            </span>
          ) : (
            'Submit Payout Request'
          )}
        </button>
      </form>
    </div>
  )
}