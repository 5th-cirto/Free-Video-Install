<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import axios from 'axios'
import { aiSummaryStreamApi } from './api/aiSummary'
import { ordersApi, checkoutSessionApi, membershipStatusApi } from './api/billing'
import { configureApiClient, apiBase } from './api/client'
import { loginApi, meApi, registerApi, requestPasswordResetApi, resetPasswordApi } from './api/auth'
import {
  buildThumbnailUrl,
  createBatchDownloadApi,
  createDownloadApi,
  downloadSubtitleApi,
  inspectVideoApi,
  openPathApi,
  runtimeConfigApi,
  tasksApi,
} from './api/video'
import { extractFilename, triggerBlobDownload } from './utils/download'
import { getAxiosDetail, getAxiosMessage } from './utils/axiosErrors'
import { formatDuration, formatSubtitleTime, formatTimestamp } from './utils/format'
import { parseSseMessage } from './utils/sse'
import DownloadPanel from './components/DownloadPanel.vue'
import InPageNav from './components/InPageNav.vue'
import LandingSeoSections from './components/LandingSeoSections.vue'
import SiteSeoFooter from './components/SiteSeoFooter.vue'
import TechCredibilityStrip from './components/TechCredibilityStrip.vue'
import StudioHeader from './components/StudioHeader.vue'
import SummaryPanel from './components/SummaryPanel.vue'
import TaskCenterPanel from './components/TaskCenterPanel.vue'
import AuthDialog from './components/dialogs/AuthDialog.vue'
import BillingDialog from './components/dialogs/BillingDialog.vue'
import MindmapDialog from './components/dialogs/MindmapDialog.vue'

const ACCESS_TOKEN_KEY = 'uvd_access_token'
const savedToken = localStorage.getItem(ACCESS_TOKEN_KEY) || ''
const accessToken = ref(savedToken)

// =============================
// 账号 / 会员状态
// =============================
const currentUser = ref(null)
const membershipStatus = ref({
  is_vip: false,
  plan_code: 'free',
  valid_until: '',
})
const billingLoading = ref(false)
const authDialogVisible = ref(false)
const authMode = ref('login')
const authEmail = ref('')
const authPassword = ref('')
const authConfirmPassword = ref('')
const authActionToken = ref('')
const authLoading = ref(false)
const authError = ref('')
const authInfo = ref('')
const billingDialogVisible = ref(false)
const billingHistoryLoading = ref(false)
const billingOrders = ref([])

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
const aiQuotaExceeded = ref(false)
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
const isLoggedIn = computed(() => Boolean(currentUser.value?.email))
const isVipUser = computed(() => Boolean(membershipStatus.value?.is_vip))
const vipValidUntilText = computed(() => membershipStatus.value?.valid_until || '')

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

// 封面统一走后端代理，避免第三方跨域或防盗链导致的加载失败。
function thumbnailUrl(rawUrl) {
  return buildThumbnailUrl(rawUrl)
}

function setAccessToken(token) {
  accessToken.value = token || ''
  if (accessToken.value) {
    localStorage.setItem(ACCESS_TOKEN_KEY, accessToken.value)
  } else {
    localStorage.removeItem(ACCESS_TOKEN_KEY)
  }
}

function clearSession() {
  setAccessToken('')
  currentUser.value = null
  membershipStatus.value = {
    is_vip: false,
    plan_code: 'free',
    valid_until: '',
  }
}

configureApiClient({
  getAccessToken: () => accessToken.value,
  onUnauthorized: clearSession,
})

function openAuthDialog(mode = 'login') {
  authMode.value = mode
  authError.value = ''
  authInfo.value = ''
  authDialogVisible.value = true
}

function closeAuthDialog() {
  authDialogVisible.value = false
  authError.value = ''
  authInfo.value = ''
  authPassword.value = ''
  authConfirmPassword.value = ''
  authActionToken.value = ''
}

function switchAuthMode() {
  if (authMode.value === 'register') authMode.value = 'login'
  else if (authMode.value === 'login') authMode.value = 'register'
  else authMode.value = 'login'
  authError.value = ''
  authInfo.value = ''
  authPassword.value = ''
  authConfirmPassword.value = ''
  authActionToken.value = ''
}

function openBillingDialog() {
  if (!isLoggedIn.value) {
    openAuthDialog('login')
    return
  }
  billingDialogVisible.value = true
  loadBillingOrders()
}

function closeBillingDialog() {
  billingDialogVisible.value = false
}

