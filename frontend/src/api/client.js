import axios from 'axios'

const BACKEND_URL = import.meta.env.VITE_API_URL || ''
const API_BASE = BACKEND_URL + '/api/v1'

const client = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
})

export function setMerchantId(merchantId) {
  client.defaults.headers['X-Merchant-Id'] = merchantId
}

export async function fetchMerchants() {
  const res = await client.get('/merchants/')
  return res.data
}

export async function fetchBalance() {
  const res = await client.get('/balance/')
  return res.data
}

export async function fetchLedger() {
  const res = await client.get('/ledger/')
  return res.data
}

export async function fetchPayouts() {
  const res = await client.get('/payouts/list/')
  return res.data
}

export async function fetchBankAccounts() {
  const res = await client.get('/bank-accounts/')
  return res.data
}

export async function createPayout(idempotencyKey, amountPaise, bankAccountId) {
  const res = await client.post('/payouts/', {
    amount_paise: amountPaise,
    bank_account_id: bankAccountId,
  }, {
    headers: {
      'Idempotency-Key': idempotencyKey,
    },
  })
  return res
}

export async function fetchIntegrity() {
  const res = await client.get('/integrity/')
  return res.data
}

export default client