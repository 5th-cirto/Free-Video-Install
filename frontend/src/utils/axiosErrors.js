import { axios } from '../api/client'

export function getAxiosMessage(error, fallback = '请求失败') {
  if (!axios.isAxiosError(error)) {
    return String(error?.message || fallback)
  }
  const detail = error.response?.data?.detail
  const message = error.response?.data?.message
  if (typeof detail === 'string' && detail.trim()) return detail
  if (detail && typeof detail === 'object' && typeof detail.message === 'string' && detail.message.trim()) {
    return detail.message
  }
  if (typeof message === 'string' && message.trim()) return message
  if (typeof error.message === 'string' && error.message.trim()) return error.message
  return fallback
}

export function getAxiosDetail(error) {
  if (!axios.isAxiosError(error)) return null
  const detail = error.response?.data?.detail
  if (detail && typeof detail === 'object') return detail
  return null
}