async function loadMembershipStatus() {
  if (!accessToken.value) return
  try {
    const resp = await membershipStatusApi()
    membershipStatus.value = {
      is_vip: Boolean(resp?.data?.is_vip),
      plan_code: String(resp?.data?.plan_code || 'free'),
      valid_until: String(resp?.data?.valid_until || ''),
    }
  } catch (_error) {
    membershipStatus.value = {
      is_vip: false,
      plan_code: 'free',
      valid_until: '',
    }
  }
}

async function loadCurrentUser() {
  if (!accessToken.value) return
  try {
    const resp = await meApi()
    currentUser.value = {
      user_id: resp?.data?.user_id,
      email: resp?.data?.email || '',
    }
    membershipStatus.value = {
      is_vip: Boolean(resp?.data?.membership?.is_vip),
      plan_code: resp?.data?.membership?.is_vip ? 'vip_1m' : 'free',
      valid_until: String(resp?.data?.membership?.vip_valid_until || ''),
    }
    await loadMembershipStatus()
  } catch (_error) {
    clearSession()
  }
}

async function registerAccount() {
  authError.value = ''
  authInfo.value = ''
  if (!authEmail.value.trim()) {
    authError.value = '请输入邮箱'
    return
  }
  if (authPassword.value.length < 8) {
    authError.value = '密码至少 8 位'
    return
  }
  if (authPassword.value !== authConfirmPassword.value) {
    authError.value = '两次输入密码不一致'
    return
  }
  authLoading.value = true
  try {
    await registerApi({ email: authEmail.value.trim(), password: authPassword.value })
    authMode.value = 'login'
    authInfo.value = '注册成功，请登录。'
    authConfirmPassword.value = ''
  } catch (error) {
    authError.value = error.message || '注册失败'
  } finally {
    authLoading.value = false
  }
}

async function loginAccount() {
  authError.value = ''
  authInfo.value = ''
  authLoading.value = true
  try {
    const resp = await loginApi({ email: authEmail.value.trim(), password: authPassword.value })
    const token = resp?.data?.access_token || ''
    if (!token) throw new Error('登录成功但未返回 token')
    setAccessToken(token)
    await loadCurrentUser()
    closeAuthDialog()
  } catch (error) {
    authError.value = error.message || '登录失败'
  } finally {
    authLoading.value = false
  }
}

async function requestPasswordResetEmail() {
  authError.value = ''
  authInfo.value = ''
  if (!authEmail.value.trim()) {
    authError.value = '请输入邮箱地址后再发送重置邮件'
    return
  }
  authLoading.value = true
  try {
    await requestPasswordResetApi({ email: authEmail.value.trim() })
    authInfo.value = '重置密码邮件已发送，请到邮箱点击链接继续。'
  } catch (error) {
    authError.value = error.message || '发送重置邮件失败'
  } finally {
    authLoading.value = false
  }
}

async function completePasswordReset() {
  authError.value = ''
  authInfo.value = ''
  if (!authActionToken.value.trim()) {
    authError.value = '重置令牌缺失，请重新打开邮箱中的重置链接'
    return
  }
  if (authPassword.value.length < 8) {
    authError.value = '新密码至少 8 位'
    return
  }
  if (authPassword.value !== authConfirmPassword.value) {
    authError.value = '两次输入密码不一致'
    return
  }
  authLoading.value = true
  try {
    await resetPasswordApi({ token: authActionToken.value.trim(), new_password: authPassword.value })
    authMode.value = 'login'
    authActionToken.value = ''
    authPassword.value = ''
    authConfirmPassword.value = ''
    authInfo.value = '密码重置成功，请使用新密码登录。'
  } catch (error) {
    authError.value = error.message || '密码重置失败'
  } finally {
    authLoading.value = false
  }
}

async function loadBillingOrders() {
  if (!isLoggedIn.value) return
  billingHistoryLoading.value = true
  try {
    const resp = await ordersApi()
    billingOrders.value = resp?.data?.orders || []
  } catch (error) {
    actionError.value = error.message || '加载账单记录失败'
  } finally {
    billingHistoryLoading.value = false
  }
}

function logoutAccount() {
  clearSession()
}

