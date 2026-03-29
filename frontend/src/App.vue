<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import DownloadPanel from './components/DownloadPanel.vue'
import StudioHeader from './components/StudioHeader.vue'
import SummaryPanel from './components/SummaryPanel.vue'
import TaskCenterPanel from './components/TaskCenterPanel.vue'

const apiBase = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

const mode = ref('single')
const singleUrl = ref('')
const batchInput = ref('')
const inspectLoading = ref(false)
const inspectError = ref('')
const inspectInfo = ref(null)
const selectedFormatId = ref('')
const actionError = ref('')
const actionLoading = ref(false)
const downloadsDir = ref('')
const aiLanguage = ref('')
const aiLoading = ref(false)
const aiError = ref('')
const aiStage = ref('')
const aiRaw = ref('')
const aiResult = ref(null)
const aiPartialResult = ref({
  summary: '',
  outline: [],
  key_points: [],
  mindmap_mermaid: '',
})
const aiCurrentUrl = ref('')
const mindmapSvg = ref('')
const mindmapRenderError = ref('')
const mindmapRenderHint = ref('')
const mindmapFullscreen = ref(false)
let mermaidInstance = null

const tasks = ref([])
let pollTimer = null

const parsedBatchUrls = computed(() =>
  batchInput.value
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean),
)

const successCount = computed(() => tasks.value.filter((task) => task.status === 'success').length)
const failedCount = computed(() => tasks.value.filter((task) => task.status === 'failed').length)
const runningCount = computed(() =>
  tasks.value.filter((task) => task.status === 'running' || task.status === 'queued').length,
)
const aiDisplayResult = computed(() => aiResult.value || aiPartialResult.value)
const aiStreamingSummary = computed(() => {
  const partial = String(aiDisplayResult.value?.summary || '').trim()
  if (partial) return partial
  const raw = String(aiRaw.value || '')
  if (!raw) return ''
  const match = raw.match(/"summary"\s*:\s*"([\s\S]*?)(?:"\s*,\s*"outline"|$)/)
  if (!match?.[1]) return ''
  return match[1].replace(/\\"/g, '"').replace(/\\n/g, '\n').trim()
})
const aiStreamingKeyPoints = computed(() => {
  const fromPartial = Array.isArray(aiDisplayResult.value?.key_points) ? aiDisplayResult.value.key_points : []
  if (fromPartial.length) return fromPartial
  const raw = String(aiRaw.value || '')
  if (!raw) return []
  const match = raw.match(/"key_points"\s*:\s*\[([\s\S]*?)(?:\]|$)/)
  if (!match?.[1]) return []
  const body = match[1]
  const points = []
  const regex = /"((?:\\.|[^"])*)"/g
  let item
  while ((item = regex.exec(body)) !== null) {
    const value = String(item[1] || '').replace(/\\"/g, '"').replace(/\\n/g, '\n').trim()
    if (value) points.push(value)
  }
  return points
})
const hasAiContent = computed(
  () =>
    Boolean(aiRaw.value) ||
    Boolean(aiDisplayResult.value?.summary) ||
    Boolean(aiDisplayResult.value?.outline?.length) ||
    Boolean(aiDisplayResult.value?.key_points?.length) ||
    Boolean(aiDisplayResult.value?.mindmap_mermaid) ||
    Boolean(aiResult.value?.subtitle_segments?.length),
)
const aiViewTab = ref('summary')
const taskCenterExpanded = ref(false)

function formatDuration(seconds) {
  if (!seconds || Number.isNaN(seconds)) return '--:--'
  const total = Math.floor(seconds)
  const hours = Math.floor(total / 3600)
  const minutes = Math.floor((total % 3600) / 60)
  const secs = total % 60
  if (hours > 0) return `${hours}:${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')}`
  return `${minutes}:${String(secs).padStart(2, '0')}`
}

function formatTimestamp(seconds) {
  const value = Number(seconds || 0)
  if (!Number.isFinite(value) || value < 0) return '00:00'
  const total = Math.floor(value)
  const hours = Math.floor(total / 3600)
  const minutes = Math.floor((total % 3600) / 60)
  const secs = total % 60
  if (hours > 0) return `${hours}:${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')}`
  return `${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')}`
}

function thumbnailUrl(rawUrl) {
  if (!rawUrl) return ''
  return `${apiBase}/api/video/thumbnail?url=${encodeURIComponent(rawUrl)}`
}

