import { apiBase, apiClient, requestJson } from './client'

export function buildThumbnailUrl(rawUrl) {
  if (!rawUrl) return ''
  return `${apiBase}/api/video/thumbnail?url=${encodeURIComponent(rawUrl)}`
}

export function inspectVideoApi(payload) {
  return requestJson('/api/video/inspect', payload, 'POST')
}

export function createDownloadApi(payload) {
  return requestJson('/api/video/download', payload, 'POST')
}

export function createBatchDownloadApi(payload) {
  return requestJson('/api/video/download/batch', payload, 'POST')
}

export function tasksApi() {
  return requestJson('/api/video/tasks')
}

export function runtimeConfigApi() {
  return requestJson('/api/video/config')
}

export function openPathApi(path) {
  return requestJson('/api/video/open-path?path=' + encodeURIComponent(path), null, 'POST')
}

export function downloadSubtitleApi(payload) {
  return apiClient.post('/api/video/subtitles/download', payload, { responseType: 'blob' })
}
