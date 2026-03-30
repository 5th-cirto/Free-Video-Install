export function parseSseMessage(rawMessage) {
  const lines = String(rawMessage || '')
    .split('\n')
    .map((line) => line.trimEnd())
  let event = 'message'
  const dataLines = []
  for (const line of lines) {
    if (line.startsWith('event:')) {
      event = line.slice('event:'.length).trim() || 'message'
    } else if (line.startsWith('data:')) {
      dataLines.push(line.slice('data:'.length).trim())
    }
  }
  let data = {}
  if (dataLines.length) {
    try {
      data = JSON.parse(dataLines.join('\n'))
    } catch (_error) {
      data = {}
    }
  }
  return { event, data }
}
