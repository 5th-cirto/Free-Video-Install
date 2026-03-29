<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'

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

function formatDuration(seconds) {
  if (!seconds || Number.isNaN(seconds)) return '--:--'
  const total = Math.floor(seconds)
  const hours = Math.floor(total / 3600)
  const minutes = Math.floor((total % 3600) / 60)
  const secs = total % 60
  if (hours > 0) return `${hours}:${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')}`
  return `${minutes}:${String(secs).padStart(2, '0')}`
}

function formatBytes(size) {
  if (!size || Number.isNaN(size)) return '未知'
  const units = ['B', 'KB', 'MB', 'GB']
  let value = size
  let unit = 0
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024
    unit += 1
  }
  return `${value.toFixed(value >= 10 ? 0 : 1)} ${units[unit]}`
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
    theme: 'dark',
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
    <header class="top-nav">
      <div class="brand">
        <span class="badge">PRO</span>
        <span>万能视频下载器 · AI 工作台</span>
      </div>
      <div class="cta">解析 · 下载 · 总结 · 导图导出</div>
    </header>

    <section class="studio-layout">
      <aside class="left-pane panel">
        <div class="panel-head">
          <h2>下载工作台</h2>
          <div class="mode-switch">
            <button :class="{ active: mode === 'single' }" @click="mode = 'single'">单条</button>
            <button :class="{ active: mode === 'batch' }" @click="mode = 'batch'">批量</button>
          </div>
        </div>

        <div v-if="inspectInfo" class="hero-video">
          <img v-if="inspectInfo.thumbnail" :src="thumbnailUrl(inspectInfo.thumbnail)" alt="thumbnail" />
          <div class="hero-video-info">
            <p class="title">{{ inspectInfo.title || '未命名视频' }}</p>
            <p class="meta">平台: {{ inspectInfo.extractor || '未知' }}</p>
            <p class="meta">时长: {{ formatDuration(inspectInfo.duration) }}</p>
            <p class="meta">可用格式: {{ inspectInfo.formats?.length || 0 }}</p>
          </div>
        </div>
        <div v-else class="empty">先输入视频链接并解析，右侧会自动开始 AI 总结。</div>

        <div v-if="mode === 'single'" class="field-group">
          <label>视频链接</label>
          <input v-model="singleUrl" type="text" placeholder="粘贴视频链接，如 https://..." />
          <button class="action" :disabled="inspectLoading" @click="inspectVideo">
            {{ inspectLoading ? '解析中...' : '解析视频信息 + 自动AI总结' }}
          </button>
          <p v-if="inspectError" class="error">{{ inspectError }}</p>
        </div>

        <div v-else class="field-group">
          <label>批量链接（每行一条）</label>
          <textarea
            v-model="batchInput"
            rows="6"
            placeholder="https://example.com/video-1&#10;https://example.com/video-2"
          />
          <p class="hint">当前识别 {{ parsedBatchUrls.length }} 条链接</p>
        </div>

        <div class="field-group">
          <label>目标格式（可选）</label>
          <select v-model="selectedFormatId">
            <option value="">自动选择（推荐）</option>
            <option
              v-for="fmt in inspectInfo?.formats || []"
              :key="`${fmt.format_id}-${fmt.ext}`"
              :value="fmt.format_id"
            >
              {{ fmt.format_id }} · {{ fmt.ext }} · {{ fmt.resolution || '未知分辨率' }} ·
              {{ fmt.vcodec === 'none' ? '仅音频' : fmt.acodec === 'none' ? '仅视频' : '音视频' }}
            </option>
          </select>
        </div>

        <div class="submit-row">
          <button
            v-if="mode === 'single'"
            class="action strong"
            :disabled="actionLoading || !singleUrl.trim()"
            @click="createSingleDownload"
          >
            {{ actionLoading ? '提交中...' : '开始下载当前视频' }}
          </button>
          <button v-else class="action strong" :disabled="actionLoading" @click="createBatchDownload">
            {{ actionLoading ? '提交中...' : '开始批量下载' }}
          </button>
          <p v-if="actionError" class="error">{{ actionError }}</p>
        </div>

        <p v-if="downloadsDir" class="hint">默认下载目录：{{ downloadsDir }}</p>

        <div v-if="inspectInfo?.formats?.length" class="formats">
          <h3>格式预览</h3>
          <p v-if="inspectInfo.is_adaptive_only" class="hint">
            当前为分离流，下载时会自动合并音视频。
          </p>
          <div class="format-row" v-for="fmt in inspectInfo.formats.slice(0, 8)" :key="fmt.format_id">
            <span>{{ fmt.format_id }}</span>
            <span>{{ fmt.ext }}</span>
            <span>{{ fmt.resolution || '-' }}</span>
            <span>{{ formatBytes(fmt.filesize) }}</span>
          </div>
        </div>
      </aside>

      <section class="right-pane panel">
        <div class="panel-head">
          <h2>AI 总结结果</h2>
          <div class="status-tags">
            <span v-if="aiStage">阶段 {{ aiStage }}</span>
            <span v-if="aiLoading">生成中</span>
          </div>
        </div>

        <p v-if="aiError" class="error">{{ aiError }}</p>

        <div class="result-tabs">
          <button :class="{ active: aiViewTab === 'summary' }" @click="aiViewTab = 'summary'">总结摘要</button>
          <button :class="{ active: aiViewTab === 'outline' }" @click="aiViewTab = 'outline'">章节总结</button>
          <button :class="{ active: aiViewTab === 'mindmap' }" @click="aiViewTab = 'mindmap'">思维导图</button>
          <button :class="{ active: aiViewTab === 'subtitle' }" @click="aiViewTab = 'subtitle'">字幕内容</button>
        </div>

        <div class="result-body" v-if="hasAiContent">
          <div v-if="aiViewTab === 'summary'">
            <p class="meta"><strong>总结：</strong></p>
            <p class="content-text">{{ aiStreamingSummary || '等待结构化总结输出...' }}</p>
            <div class="list-box" v-if="aiStreamingKeyPoints.length">
              <p class="meta"><strong>核心要点：</strong></p>
              <ul>
                <li v-for="(item, idx) in aiStreamingKeyPoints" :key="`point-${idx}`">{{ item }}</li>
              </ul>
            </div>
            <details v-if="aiRaw" class="raw-debug">
              <summary>查看流式原始输出</summary>
              <pre class="raw-box">{{ aiRaw }}</pre>
            </details>
          </div>

          <div v-if="aiViewTab === 'outline'" class="list-box">
            <p class="meta"><strong>章节大纲：</strong></p>
            <ul v-if="aiDisplayResult.outline?.length">
              <li v-for="(item, idx) in aiDisplayResult.outline" :key="`outline-${idx}`">{{ item }}</li>
            </ul>
            <p v-else class="hint">等待大纲流式输出...</p>
          </div>

          <div v-if="aiViewTab === 'mindmap'" class="list-box">
            <div class="mindmap-actions">
              <button class="open-btn" :disabled="!mindmapSvg" @click="openMindmapFullscreen">全屏预览</button>
              <button class="open-btn" :disabled="!mindmapSvg" @click="downloadMindmapSvg">下载 SVG</button>
            </div>
            <div v-if="mindmapSvg" class="mindmap-preview" v-html="mindmapSvg"></div>
            <p v-else class="hint">等待导图渲染...</p>
            <p v-if="mindmapRenderHint" class="hint">{{ mindmapRenderHint }}</p>
            <p v-if="mindmapRenderError" class="error">{{ mindmapRenderError }}</p>
          </div>

          <div v-if="aiViewTab === 'subtitle'" class="list-box">
            <p class="meta"><strong>字幕分段：</strong></p>
            <div class="mindmap-actions">
              <button class="open-btn" @click="downloadSubtitleFile('txt')">下载 TXT</button>
              <button class="open-btn" @click="downloadSubtitleFile('srt')">下载 SRT</button>
              <button class="open-btn" @click="downloadSubtitleFile('vtt')">下载 VTT</button>
            </div>
            <div class="segments-box" v-if="aiResult?.subtitle_segments?.length">
              <p v-for="(seg, idx) in aiResult.subtitle_segments" :key="`seg-${idx}`" class="segment-line">
                [{{ formatTimestamp(seg.start) }} - {{ formatTimestamp(seg.end) }}] {{ seg.text }}
              </p>
            </div>
            <p v-else class="hint">字幕会在最终结果阶段展示。</p>
          </div>
        </div>
        <div v-else class="empty">等待解析后自动生成 AI 总结。</div>
      </section>
    </section>

    <section class="panel tasks-panel">
      <div class="panel-head">
        <h2>任务中心</h2>
        <div class="status-tags">
          <span>进行中 {{ runningCount }}</span>
          <span>成功 {{ successCount }}</span>
          <span>失败 {{ failedCount }}</span>
        </div>
      </div>
      <div v-if="tasks.length === 0" class="empty">暂无下载任务</div>
      <div v-else class="task-list">
        <article v-for="task in tasks" :key="task.task_id" class="task-item">
          <div class="task-top">
            <strong>{{ task.payload?.url || 'unknown url' }}</strong>
            <span :class="['pill', task.status]">{{ task.status }}</span>
          </div>
          <div class="progress"><div class="bar" :style="{ width: `${Math.round(task.progress || 0)}%` }" /></div>
          <div class="task-meta">
            <span>{{ Math.round(task.progress || 0) }}%</span>
            <span v-if="task.result?.filepath">文件: {{ task.result.filepath }}</span>
            <button
              v-if="task.result?.filepath && task.status === 'success'"
              class="open-btn"
              @click="openLocalPath(task.result.filepath)"
            >
              打开文件位置
            </button>
            <span v-else-if="task.error" class="error">原因: {{ task.error }}</span>
          </div>
        </article>
      </div>
    </section>

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
@import url('https://fonts.googleapis.com/css2?family=Lexend:wght@400;600;700;800&family=Chivo:wght@400;700&display=swap');

