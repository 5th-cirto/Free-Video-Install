import axios from 'axios'

const apiBase = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

const apiClient = axios.create({
  baseURL: apiBase,
  headers: { 'Content-Type': 'application/json' },
})

let accessTokenProvider = () => ''
let unauthorizedHandler = null

function isAuthEntryPath(path) {
  const value = String(path || '')
  return value.startsWith('/api/auth/login') || value.startsWith('/api/auth/register')
}

apiClient.interceptors.request.use((config) => {
  const token = accessTokenProvider?.() || ''
  if (token) {
    config.headers = config.headers || {}
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export function configureApiClient({ getAccessToken, onUnauthorized } = {}) {
  if (typeof getAccessToken === 'function') {
    accessTokenProvider = getAccessToken
  }
  unauthorizedHandler = typeof onUnauthorized === 'function' ? onUnauthorized : null
}

function toNetworkError(path) {
  return new Error(`无法连接后端接口(${apiBase})。请确认后端已启动，并允许当前前端端口跨域访问。`)
}

function toReadableError(error, path) {
  const detail = error?.response?.data?.detail
  const message = error?.response?.data?.message
  if (typeof detail === 'string' && detail.trim()) return new Error(detail)
  if (detail && typeof detail === 'object' && typeof detail.message === 'string' && detail.message.trim()) {
    return new Error(detail.message)
  }
  if (typeof message === 'string' && message.trim()) return new Error(message)
  if (typeof error?.message === 'string' && error.message.trim()) {
    if (error.message.includes('Network Error') || error.message.includes('ERR_NETWORK')) {
      return toNetworkError(path)
    }
    return new Error(error.message)
  }
  return new Error('请求失败')
}

export async function requestJson(path, payload = null, method = 'GET') {
  try {
    const response = await apiClient.request({
      url: path,
      method,
      data: payload || undefined,
    })
    return response.data
  } catch (error) {
    if (axios.isAxiosError(error) && error.response?.status === 401 && !isAuthEntryPath(path)) {
      unauthorizedHandler?.()
    }
    throw toReadableError(error, path)
  }
}

export { apiBase, apiClient, axios }
