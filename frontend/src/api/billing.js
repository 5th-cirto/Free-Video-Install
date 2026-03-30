import { requestJson } from './client'

export function membershipStatusApi() {
  return requestJson('/api/billing/membership-status')
}

export function ordersApi() {
  return requestJson('/api/billing/orders')
}

export function checkoutSessionApi(payload) {
  return requestJson('/api/billing/checkout-session', payload, 'POST')
}