:global(body) {
  margin: 0;
  font-family: 'Chivo', sans-serif;
  background:
    radial-gradient(circle at 8% -10%, rgba(62, 106, 255, 0.3), transparent 45%),
    radial-gradient(circle at 92% -15%, rgba(255, 32, 164, 0.22), transparent 45%),
    #060911;
  color: #edf2ff;
}

.app-shell {
  min-height: 100vh;
  max-width: 1460px;
  margin: 0 auto;
  padding: 18px 18px 28px;
}

.top-nav {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
}

.brand {
  display: flex;
  gap: 10px;
  align-items: center;
  font-family: 'Lexend', sans-serif;
  font-weight: 700;
}

.badge {
  background: linear-gradient(130deg, #5ffff0, #7e68ff);
  color: #071427;
  border-radius: 999px;
  padding: 4px 8px;
  font-size: 11px;
  font-weight: 800;
}

.cta {
  color: #bdc8ff;
  font-size: 13px;
}

.studio-layout {
  display: grid;
  grid-template-columns: 420px 1fr;
  gap: 12px;
}

.panel {
  background: linear-gradient(145deg, rgba(11, 15, 26, 0.95), rgba(18, 22, 36, 0.94));
  border: 1px solid rgba(113, 132, 255, 0.26);
  border-radius: 14px;
  padding: 14px;
  box-shadow:
    0 14px 32px rgba(0, 0, 0, 0.45),
    inset 0 1px 0 rgba(255, 255, 255, 0.04);
}

.panel-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.panel h2 {
  margin: 0;
  font-family: 'Lexend', sans-serif;
  font-size: 18px;
}

.left-pane {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.hero-video {
  border: 1px solid rgba(114, 132, 255, 0.25);
  border-radius: 10px;
  overflow: hidden;
  background: rgba(8, 11, 20, 0.78);
}

.hero-video img {
  width: 100%;
  aspect-ratio: 16 / 9;
  object-fit: cover;
}

.hero-video-info {
  padding: 10px;
}

.mode-switch {
  background: rgba(53, 67, 123, 0.6);
  border-radius: 999px;
  padding: 3px;
  display: flex;
  gap: 4px;
}

.mode-switch button,
.result-tabs button {
  border: 0;
  background: transparent;
  color: #b3bfef;
  cursor: pointer;
  border-radius: 999px;
  padding: 6px 11px;
}

.mode-switch .active,
.result-tabs .active {
  background: linear-gradient(130deg, #5f83ff, #f73eb7);
  color: #fff;
}

.field-group {
  display: grid;
  gap: 7px;
}

.field-group.compact {
  margin-bottom: 6px;
}

label {
  color: #95a4e6;
  font-size: 12px;
}

input,
textarea,
select {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid rgba(90, 108, 181, 0.72);
  border-radius: 10px;
  background: #0a1020;
  color: #eef2ff;
  padding: 10px 11px;
  font-size: 13px;
  outline: none;
}

input[readonly] {
  opacity: 0.85;
}

input:focus,
textarea:focus,
select:focus {
  border-color: #6f8fff;
  box-shadow: 0 0 0 2px rgba(111, 143, 255, 0.24);
}

.action,
.open-btn {
  border: 0;
  border-radius: 10px;
  cursor: pointer;
  font-size: 13px;
}

.action {
  background: #33467f;
  color: #fff;
  font-weight: 700;
  padding: 10px 13px;
}

.action.strong {
  background: linear-gradient(130deg, #5ffff0, #5f81ff 65%, #f33db6);
  color: #071224;
}

.action:disabled,
.open-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.open-btn {
  background: rgba(16, 23, 45, 0.95);
  color: #c3d0ff;
  border: 1px solid rgba(96, 123, 239, 0.48);
  padding: 7px 10px;
}

.submit-row {
  display: grid;
  gap: 7px;
}

.meta {
  margin: 0;
  color: #a9b7e9;
  font-size: 13px;
}

.title {
  margin: 0 0 4px;
  font-weight: 700;
  font-size: 15px;
}

.hint {
  margin: 0;
  color: #93a4e2;
  font-size: 12px;
}

.error {
  margin: 0;
  color: #ff9db5;
  font-size: 12px;
}

.formats h3 {
  margin: 0 0 8px;
  font-size: 13px;
  color: #c4d1ff;
}

.format-row {
  display: grid;
  grid-template-columns: 0.85fr 0.5fr 0.95fr 0.7fr;
  gap: 8px;
  font-size: 12px;
  padding: 7px 9px;
  background: rgba(22, 30, 56, 0.82);
  border-radius: 8px;
  margin-bottom: 6px;
}

.right-pane {
  min-height: 700px;
  display: flex;
  flex-direction: column;
}

.status-tags {
  display: flex;
  gap: 8px;
}

.status-tags span {
  border: 1px solid rgba(107, 127, 230, 0.35);
  background: rgba(32, 43, 84, 0.65);
  border-radius: 999px;
  padding: 5px 8px;
  font-size: 11px;
  color: #bcd0ff;
}

.summary-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin: 4px 0 8px;
}

.result-tabs {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  background: rgba(23, 31, 56, 0.72);
  border: 1px solid rgba(106, 127, 232, 0.26);
  border-radius: 999px;
  padding: 3px;
  width: fit-content;
  margin-bottom: 10px;
}

.result-body {
  border: 1px solid rgba(106, 124, 216, 0.28);
  background: rgba(7, 12, 24, 0.75);
  border-radius: 10px;
  padding: 11px;
  min-height: 470px;
}

.content-text {
  margin: 6px 0 0;
  font-size: 14px;
  line-height: 1.7;
  color: #d8e0ff;
}

.raw-box {
  white-space: pre-wrap;
  background: rgba(11, 18, 36, 0.85);
  border: 1px solid rgba(95, 118, 210, 0.24);
  border-radius: 10px;
  padding: 10px;
  margin-bottom: 10px;
  color: #dbe3ff;
  font-size: 12px;
  max-height: 180px;
  overflow: auto;
}

.raw-debug {
  margin-top: 10px;
}

.raw-debug summary {
  cursor: pointer;
  color: #9eb2ff;
  font-size: 12px;
}

.list-box ul {
  margin: 7px 0 0;
  padding-left: 18px;
}

.list-box li {
  color: #d6deff;
  line-height: 1.7;
  margin-bottom: 4px;
  font-size: 13px;
}

.mindmap-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 0 0 8px;
}

.mindmap-preview {
  border: 1px solid rgba(107, 127, 228, 0.22);
  border-radius: 10px;
  background: rgba(10, 16, 31, 0.82);
  padding: 10px;
  overflow: auto;
}

.segments-box {
  max-height: 470px;
  overflow: auto;
  border: 1px solid rgba(102, 121, 218, 0.24);
  border-radius: 10px;
  padding: 10px;
  background: rgba(10, 15, 30, 0.82);
}

.segment-line {
  margin: 0 0 7px;
  color: #d5defe;
  line-height: 1.55;
  font-size: 12px;
}

.tasks-panel {
  margin-top: 12px;
}

.task-list {
  display: grid;
  gap: 8px;
}

.task-item {
  background: rgba(12, 18, 34, 0.85);
  border: 1px solid rgba(105, 125, 226, 0.22);
  border-radius: 10px;
  padding: 9px;
}

.task-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  font-size: 13px;
}

.pill {
  border-radius: 999px;
  padding: 4px 8px;
  font-size: 11px;
}

.pill.queued,
.pill.running {
  color: #78e7ff;
  background: rgba(0, 186, 255, 0.14);
}

.pill.success {
  color: #8af9cb;
  background: rgba(62, 245, 163, 0.14);
}

.pill.failed {
  color: #ff9cb4;
  background: rgba(255, 97, 132, 0.14);
}

.progress {
  margin-top: 8px;
  width: 100%;
  height: 7px;
  border-radius: 999px;
  overflow: hidden;
  background: #121d3f;
}

.bar {
  height: 100%;
  background: linear-gradient(90deg, #5ff3ff, #5f81ff, #f83fb8);
}

.task-meta {
  margin-top: 7px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  font-size: 12px;
  color: #a9b7e9;
}

.empty {
  color: #9baded;
  font-size: 13px;
  padding: 10px 0;
}

.mindmap-modal {
  position: fixed;
  inset: 0;
  z-index: 50;
  background: rgba(2, 7, 20, 0.86);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 22px;
}

.mindmap-modal-content {
  width: min(1320px, 100%);
  max-height: calc(100vh - 44px);
  background: rgba(8, 14, 32, 0.98);
  border: 1px solid rgba(117, 147, 255, 0.35);
  border-radius: 14px;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.mindmap-modal-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.mindmap-modal-preview {
  overflow: auto;
  flex: 1;
  background: rgba(13, 20, 43, 0.85);
  border: 1px solid rgba(95, 128, 255, 0.2);
  border-radius: 10px;
  padding: 14px;
}

@media (max-width: 1200px) {
  .studio-layout {
    grid-template-columns: 1fr;
  }
  .right-pane {
    min-height: auto;
  }
}
</style>
