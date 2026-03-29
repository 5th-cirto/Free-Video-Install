<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import axios from 'axios'
import DownloadPanel from './components/DownloadPanel.vue'
import StudioHeader from './components/StudioHeader.vue'
import SummaryPanel from './components/SummaryPanel.vue'
import TaskCenterPanel from './components/TaskCenterPanel.vue'

// 后端 API 地址：支持通过 VITE_API_BASE 覆盖，默认本地 8000。
const apiBase = import.meta.env.VITE_API_BASE || 'http://localhost:8000'
// Axios 实例：统一 baseURL 与请求头，便于后续集中扩展（如拦截器）。
const apiClient = axios.create({
  baseURL: apiBase,
  headers: { 'Content-Type': 'application/json' },
})

// =============================
// 下载工作台状态
// =============================
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

// =============================
// AI 总结状态
// =============================
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

// =============================
// 任务中心状态
// =============================
const tasks = ref([])
let pollTimer = null

// 批量输入拆分为 URL 数组，供批量下载接口直接使用。
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

// AI 展示优先使用最终结果；流式中间态作为回退。
const aiDisplayResult = computed(() => aiResult.value || aiPartialResult.value)

// 从 partial_result 中读取摘要；若中间态缺失，再尝试从 delta 拼接文本中提取。
const aiStreamingSummary = computed(() => {
  const partial = String(aiDisplayResult.value?.summary || '').trim()
  if (partial) return partial
  const raw = String(aiRaw.value || '')
  if (!raw) return ''
  const match = raw.match(/"summary"\s*:\s*"([\s\S]*?)(?:"\s*,\s*"outline"|$)/)
  if (!match?.[1]) return ''
  return match[1].replace(/\\"/g, '"').replace(/\\n/g, '\n').trim()
})

// 核心要点同理：优先结构化中间态，回退到 raw 文本解析。
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

// 判断 AI 区是否有可展示内容，用于决定显示“结果区”还是“空态文案”。
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

// 将秒数格式化为 mm:ss / hh:mm:ss。
function formatDuration(seconds) {
  if (!seconds || Number.isNaN(seconds)) return '--:--'
  const total = Math.floor(seconds)
  const hours = Math.floor(total / 3600)
  const minutes = Math.floor((total % 3600) / 60)
  const secs = total % 60
  if (hours > 0) return `${hours}:${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')}`
  return `${minutes}:${String(secs).padStart(2, '0')}`
}

// 字幕时间格式化（用于页面展示）。
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

// 封面统一走后端代理，避免第三方跨域或防盗链导致的加载失败。
function thumbnailUrl(rawUrl) {
  if (!rawUrl) return ''
  return `${apiBase}/api/video/thumbnail?url=${encodeURIComponent(rawUrl)}`
}

// 从 axios 异常中提取可读错误信息，优先后端 detail 字段。
function getAxiosMessage(error, fallback = '请求失败') {
  if (!axios.isAxiosError(error)) {
    return String(error?.message || fallback)
  }
  const detail = error.response?.data?.detail
  const message = error.response?.data?.message
  if (typeof detail === 'string' && detail.trim()) return detail
  if (typeof message === 'string' && message.trim()) return message
  if (typeof error.message === 'string' && error.message.trim()) return error.message
  return fallback
}

// 通用 JSON API 调用封装（axios 版本）。
async function callApi(path, payload = null, method = 'GET') {
  try {
    const response = await apiClient.request({
      url: path,
      method,
      data: payload || undefined,
    })
    return response.data
  } catch (error) {
    const text = getAxiosMessage(error)
    if (text.includes('Network Error') || text.includes('ERR_NETWORK')) {
      throw new Error(`无法连接后端接口(${apiBase})。请确认后端已启动，并允许当前前端端口跨域访问。`)
    }
    throw new Error(text)
  }
}

// 解析视频信息，并在成功后自动触发 AI 总结（单条模式主流程）。
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

// 创建单条下载任务。
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

// 创建批量下载任务。
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