async function callApi(path, payload = null, method = 'GET') {
  const options = {
    method,
    headers: {
      'Content-Type': 'application/json',
    },
  }
  if (payload) options.body = JSON.stringify(payload)

  let response
  try {
    response = await fetch(`${apiBase}${path}`, options)
  } catch (error) {
    const text = String(error?.message || '')
    if (text.includes('Failed to fetch')) {
      throw new Error(`无法连接后端接口(${apiBase})。请确认后端已启动，并允许当前前端端口跨域访问。`)
    }
    throw error
  }
  const body = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw new Error(body?.detail || body?.message || `请求失败(${response.status})`)
  }
  return body
}

async function inspectVideo() {
  inspectError.value = ''
  actionError.value = ''
  inspectInfo.value = null
  selectedFormatId.value = ''
  if (!singleUrl.value.trim()) {
    inspectError.value = '请先输入视频链接'
    return
  }
  inspectLoading.value = true
  try {
    const resp = await callApi('/api/video/inspect', { url: singleUrl.value.trim() }, 'POST')
    inspectInfo.value = resp.data
    aiCurrentUrl.value = singleUrl.value.trim()
    await startAiSummaryStream(singleUrl.value.trim())
  } catch (error) {
    inspectError.value = error.message
  } finally {
    inspectLoading.value = false
  }
}

async function createSingleDownload() {
  actionError.value = ''
  actionLoading.value = true
  try {
    await callApi(
      '/api/video/download',
      { url: singleUrl.value.trim(), format_id: selectedFormatId.value || null },
      'POST',
    )
    await loadTasks()
  } catch (error) {
    actionError.value = error.message
  } finally {
    actionLoading.value = false
  }
}

async function createBatchDownload() {
  actionError.value = ''
  actionLoading.value = true
  try {
    if (!parsedBatchUrls.value.length) throw new Error('请至少输入一条链接')
    await callApi(
      '/api/video/download/batch',
      {
        urls: parsedBatchUrls.value,
        format_id: selectedFormatId.value || null,
      },
      'POST',
    )
    await loadTasks()
  } catch (error) {
    actionError.value = error.message
  } finally {
    actionLoading.value = false
  }
}

async function loadTasks() {
  try {
    const resp = await callApi('/api/video/tasks')
    tasks.value = resp?.data?.tasks || []
  } catch (_error) {
    // Keep silent for polling to avoid noisy UI.
  }
}

async function loadRuntimeConfig() {
  try {
    const resp = await callApi('/api/video/config')
    downloadsDir.value = resp?.data?.downloads_dir || ''
  } catch (_error) {
    downloadsDir.value = ''
  }
}

async function openLocalPath(path) {
  if (!path) return
  try {
    await callApi('/api/video/open-path?path=' + encodeURIComponent(path), null, 'POST')
  } catch (error) {
    actionError.value = error.message
  }
}

function resetAiState() {
  aiError.value = ''
  aiStage.value = ''
  aiRaw.value = ''
  aiResult.value = null
  aiPartialResult.value = {
    summary: '',
    outline: [],
    key_points: [],
    mindmap_mermaid: '',
  }
  mindmapSvg.value = ''
  mindmapRenderError.value = ''
  mindmapRenderHint.value = ''
  aiViewTab.value = 'summary'
}

