export function triggerBlobDownload(blob, filename) {
  const objectUrl = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = objectUrl
  anchor.download = filename
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  URL.revokeObjectURL(objectUrl)
}

export function extractFilename(disposition, fallback) {
  const match = /filename="?([^"]+)"?/i.exec(disposition || '')
  return match?.[1] || fallback
}
