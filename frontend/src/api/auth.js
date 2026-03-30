import { requestJson } from './client'

export function registerApi(payload) {
  return requestJson('/api/auth/register', payload, 'POST')
}

export function loginApi(payload) {
  return requestJson('/api/auth/login', payload, 'POST')
}

export function meApi() {
  return requestJson('/api/auth/me')
}

export function requestPasswordResetApi(payload) {
  return requestJson('/api/auth/request-password-reset', payload, 'POST')
}

export function resetPasswordApi(payload) {
  return requestJson('/api/auth/reset-password', payload, 'POST')
}
