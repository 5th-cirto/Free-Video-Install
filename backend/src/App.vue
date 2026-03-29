<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'

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

  const response = await fetch(`${apiBase}${path}`, options)
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
        <span>FlowGrab Studio</span>
      </div>
      <div class="cta">极速下载 · 批量处理 · 本地保存</div>
    </header>

    <section class="hero">
      <p class="kicker">Universal Video Downloader</p>
      <h1>一站式下载全网视频，<span>秒级开工</span></h1>
      <p class="sub">
        支持多平台链接解析、格式选择与批量下载。先用 MVP 跑通价值，再接入会员订阅与 AI 增值能力。
      </p>
    </section>

    <section class="workspace">
      <div class="panel input-panel">
        <div class="panel-head">
          <h2>下载工作台</h2>
          <div class="mode-switch">
            <button :class="{ active: mode === 'single' }" @click="mode = 'single'">单条</button>
            <button :class="{ active: mode === 'batch' }" @click="mode = 'batch'">批量</button>
          </div>
        </div>

        <div v-if="mode === 'single'" class="field-group">
          <label>视频链接</label>
          <input v-model="singleUrl" type="text" placeholder="粘贴视频链接，如 https://..." />
          <button class="action" :disabled="inspectLoading" @click="inspectVideo">
            {{ inspectLoading ? '解析中...' : '解析视频信息' }}
          </button>
          <p v-if="inspectError" class="error">{{ inspectError }}</p>
        </div>

        <div v-else class="field-group">
          <label>批量链接（每行一条）</label>
          <textarea
            v-model="batchInput"
            rows="7"
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
            {{ actionLoading ? '提交中...' : '开始下载' }}
          </button>
          <button v-else class="action strong" :disabled="actionLoading" @click="createBatchDownload">
            {{ actionLoading ? '提交中...' : '开始批量下载' }}
          </button>
          <p v-if="actionError" class="error">{{ actionError }}</p>
        </div>
        <p class="hint" v-if="downloadsDir">文件默认保存到：{{ downloadsDir }}</p>
      </div>

      <div class="panel info-panel">
        <h2>解析结果</h2>
        <div v-if="inspectInfo" class="video-card">
          <img v-if="inspectInfo.thumbnail" :src="thumbnailUrl(inspectInfo.thumbnail)" alt="thumbnail" />
          <div>
            <p class="title">{{ inspectInfo.title || '未命名视频' }}</p>
            <p class="meta">
              平台: {{ inspectInfo.extractor || '未知' }} · 时长: {{ formatDuration(inspectInfo.duration) }}
            </p>
            <p class="meta">可用格式: {{ inspectInfo.formats?.length || 0 }} 个</p>
          </div>
        </div>
        <div v-else class="empty">先解析单条链接，可预览标题、时长与可选格式。</div>

        <div v-if="inspectInfo?.formats?.length" class="formats">
          <h3>格式预览</h3>
          <p v-if="inspectInfo.is_adaptive_only" class="hint">
            当前视频平台只提供分离流（音频/视频分开）。下载时系统会自动合并为可播放文件。
          </p>
          <div class="format-row" v-for="fmt in inspectInfo.formats.slice(0, 8)" :key="fmt.format_id">
            <span>{{ fmt.format_id }}</span>
            <span>{{ fmt.ext }}</span>
            <span>{{ fmt.resolution || '-' }}</span>
            <span>{{ formatBytes(fmt.filesize) }}</span>
          </div>
        </div>
      </div>
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
      <div v-if="tasks.length === 0" class="empty">暂无下载任务，创建第一条任务开始验证 MVP。</div>
      <div v-else class="task-list">
        <article v-for="task in tasks" :key="task.task_id" class="task-item">
          <div class="task-top">
            <strong>{{ task.payload?.url || 'unknown url' }}</strong>
            <span :class="['pill', task.status]">{{ task.status }}</span>
          </div>
          <div class="progress">
            <div class="bar" :style="{ width: `${Math.round(task.progress || 0)}%` }" />
          </div>
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

    <section class="pricing">
      <h2>后续可直接升级的付费功能</h2>
      <div class="cards">
        <div class="card">
          <h3>Creator Plus</h3>
          <p>无排队并发、批量模板、历史任务管理</p>
        </div>
        <div class="card hot">
          <h3>AI Pro</h3>
          <p>视频摘要、字幕翻译、多语导出与自动打点</p>
        </div>
        <div class="card">
          <h3>Team</h3>
          <p>多人协作、权限控制、私有部署支持</p>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Lexend:wght@400;600;700;800&family=Chivo:wght@400;700&display=swap');