async function startVipCheckout() {
  if (!isLoggedIn.value) {
    openAuthDialog('login')
    return
  }
  billingLoading.value = true
  actionError.value = ''
  try {
    const resp = await checkoutSessionApi({ plan_code: 'vip_1m', idempotency_key: `web-${Date.now()}` })
    const url = resp?.data?.checkout_url || ''
    if (!url) throw new Error('未获取到支付链接')
    window.location.href = url
  } catch (error) {
    actionError.value = error.message || '创建支付会话失败'
  } finally {
    billingLoading.value = false
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
    const resp = await inspectVideoApi({ url: singleUrl.value.trim() })
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
    await createDownloadApi({ url: singleUrl.value.trim(), format_id: selectedFormatId.value || null })
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
    await createBatchDownloadApi({
      urls: parsedBatchUrls.value,
      format_id: selectedFormatId.value || null,
    })
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
    const resp = await tasksApi()
    tasks.value = resp?.data?.tasks || []
  } catch (_error) {
    // Keep silent for polling to avoid noisy UI.
  }
}

// 拉取运行时配置（主要是默认下载目录）。
async function loadRuntimeConfig() {
  try {
    const resp = await runtimeConfigApi()
    downloadsDir.value = resp?.data?.downloads_dir || ''
  } catch (_error) {
    downloadsDir.value = ''
  }
}

// 打开本地路径（由后端执行系统命令）。
async function openLocalPath(path) {
  if (!path) return
  try {
    await openPathApi(path)
  } catch (error) {
    actionError.value = error.message
  }
}

