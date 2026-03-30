import { computed, ref, watch } from 'vue'
import { aiSummaryStreamApi } from '../api/aiSummary'
import { apiBase, axios } from '../api/client'
import { downloadSubtitleApi } from '../api/video'
import { extractFilename, triggerBlobDownload } from '../utils/download'
import { getAxiosDetail, getAxiosMessage } from '../utils/axiosErrors'
import { formatSubtitleTime } from '../utils/format'
import { parseSseMessage } from '../utils/sse'

export function useAiSummary({ singleUrl, openAuthDialog }) {
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
  const aiViewTab = ref('summary')

  const mindmapSvg = ref('')
  const mindmapRenderError = ref('')
  const mindmapRenderHint = ref('')
  const mindmapFullscreen = ref(false)
  let mermaidInstance = null

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
          const responseText = event.event?.target?.responseText || event.currentTarget?.responseText || ''
          if (typeof responseText !== 'string') return
          if (responseText.length <= processedLength) return
          buffer += responseText.slice(processedLength)
          processedLength = responseText.length
          flushSseBuffer()
        },
      )
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

  function downloadMindmapSvg() {
    try {
      const svgText = getMindmapSvgText()
      const blob = new Blob([svgText], { type: 'image/svg+xml;charset=utf-8' })
      triggerBlobDownload(blob, 'mindmap.svg')
    } catch (error) {
      aiError.value = error.message || '导出 SVG 失败'
    }
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

  return {
    aiLanguage,
    aiLoading,
    aiError,
    aiQuotaExceeded,
    aiStage,
    aiRaw,
    aiResult,
    aiCurrentUrl,
    aiViewTab,
    mindmapSvg,
    mindmapRenderError,
    mindmapRenderHint,
    mindmapFullscreen,
    aiDisplayResult,
    aiStreamingSummary,
    aiStreamingKeyPoints,
    hasAiContent,
    resetAiState,
    startAiSummaryStream,
    openMindmapFullscreen,
    closeMindmapFullscreen,
    downloadMindmapSvg,
    downloadSubtitleFile,
  }
}
