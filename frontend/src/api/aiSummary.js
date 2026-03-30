import { apiClient } from './client'

export function aiSummaryStreamApi(payload, onDownloadProgress) {
  return apiClient.post('/api/ai-summary/stream', payload, {
    responseType: 'text',
    onDownloadProgress,
  })
}