// 开始一次新的 AI 总结前，清空旧状态，避免页面残留。
function resetAiState() {
  aiError.value = ''
  aiQuotaExceeded.value = false
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

    await aiSummaryStreamApi(
      {
        url: targetUrl,
        language: aiLanguage.value.trim() || null,
      },
      (event) => {
        // axios 在浏览器内通过 XHR 提供 responseText，可用来模拟增量 SSE 解析。
        const responseText = event.event?.target?.responseText || event.currentTarget?.responseText || ''
        if (typeof responseText !== 'string') return
        if (responseText.length <= processedLength) return
        buffer += responseText.slice(processedLength)
        processedLength = responseText.length
        flushSseBuffer()
      },
    )
    // 兜底：请求完成后再冲洗一次缓冲区，避免尾包漏解析。
    flushSseBuffer()
  } catch (error) {
    if (axios.isAxiosError(error) && error.response?.status === 401) {
      aiError.value = 'AI 总结需要先登录，请先注册/登录账号。'
      openAuthDialog('login')
      return
    }
    const detail = getAxiosDetail(error)
    if (detail?.code === 'AI_DAILY_LIMIT_EXCEEDED') {
      const limit = Number(detail.limit || 0)
      const used = Number(detail.used || 0)
      aiError.value = `今日免费额度已用完 (${used}/${limit})，开通 VIP 后可无限使用。`
      aiQuotaExceeded.value = true
      return
    }
    // Defensive fallback: even if backend detail payload is stripped by an intermediary,
    // treat 403 from AI summary endpoint as quota/auth restriction and show friendly UX.
    if (axios.isAxiosError(error) && error.response?.status === 403) {
      aiError.value = '当前账号今日免费 AI 总结次数已用完，请开通 VIP 继续使用。'
      aiQuotaExceeded.value = true
      return
    }
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

function sanitizeMindmapSource(source) {
  const text = String(source || '').trim()
  if (!text) return ''
  const fencedMatch = text.match(/```(?:mermaid)?\s*([\s\S]*?)```/i)
  const unwrapped = fencedMatch?.[1] ? fencedMatch[1] : text
  return unwrapped
    .replace(/\r\n/g, '\n')
    .replace(/^\uFEFF/, '')
    .trim()
}

function isMermaidErrorSvg(svgText) {
  const text = String(svgText || '')
  if (!text) return false
  return (
    text.includes('Syntax error in text') ||
    text.includes('mermaid version') ||
    text.includes('error-icon') ||
    text.includes('class="error-message"')
  )
}

// 根据 mindmap_mermaid 渲染 SVG；失败时尝试用大纲重建导图。
async function renderMindmapSvg(source) {
  const normalizedSource = sanitizeMindmapSource(source)
  if (!normalizedSource) {
    mindmapSvg.value = ''
    mindmapRenderError.value = ''
    mindmapRenderHint.value = ''
    return
  }
  const fallbackSource = sanitizeMindmapSource(buildFallbackMindmapSource(aiResult.value))
  try {
    const mermaid = await ensureMermaid()
    const id = `mindmap-${Date.now()}`
    const output = await mermaid.render(id, normalizedSource)
    if (isMermaidErrorSvg(output?.svg)) {
      throw new Error('Mermaid 返回语法错误图')
    }
    mindmapSvg.value = output.svg || ''
    mindmapRenderError.value = ''
    mindmapRenderHint.value = ''
  } catch (error) {
    try {
      if (fallbackSource && fallbackSource !== normalizedSource) {
        const mermaid = await ensureMermaid()
        const id = `mindmap-fallback-${Date.now()}`
        const output = await mermaid.render(id, fallbackSource)
        if (isMermaidErrorSvg(output?.svg)) {
          throw new Error('Fallback Mermaid 返回语法错误图')
        }
        mindmapSvg.value = output.svg || ''
        mindmapRenderError.value = ''
        mindmapRenderHint.value = '导图语法异常，已自动回退到大纲导图。'
        return
      }
    } catch (_fallbackError) {
      // Keep original error below.
    }
    mindmapSvg.value = ''
    mindmapRenderHint.value = '导图语法异常，请重试。'
    mindmapRenderError.value = ''
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
    const response = await downloadSubtitleApi({
      url: targetUrl,
      language: aiLanguage.value.trim() || null,
      format,
    })
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
  const params = new URLSearchParams(window.location.search)
  const action = params.get('action') || ''
  const token = params.get('token') || ''
  if (action === 'reset_password' && token) {
    openAuthDialog('reset')
    authActionToken.value = token
    authInfo.value = '请输入新密码完成重置。'
    window.history.replaceState({}, '', window.location.pathname + window.location.hash)
  }

  if (accessToken.value) {
    await loadCurrentUser()
  }
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
    <a class="skip-to-workspace" href="#section-workspace">跳到工作台</a>
    <StudioHeader
      :running-count="runningCount"
      :success-count="successCount"
      :failed-count="failedCount"
      :user-email="currentUser?.email || ''"
      :is-vip="isVipUser"
      :vip-valid-until="vipValidUntilText"
      :billing-loading="billingLoading"
      @login="openAuthDialog('login')"
      @register="openAuthDialog('register')"
      @logout="logoutAccount"
      @open-billing="openBillingDialog"
      @buy-vip="startVipCheckout"
    />

    <InPageNav />

    <main class="studio-main">
    <div id="section-guide" class="anchor-target">
      <LandingSeoSections />
    </div>

    <!--<TechCredibilityStrip />-->

    <!-- 双栏工作区：左下载、右总结（移动端改为单列） -->
    <section
      id="section-workspace"
      class="studio-layout anchor-target"
      aria-label="视频下载与 AI 总结工作台"
    >
      <!-- 右侧总结面板（桌面端显示在右侧） -->
      <SummaryPanel
        class="right-column"
        :ai-stage="aiStage"
        :ai-loading="aiLoading"
        :ai-error="aiError"
        :ai-quota-exceeded="aiQuotaExceeded"
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
        @upgrade-vip="startVipCheckout"
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

    <div id="section-tasks" class="anchor-target">
      <TaskCenterPanel
        :expanded="taskCenterExpanded"
        :running-count="runningCount"
        :success-count="successCount"
        :failed-count="failedCount"
        :tasks="tasks"
        @toggle="taskCenterExpanded = !taskCenterExpanded"
        @open-local-path="openLocalPath"
      />
    </div>

    <div id="section-more" class="anchor-target">
      <SiteSeoFooter />
    </div>
    </main>

    <MindmapDialog
      :visible="mindmapFullscreen"
      :svg="mindmapSvg"
      @update:visible="mindmapFullscreen = $event"
      @close="closeMindmapFullscreen"
    />

    <BillingDialog
      :visible="billingDialogVisible"
      :loading="billingHistoryLoading"
      :orders="billingOrders"
      @update:visible="billingDialogVisible = $event"
      @close="closeBillingDialog"
    />

    <AuthDialog
      :visible="authDialogVisible"
      :mode="authMode"
      :email="authEmail"
      :password="authPassword"
      :confirm-password="authConfirmPassword"
      :action-token="authActionToken"
      :loading="authLoading"
      :error="authError"
      :info="authInfo"
      @update:visible="authDialogVisible = $event"
      @update:email="authEmail = $event"
      @update:password="authPassword = $event"
      @update:confirm-password="authConfirmPassword = $event"
      @update:action-token="authActionToken = $event"
      @close="closeAuthDialog"
      @switch-mode="switchAuthMode"
      @register="registerAccount"
      @login="loginAccount"
      @reset-password="completePasswordReset"
      @request-reset-email="requestPasswordResetEmail"
      @back-login="openAuthDialog('login')"
    />
  </div>
</template>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Lexend:wght@500;700;800&family=Manrope:wght@400;500;600;700&display=swap');

/* 全局页面背景与基础字体 */
:global(html) {
  scroll-behavior: smooth;
}

.skip-to-workspace {
  position: absolute;
  left: -9999px;
  top: 0;
  z-index: 100;
  padding: 10px 14px;
  background: #1f6fff;
  color: #fff;
  font-size: 13px;
  font-weight: 600;
  text-decoration: none;
  border-radius: 0 0 8px 0;
}

.skip-to-workspace:focus {
  left: 14px;
  top: 14px;
}

:global(body) {
  margin: 0;
  font-family: 'Manrope', sans-serif;
  color: #192847;
  background:
    radial-gradient(circle at 8% -18%, rgba(64, 132, 255, 0.14), transparent 46%),
    radial-gradient(circle at 100% -12%, rgba(86, 189, 255, 0.12), transparent 42%),
    #f2f6fc;
}

/* 整页自然滚动，不限制在单一视口高度内 */
.app-shell {
  position: relative;
  min-height: 100vh;
  max-width: 1440px;
  margin: 0 auto;
  padding: 14px 14px 40px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  box-sizing: border-box;
}

/* 主内容区：随文档流增高 */
.studio-main {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.anchor-target {
  scroll-margin-top: 72px;
}

@media (max-width: 960px) {
  .anchor-target {
    scroll-margin-top: 56px;
  }
}

/* 桌面端双栏：给出足够操作高度，超出部分在列内滚动或由页面滚动 */
.studio-layout {
  display: flex;
  gap: 10px;
  align-items: stretch;
  min-height: min(880px, 85vh);
}

/* 左栏（下载工作台） */
.left-column {
  order: 1;
  flex: 0 0 40%;
  max-width: 40%;
  min-height: 0;
  overflow: auto;
  align-self: stretch;
}

/* 右栏（AI 总结） */
.right-column {
  order: 2;
  flex: 1 1 60%;
  max-width: 60%;
  min-height: 0;
  overflow: hidden;
  align-self: stretch;
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

.auth-modal {
  position: fixed;
  inset: 0;
  background: rgba(23, 37, 66, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
  z-index: 80;
}

.auth-modal-card {
  width: min(420px, 100%);
  background: #fff;
  border: 1px solid #d7e2f3;
  border-radius: 14px;
  padding: 16px;
  box-shadow: 0 18px 40px rgba(20, 38, 72, 0.2);
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.auth-modal-card h3 {
  margin: 0;
  color: #162544;
}

.auth-subtitle {
  margin: 0 0 4px;
  color: #617399;
  font-size: 13px;
}

.auth-label {
  color: #2f4773;
  font-size: 12px;
  font-weight: 600;
}

.auth-input {
  border: 1px solid #cfdced;
  border-radius: 10px;
  padding: 9px 10px;
  font-size: 13px;
  color: #1e3359;
  outline: none;
}

.auth-input:focus {
  border-color: #5b8fff;
  box-shadow: 0 0 0 3px rgba(91, 143, 255, 0.2);
}

.auth-error {
  margin: 2px 0;
  color: #cb3b3b;
  font-size: 12px;
}

.auth-info {
  margin: 2px 0;
  color: #1f6fff;
  font-size: 12px;
}

.auth-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 2px;
}

.auth-btn {
  border: 1px solid #cfdced;
  background: #fff;
  color: #31476f;
  border-radius: 10px;
  padding: 7px 11px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}

.auth-btn-primary {
  border-color: #1f6fff;
  background: #1f6fff;
  color: #fff;
}

.auth-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.auth-switch {
  margin-top: 2px;
  border: none;
  background: transparent;
  color: #245fc6;
  font-size: 12px;
  text-align: left;
  cursor: pointer;
  padding: 0;
}

.auth-extra-actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  margin-top: 4px;
}

.auth-link-btn {
  border: none;
  background: transparent;
  color: #395a92;
  font-size: 12px;
  cursor: pointer;
  padding: 0;
}

.billing-card {
  width: min(680px, 100%);
}

.billing-list {
  max-height: 320px;
  overflow: auto;
  border: 1px solid #dbe4f4;
  border-radius: 10px;
  background: #fbfdff;
  padding: 8px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.billing-item {
  border: 1px solid #d5e1f2;
  border-radius: 10px;
  background: #fff;
  padding: 8px 10px;
}

.billing-row {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  color: #25395f;
  font-size: 12px;
}

.billing-meta {
  margin-top: 4px;
  color: #5c7099;
  font-size: 11px;
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
    min-height: 0;
  }

  .left-column {
    min-height: 0;
  }

  .studio-layout {
    min-height: 0;
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