:global(body) {
  margin: 0;
  font-family: 'Chivo', sans-serif;
  background:
    radial-gradient(circle at 12% -5%, #3555ff 0%, transparent 42%),
    radial-gradient(circle at 88% 0%, #1ecffb 0%, transparent 35%),
    #070b19;
  color: #eef2ff;
}

.app-shell {
  min-height: 100vh;
  padding: 20px;
  max-width: 1160px;
  margin: 0 auto 40px;
}

.top-nav {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 28px;
  padding: 8px 2px;
}

.brand {
  display: flex;
  gap: 10px;
  align-items: center;
  font-family: 'Lexend', sans-serif;
  font-weight: 700;
  letter-spacing: 0.3px;
}

.badge {
  background: linear-gradient(125deg, #28f5f5, #5a79ff);
  color: #031220;
  font-size: 12px;
  padding: 4px 8px;
  border-radius: 999px;
  font-weight: 800;
}

.cta {
  color: #b9c5ff;
  font-size: 14px;
}

.hero {
  margin: 36px 0;
}

.kicker {
  color: #73f6ff;
  text-transform: uppercase;
  letter-spacing: 1.4px;
  font-size: 12px;
  margin-bottom: 10px;
}

.hero h1 {
  font-family: 'Lexend', sans-serif;
  font-size: clamp(28px, 5vw, 52px);
  line-height: 1.08;
  margin: 0 0 10px;
}

.hero h1 span {
  color: #6f8bff;
}

.sub {
  max-width: 760px;
  color: #b3bddf;
}

.workspace {
  display: grid;
  grid-template-columns: 1.1fr 0.9fr;
  gap: 16px;
}

.panel {
  background: linear-gradient(140deg, rgba(20, 26, 52, 0.95), rgba(12, 16, 32, 0.95));
  border: 1px solid rgba(109, 137, 255, 0.35);
  border-radius: 18px;
  padding: 18px;
  backdrop-filter: blur(10px);
  box-shadow:
    0 18px 42px rgba(7, 10, 25, 0.46),
    inset 0 1px 0 rgba(255, 255, 255, 0.05);
}

.panel-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
}

.panel h2 {
  margin: 0;
  font-family: 'Lexend', sans-serif;
  font-size: 18px;
}

.mode-switch {
  background: rgba(46, 61, 120, 0.6);
  border-radius: 999px;
  padding: 4px;
  display: flex;
  gap: 4px;
}

.mode-switch button {
  border: 0;
  background: transparent;
  color: #b0b9d7;
  border-radius: 999px;
  padding: 6px 12px;
  cursor: pointer;
}

.mode-switch .active {
  background: #6083ff;
  color: #fff;
}

.field-group {
  display: grid;
  gap: 8px;
  margin-bottom: 14px;
}

label {
  color: #8fa0df;
  font-size: 13px;
}

input,
textarea,
select {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid #314172;
  border-radius: 12px;
  background: #0d142b;
  color: #edf2ff;
  padding: 12px 13px;
  font-size: 14px;
  outline: none;
}

input:focus,
textarea:focus,
select:focus {
  border-color: #5f80ff;
  box-shadow: 0 0 0 3px rgba(95, 128, 255, 0.2);
}

.action {
  border: 0;
  border-radius: 12px;
  background: #34467f;
  color: #fff;
  font-weight: 700;
  padding: 11px 14px;
  cursor: pointer;
}

.action:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.action.strong {
  background: linear-gradient(130deg, #77f7ff, #5f7eff 65%);
  color: #071122;
}

.submit-row {
  display: grid;
  gap: 8px;
}

.hint {
  margin: 0;
  color: #94a5df;
  font-size: 12px;
}

.error {
  margin: 0;
  color: #ff90a8;
  font-size: 13px;
}

.video-card {
  display: grid;
  grid-template-columns: 120px 1fr;
  gap: 12px;
  margin-bottom: 14px;
}

.video-card img {
  width: 120px;
  height: 76px;
  object-fit: cover;
  border-radius: 10px;
}

.title {
  margin: 0 0 6px;
  font-weight: 700;
}

.meta {
  margin: 0;
  font-size: 13px;
  color: #98a8de;
}

.empty {
  font-size: 14px;
  color: #9dafeb;
  padding: 14px 0;
}

.formats h3 {
  margin: 12px 0 8px;
  font-size: 14px;
  color: #b7c6ff;
}

.format-row {
  display: grid;
  grid-template-columns: 0.9fr 0.6fr 1fr 0.8fr;
  gap: 8px;
  padding: 8px 10px;
  font-size: 12px;
  background: rgba(26, 34, 67, 0.7);
  border-radius: 8px;
  margin-bottom: 6px;
}

.tasks-panel {
  margin-top: 16px;
}

.status-tags {
  display: flex;
  gap: 8px;
}

.status-tags span {
  background: rgba(42, 57, 113, 0.6);
  border: 1px solid rgba(113, 140, 255, 0.25);
  padding: 5px 9px;
  border-radius: 999px;
  font-size: 12px;
  color: #b8c6ff;
}

.task-list {
  display: grid;
  gap: 10px;
}

.task-item {
  background: rgba(14, 21, 44, 0.8);
  border-radius: 12px;
  padding: 10px;
  border: 1px solid rgba(105, 132, 240, 0.2);
}

.task-top {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
  margin-bottom: 8px;
  font-size: 13px;
}

.pill {
  border-radius: 999px;
  padding: 4px 8px;
  font-size: 11px;
  text-transform: uppercase;
}

.pill.queued,
.pill.running {
  background: rgba(0, 196, 255, 0.16);
  color: #7de8ff;
}

.pill.success {
  background: rgba(76, 255, 167, 0.16);
  color: #89f8c8;
}

.pill.failed {
  background: rgba(255, 93, 129, 0.16);
  color: #ff93ad;
}

.progress {
  width: 100%;
  background: #111b3d;
  border-radius: 999px;
  height: 8px;
  overflow: hidden;
}

.bar {
  height: 100%;
  background: linear-gradient(90deg, #5ff9ff, #6181ff);
  transition: width 0.35s ease;
}

.task-meta {
  margin-top: 6px;
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  font-size: 12px;
  color: #9aabdf;
}

.open-btn {
  border: 1px solid rgba(95, 128, 255, 0.45);
  background: rgba(19, 28, 58, 0.95);
  color: #b8c6ff;
  border-radius: 8px;
  padding: 4px 8px;
  font-size: 12px;
  cursor: pointer;
}

.pricing {
  margin-top: 16px;
}

.pricing h2 {
  font-size: 18px;
  margin: 0 0 12px;
}

.cards {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.card {
  background: rgba(14, 21, 44, 0.8);
  border-radius: 14px;
  padding: 14px;
  border: 1px solid rgba(105, 132, 240, 0.25);
}

.card.hot {
  border-color: rgba(95, 249, 255, 0.45);
  box-shadow: 0 0 0 1px rgba(95, 249, 255, 0.2);
}

.card h3 {
  margin: 0 0 8px;
  font-family: 'Lexend', sans-serif;
}

.card p {
  margin: 0;
  color: #9dafeb;
  font-size: 13px;
  line-height: 1.45;
}

@media (max-width: 1000px) {
  .workspace {
    grid-template-columns: 1fr;
  }
  .cards {
    grid-template-columns: 1fr;
  }
}
</style>