// 拉取任务列表（用于任务中心 + 顶部统计）。
async function loadTasks() {
  try {
    const resp = await callApi('/api/video/tasks')
    tasks.value = resp?.data?.tasks || []
  } catch (_error) {
    // Keep silent for polling to avoid noisy UI.
  }
}

// 拉取运行时配置（主要是默认下载目录）。
async function loadRuntimeConfig() {
  try {
    const resp = await callApi('/api/video/config')
    downloadsDir.value = resp?.data?.downloads_dir || ''
  } catch (_error) {
    downloadsDir.value = ''
  }
}

// 打开本地路径（由后端执行系统命令）。
async function openLocalPath(path) {
  if (!path) return
  try {
    await callApi('/api/video/open-path?path=' + encodeURIComponent(path), null, 'POST')
  } catch (error) {
    actionError.value = error.message
  }
}

// 开始一次新的 AI 总结前，清空旧状态，避免页面残留。
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

// 解析 SSE 文本包，提取 event 和 data。
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

// AI SSE 主流程：
// 1) 发起流式请求
// 2) 逐包解析 stage/delta/partial_result/result/error/done
// 3) 驱动右侧总结区实时渲染
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
    let buffer = ''
    let processedLength = 0
    const flushSseBuffer = () => {
      let splitIndex = buffer.indexOf('\n\n')
      while (splitIndex !== -1) {
        const packet = buffer.slice(0, splitIndex)
        buffer = buffer.slice(splitIndex + 2)
        if (!packet.trim()) {
          splitIndex = buffer.indexOf('\n\n')
          continue
        }
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

    await apiClient.post(
      '/api/ai-summary/stream',
      {
        url: targetUrl,
        language: aiLanguage.value.trim() || null,
      },
      {
        responseType: 'text',
        onDownloadProgress: (event) => {
          // axios 在浏览器内通过 XHR 提供 responseText，可用来模拟增量 SSE 解析。
          const responseText = event.event?.target?.responseText || event.currentTarget?.responseText || ''
          if (typeof responseText !== 'string') return
          if (responseText.length <= processedLength) return
          buffer += responseText.slice(processedLength)
          processedLength = responseText.length
          flushSseBuffer()
        },
      },
    )
    // 兜底：请求完成后再冲洗一次缓冲区，避免尾包漏解析。
    flushSseBuffer()
  } catch (error) {
    const text = getAxiosMessage(error, 'SSE连接失败')
    if (text.includes('Network Error') || text.includes('ERR_NETWORK')) {
      aiError.value = `AI总结请求无法连接后端(${apiBase})，请检查后端服务与跨域端口配置。`
    } else {
      aiError.value = text
    }
  } finally {
    aiLoading.value = false
  }
}

// 延迟加载 Mermaid，首次使用时初始化，减少首屏开销。
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

// 根据 mindmap_mermaid 渲染 SVG；失败时尝试用大纲重建导图。
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

// 当模型返回导图语法不稳定时，使用大纲和要点兜底构造简版导图。
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

// 监听导图源码变化并自动重绘。
watch(
  () => aiDisplayResult.value?.mindmap_mermaid,
  (nextValue) => {
    renderMindmapSvg(nextValue || '')
  },
)

// 有任务运行时自动展开任务中心，降低用户错过进度变化的概率。
watch(runningCount, (count) => {
  if (count > 0) {
    taskCenterExpanded.value = true
  }
})

// 导图全屏弹窗开关。
function openMindmapFullscreen() {
  if (!mindmapSvg.value) return
  mindmapFullscreen.value = true
}

function closeMindmapFullscreen() {
  mindmapFullscreen.value = false
}

// 确保导出 SVG 含命名空间，兼容更多查看器。
function getMindmapSvgText() {
  if (!mindmapSvg.value) throw new Error('当前无可导出的思维导图')
  if (mindmapSvg.value.includes('xmlns=')) return mindmapSvg.value
  return mindmapSvg.value.replace('<svg ', '<svg xmlns="http://www.w3.org/2000/svg" ')
}

// 通用 Blob 下载函数（导图和字幕下载都复用）。
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

