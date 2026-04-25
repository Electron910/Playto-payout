import React, { useState, useEffect } from 'react'
import { fetchMerchants, setMerchantId } from './api/client'
import MerchantSelector from './components/MerchantSelector'
import Dashboard from './components/Dashboard'

export default function App() {
  const [merchants, setMerchants] = useState([])
  const [selectedMerchant, setSelectedMerchant] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchMerchants()
      .then((data) => {
        setMerchants(data)
        if (data.length > 0) {
          setSelectedMerchant(data[0])
          setMerchantId(data[0].id)
        }
      })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  function handleMerchantChange(merchant) {
    setSelectedMerchant(merchant)
    setMerchantId(merchant.id)
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-playto-light">
        <div className="flex flex-col items-center gap-4">
          <div className="w-12 h-12 border-4 border-playto-blue border-t-transparent rounded-full animate-spin"></div>
          <p className="text-playto-dark font-medium">Loading Playto Engine…</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-playto-light">
      <header className="bg-playto-dark shadow-lg">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 bg-playto-gold rounded-lg flex items-center justify-center">
                <svg className="w-5 h-5 text-playto-dark" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <div>
                <h1 className="text-white text-lg font-bold tracking-tight">Playto</h1>
                <p className="text-playto-blue text-xs -mt-0.5">Payout Engine</p>
              </div>
            </div>
            <MerchantSelector
              merchants={merchants}
              selected={selectedMerchant}
              onChange={handleMerchantChange}
            />
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {selectedMerchant ? (
          <Dashboard merchant={selectedMerchant} />
        ) : (
          <div className="text-center py-20">
            <p className="text-playto-dark text-lg">No merchants found. Run the seed command.</p>
          </div>
        )}
      </main>
    </div>
  )
}