function parseSseMessage(rawMessage) {
  const lines = rawMessage.split('\n')
  let event = 'message'
  const dataLines = []
  for (const line of lines) {
    if (!line) continue
    if (line.startsWith('event:')) {
      event = line.slice(6).trim()
      continue
    }
    if (line.startsWith('data:')) {
      dataLines.push(line.slice(5).trim())
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

async function startAiSummaryStream(urlOverride = '') {
  resetAiState()
  const targetUrl = (urlOverride || singleUrl.value || aiCurrentUrl.value).trim()
  if (!targetUrl) {
    aiError.value = '请先在下载工作台输入视频链接'
    return
  }
  aiCurrentUrl.value = targetUrl
  aiLoading.value = true
  try {
    let response
    try {
      response = await fetch(`${apiBase}/api/ai-summary/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          url: targetUrl,
          language: aiLanguage.value.trim() || null,
        }),
      })
    } catch (error) {
      const text = String(error?.message || '')
      if (text.includes('Failed to fetch')) {
        throw new Error(`AI总结请求无法连接后端(${apiBase})，请检查后端服务与跨域端口配置。`)
      }
      throw error
    }
    if (!response.ok || !response.body) {
      throw new Error(`SSE请求失败(${response.status})`)
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder('utf-8')
    let buffer = ''

    while (true) {
      const { value, done } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })

      let splitIndex = buffer.indexOf('\n\n')
      while (splitIndex !== -1) {
        const packet = buffer.slice(0, splitIndex)
        buffer = buffer.slice(splitIndex + 2)
        const parsed = parseSseMessage(packet)
        if (parsed.event === 'stage') {
          aiStage.value = parsed.data?.stage || ''
        } else if (parsed.event === 'delta') {
          aiRaw.value += parsed.data?.text || ''
        } else if (parsed.event === 'partial_result') {
          aiPartialResult.value = {
            summary: parsed.data?.summary || '',
            outline: parsed.data?.outline || [],
            key_points: parsed.data?.key_points || [],
            mindmap_mermaid: parsed.data?.mindmap_mermaid || '',
          }
        } else if (parsed.event === 'result') {
          aiResult.value = parsed.data || null
        } else if (parsed.event === 'error') {
          aiError.value = parsed.data?.message || '总结失败'
        } else if (parsed.event === 'done') {
          aiStage.value = parsed.data?.ok ? 'done' : 'failed'
          aiLoading.value = false
        }
        splitIndex = buffer.indexOf('\n\n')
      }
    }
  } catch (error) {
    aiError.value = error.message || 'SSE连接失败'
  } finally {
    aiLoading.value = false
  }
}

async function ensureMermaid() {
  if (mermaidInstance) return mermaidInstance
  const mod = await import('mermaid')
  mermaidInstance = mod.default
  mermaidInstance.initialize({
    startOnLoad: false,
    securityLevel: 'strict',
    theme: 'default',
  })
  return mermaidInstance
}

async function renderMindmapSvg(source) {
  if (!source) {
    mindmapSvg.value = ''
    mindmapRenderError.value = ''
    mindmapRenderHint.value = ''
    return
  }
  const fallbackSource = buildFallbackMindmapSource(aiResult.value)
  try {
    const mermaid = await ensureMermaid()
    const id = `mindmap-${Date.now()}`
    const output = await mermaid.render(id, source)
    mindmapSvg.value = output.svg || ''
    mindmapRenderError.value = ''
    mindmapRenderHint.value = ''
  } catch (error) {
    try {
      if (fallbackSource && fallbackSource !== source) {
        const mermaid = await ensureMermaid()
        const id = `mindmap-fallback-${Date.now()}`
        const output = await mermaid.render(id, fallbackSource)
        mindmapSvg.value = output.svg || ''
        mindmapRenderError.value = ''
        mindmapRenderHint.value = '模型返回的导图语法无效，已使用大纲自动重建导图。'
        return
      }
    } catch (_fallbackError) {
      // Keep original error below.
    }
    mindmapSvg.value = ''
    mindmapRenderHint.value = ''
    mindmapRenderError.value = error?.message || '思维导图渲染失败'
  }
}

function buildFallbackMindmapSource(result) {
  const roots = [...(result?.outline || []), ...(result?.key_points || [])].filter(Boolean).slice(0, 12)
  if (!roots.length) return ''
  const lines = ['mindmap', '  root((VideoSummary))']
  for (const item of roots) {
    const safe = String(item).replace(/\n/g, ' ').replace(/"/g, "'").trim()
    if (safe) lines.push(`    ${safe}`)
  }
  return lines.join('\n')
}

watch(
  () => aiDisplayResult.value?.mindmap_mermaid,
  (nextValue) => {
    renderMindmapSvg(nextValue || '')
  },
)

watch(runningCount, (count) => {
  if (count > 0) {
    taskCenterExpanded.value = true
  }
})

function openMindmapFullscreen() {
  if (!mindmapSvg.value) return
  mindmapFullscreen.value = true
}

function closeMindmapFullscreen() {
  mindmapFullscreen.value = false
}

function getMindmapSvgText() {
  if (!mindmapSvg.value) throw new Error('当前无可导出的思维导图')
  if (mindmapSvg.value.includes('xmlns=')) return mindmapSvg.value
  return mindmapSvg.value.replace('<svg ', '<svg xmlns="http://www.w3.org/2000/svg" ')
}

function triggerBlobDownload(blob, filename) {
  const objectUrl = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = objectUrl
  anchor.download = filename
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  URL.revokeObjectURL(objectUrl)
}

function downloadMindmapSvg() {
  try {
    const svgText = getMindmapSvgText()
    const blob = new Blob([svgText], { type: 'image/svg+xml;charset=utf-8' })
    triggerBlobDownload(blob, 'mindmap.svg')
  } catch (error) {
    aiError.value = error.message || '导出 SVG 失败'
  }
}

function extractFilename(disposition, fallback) {
  const match = /filename="?([^"]+)"?/i.exec(disposition || '')
  return match?.[1] || fallback
}

function formatSubtitleTime(seconds, forSrt = true) {
  const value = Math.max(0, Number(seconds || 0))
  const totalMs = Math.round(value * 1000)
  const hours = Math.floor(totalMs / 3600000)
  const minutes = Math.floor((totalMs % 3600000) / 60000)
  const secs = Math.floor((totalMs % 60000) / 1000)
  const millis = totalMs % 1000
  const sep = forSrt ? ',' : '.'
  return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')}${sep}${String(millis).padStart(3, '0')}`
}

function buildLocalSubtitle(format) {
  const text = String(aiResult.value?.subtitle_text || '').trim()
  const segments = Array.isArray(aiResult.value?.subtitle_segments) ? aiResult.value.subtitle_segments : []

  if (format === 'txt') {
    if (text) return text
    return segments.map((seg) => String(seg?.text || '').trim()).filter(Boolean).join('\n')
  }

  if (format === 'vtt') {
    const rows = ['WEBVTT', '']
    segments.forEach((seg) => {
      const line = String(seg?.text || '').trim()
      if (!line) return
      rows.push(`${formatSubtitleTime(seg?.start, false)} --> ${formatSubtitleTime(seg?.end, false)}`)
      rows.push(line)
      rows.push('')
    })
    return rows.join('\n').trim()
  }

  const blocks = []
  segments.forEach((seg, idx) => {
    const line = String(seg?.text || '').trim()
    if (!line) return
    blocks.push(`${idx + 1}\n${formatSubtitleTime(seg?.start, true)} --> ${formatSubtitleTime(seg?.end, true)}\n${line}`)
  })
  return blocks.join('\n\n').trim()
}

function downloadSubtitleFromLocalResult(format) {
  const content = buildLocalSubtitle(format)
  if (!content) {
    throw new Error('当前没有可导出的字幕内容，请先完成 AI 总结。')
  }
  const blob = new Blob([content], { type: 'text/plain;charset=utf-8' })
  triggerBlobDownload(blob, `subtitle.${format}`)
}

async function downloadSubtitleFile(format) {
  const targetUrl = aiCurrentUrl.value.trim() || singleUrl.value.trim()
  if (!targetUrl) {
    aiError.value = '请先输入并解析视频链接'
    return
  }
  aiError.value = ''
  try {
    const response = await fetch(`${apiBase}/api/video/subtitles/download`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        url: targetUrl,
        language: aiLanguage.value.trim() || null,
        format,
      }),
    })
    if (!response.ok) {
      if (response.status === 404) {
        downloadSubtitleFromLocalResult(format)
        return
      }
      const body = await response.json().catch(() => ({}))
      throw new Error(body?.detail || `字幕下载失败(${response.status})`)
    }
    const blob = await response.blob()
    const disposition = response.headers.get('content-disposition') || ''
    triggerBlobDownload(blob, extractFilename(disposition, `subtitle.${format}`))
  } catch (error) {
    aiError.value = error.message || '字幕下载失败'
  }
}

onMounted(async () => {
  await loadRuntimeConfig()
  await loadTasks()
  pollTimer = setInterval(loadTasks, 2000)
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<template>
  <div class="app-shell">
    <StudioHeader :running-count="runningCount" :success-count="successCount" :failed-count="failedCount" />

    <section class="studio-layout">
      <SummaryPanel
        class="right-column"
        :ai-stage="aiStage"
        :ai-loading="aiLoading"
        :ai-error="aiError"
        :ai-view-tab="aiViewTab"
        :has-ai-content="hasAiContent"
        :ai-streaming-summary="aiStreamingSummary"
        :ai-streaming-key-points="aiStreamingKeyPoints"
        :ai-raw="aiRaw"
        :ai-display-result="aiDisplayResult"
        :ai-result="aiResult"
        :mindmap-svg="mindmapSvg"
        :mindmap-render-hint="mindmapRenderHint"
        :mindmap-render-error="mindmapRenderError"
        :format-timestamp="formatTimestamp"
        @update:ai-view-tab="aiViewTab = $event"
        @open-mindmap-fullscreen="openMindmapFullscreen"
        @download-mindmap-svg="downloadMindmapSvg"
        @download-subtitle-file="downloadSubtitleFile"
      />

      <DownloadPanel
        class="left-column"
        :mode="mode"
        :single-url="singleUrl"
        :batch-input="batchInput"
        :parsed-batch-urls="parsedBatchUrls"
        :inspect-loading="inspectLoading"
        :inspect-error="inspectError"
        :inspect-info="inspectInfo"
        :selected-format-id="selectedFormatId"
        :action-error="actionError"
        :action-loading="actionLoading"
        :downloads-dir="downloadsDir"
        :format-duration="formatDuration"
        :thumbnail-url="thumbnailUrl"
        @update:mode="mode = $event"
        @update:single-url="singleUrl = $event"
        @update:batch-input="batchInput = $event"
        @update:selected-format-id="selectedFormatId = $event"
        @inspect="inspectVideo"
        @create-single-download="createSingleDownload"
        @create-batch-download="createBatchDownload"
      />
    </section>

    <TaskCenterPanel
      :expanded="taskCenterExpanded"
      :running-count="runningCount"
      :success-count="successCount"
      :failed-count="failedCount"
      :tasks="tasks"
      @toggle="taskCenterExpanded = !taskCenterExpanded"
      @open-local-path="openLocalPath"
    />

    <div v-if="mindmapFullscreen" class="mindmap-modal" @click.self="closeMindmapFullscreen">
      <div class="mindmap-modal-content">
        <div class="mindmap-modal-head">
          <strong>思维导图全屏预览</strong>
          <button class="open-btn" @click="closeMindmapFullscreen">关闭</button>
        </div>
        <div class="mindmap-modal-preview" v-html="mindmapSvg"></div>
      </div>
    </div>
  </div>
</template>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Lexend:wght@500;700;800&family=Manrope:wght@400;500;600;700&display=swap');

:global(body) {
  margin: 0;
  font-family: 'Manrope', sans-serif;
  color: #192847;
  background:
    radial-gradient(circle at 8% -18%, rgba(64, 132, 255, 0.14), transparent 46%),
    radial-gradient(circle at 100% -12%, rgba(86, 189, 255, 0.12), transparent 42%),
    #f2f6fc;
}

.app-shell {
  height: 100vh;
  max-width: 1440px;
  margin: 0 auto;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  box-sizing: border-box;
}

.studio-layout {
  display: flex;
  gap: 10px;
  flex: 1;
  min-height: 0;
  align-items: stretch;
}

.left-column {
  order: 1;
  flex: 0 0 40%;
  max-width: 40%;
  min-height: 0;
  overflow: auto;
}

.right-column {
  order: 2;
  flex: 1 1 60%;
  max-width: 60%;
  min-height: 0;
  overflow: hidden;
}

.mindmap-modal {
  position: fixed;
  inset: 0;
  background: rgba(24, 39, 69, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  backdrop-filter: blur(4px);
  z-index: 60;
}

.mindmap-modal-content {
  width: min(1280px, 100%);
  max-height: calc(100vh - 40px);
  background: #fff;
  border: 1px solid #d7e2f3;
  border-radius: 14px;
  padding: 12px 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  box-shadow: 0 20px 40px rgba(20, 38, 72, 0.16);
}

.mindmap-modal-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  color: #1d2a48;
}

.mindmap-modal-head .open-btn {
  border: 1px solid #c9d5eb;
  background: #fff;
  color: #36507e;
  border-radius: 8px;
  font-size: 12px;
  padding: 7px 11px;
  cursor: pointer;
}

.mindmap-modal-preview {
  overflow: auto;
  flex: 1;
  background: #fbfdff;
  border: 1px solid #dbe4f4;
  border-radius: 10px;
  padding: 14px;
}

@media (max-width: 1200px) {
  .studio-layout {
    display: flex;
    flex-direction: column;
    overflow: auto;
  }

  .left-column {
    order: 1;
    flex: initial;
    max-width: none;
    overflow: visible;
  }

  .right-column {
    order: 2;
    flex: initial;
    max-width: none;
    overflow: visible;
  }

  .app-shell {
    height: auto;
    min-height: 100vh;
  }

  .mindmap-modal {
    padding: 12px;
  }
}

@media (max-width: 960px) {
  .app-shell {
    padding: 10px;
    gap: 8px;
  }

  .studio-layout {
    gap: 8px;
  }
}
</style>