// 导出当前导图为 SVG 文件。
function downloadMindmapSvg() {
  try {
    const svgText = getMindmapSvgText()
    const blob = new Blob([svgText], { type: 'image/svg+xml;charset=utf-8' })
    triggerBlobDownload(blob, 'mindmap.svg')
  } catch (error) {
    aiError.value = error.message || '导出 SVG 失败'
  }
}

// 从响应头解析文件名。
function extractFilename(disposition, fallback) {
  const match = /filename="?([^"]+)"?/i.exec(disposition || '')
  return match?.[1] || fallback
}

// 字幕时间格式化（SRT 与 VTT 分隔符不同）。
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

// 基于 aiResult 组装本地字幕内容（后端不可用时兜底下载）。
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

// 当后端返回 404 时，使用前端已有字幕结果导出。
function downloadSubtitleFromLocalResult(format) {
  const content = buildLocalSubtitle(format)
  if (!content) {
    throw new Error('当前没有可导出的字幕内容，请先完成 AI 总结。')
  }
  const blob = new Blob([content], { type: 'text/plain;charset=utf-8' })
  triggerBlobDownload(blob, `subtitle.${format}`)
}

// 优先调用后端字幕下载接口；接口不可用时回退本地导出。
async function downloadSubtitleFile(format) {
  const targetUrl = aiCurrentUrl.value.trim() || singleUrl.value.trim()
  if (!targetUrl) {
    aiError.value = '请先输入并解析视频链接'
    return
  }
  aiError.value = ''
  try {
    const response = await apiClient.post(
      '/api/video/subtitles/download',
      {
        url: targetUrl,
        language: aiLanguage.value.trim() || null,
        format,
      },
      { responseType: 'blob' },
    )
    const disposition = response.headers?.['content-disposition'] || ''
    triggerBlobDownload(response.data, extractFilename(disposition, `subtitle.${format}`))
  } catch (error) {
    if (axios.isAxiosError(error) && error.response?.status === 404) {
      downloadSubtitleFromLocalResult(format)
      return
    }
    aiError.value = getAxiosMessage(error, '字幕下载失败')
  }
}

// 页面生命周期：
// - mounted: 加载配置与任务，并启动轮询
// - unmounted: 释放轮询
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
  <!-- 页面壳层：顶部状态栏 + 双栏工作区 + 可折叠任务中心 -->
  <div class="app-shell">
    <StudioHeader :running-count="runningCount" :success-count="successCount" :failed-count="failedCount" />

    <!-- 双栏工作区：左下载、右总结（移动端改为单列） -->
    <section class="studio-layout">
      <!-- 右侧总结面板（桌面端显示在右侧） -->
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

      <!-- 左侧下载面板 -->
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

    <!-- 次级任务中心：默认折叠 -->
    <TaskCenterPanel
      :expanded="taskCenterExpanded"
      :running-count="runningCount"
      :success-count="successCount"
      :failed-count="failedCount"
      :tasks="tasks"
      @toggle="taskCenterExpanded = !taskCenterExpanded"
      @open-local-path="openLocalPath"
    />

    <!-- 导图全屏弹窗 -->
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

/* 全局页面背景与基础字体 */
:global(body) {
  margin: 0;
  font-family: 'Manrope', sans-serif;
  color: #192847;
  background:
    radial-gradient(circle at 8% -18%, rgba(64, 132, 255, 0.14), transparent 46%),
    radial-gradient(circle at 100% -12%, rgba(86, 189, 255, 0.12), transparent 42%),
    #f2f6fc;
}

/* 页面根容器 */
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

/* 桌面端双栏布局 */
.studio-layout {
  display: flex;
  gap: 10px;
  flex: 1;
  min-height: 0;
  align-items: stretch;
}

/* 左栏（下载工作台） */
.left-column {
  order: 1;
  flex: 0 0 40%;
  max-width: 40%;
  min-height: 0;
  overflow: auto;
}

/* 右栏（AI 总结） */
.right-column {
  order: 2;
  flex: 1 1 60%;
  max-width: 60%;
  min-height: 0;
  overflow: hidden;
}

/* 导图全屏弹窗 */
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

/* 平板与小屏：改为单列，并保持下载工作台在上 */
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

/* 手机端进一步压缩边距 */
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
