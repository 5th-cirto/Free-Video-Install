<script setup>
const props = defineProps({
  mode: { type: String, default: 'single' },
  singleUrl: { type: String, default: '' },
  batchInput: { type: String, default: '' },
  parsedBatchUrls: { type: Array, default: () => [] },
  inspectLoading: { type: Boolean, default: false },
  inspectError: { type: String, default: '' },
  inspectInfo: { type: Object, default: null },
  selectedFormatId: { type: String, default: '' },
  actionError: { type: String, default: '' },
  actionLoading: { type: Boolean, default: false },
  downloadsDir: { type: String, default: '' },
  formatDuration: { type: Function, required: true },
  thumbnailUrl: { type: Function, required: true },
})

const emit = defineEmits([
  'update:mode',
  'update:singleUrl',
  'update:batchInput',
  'update:selectedFormatId',
  'inspect',
  'createSingleDownload',
  'createBatchDownload',
])

function updateValue(eventName, event) {
  emit(eventName, event?.target?.value || '')
}
</script>

<template>
  <aside class="panel left-pane">
    <div class="panel-head">
      <h2>下载工作台</h2>
      <div class="mode-switch">
        <button :class="{ active: mode === 'single' }" @click="emit('update:mode', 'single')">单条</button>
        <button :class="{ active: mode === 'batch' }" @click="emit('update:mode', 'batch')">批量</button>
      </div>
    </div>

    <div v-if="inspectInfo" class="hero-video">
      <div class="hero-video-media">
        <img v-if="inspectInfo.thumbnail" :src="thumbnailUrl(inspectInfo.thumbnail)" alt="thumbnail" />
      </div>
      <div class="hero-video-info">
        <p class="title">{{ inspectInfo.title || '未命名视频' }}</p>
        <div class="meta-grid">
          <p class="meta">平台：{{ inspectInfo.extractor || '未知' }}</p>
          <p class="meta">时长：{{ formatDuration(inspectInfo.duration) }}</p>
          <p class="meta">格式：{{ inspectInfo.formats?.length || 0 }}</p>
        </div>
      </div>
    </div>
    <div v-else class="empty">输入链接后解析，右侧会自动开始 AI 总结。</div>

    <div v-if="mode === 'single'" class="field-group">
      <label>视频链接</label>
      <input
        :value="singleUrl"
        type="text"
        placeholder="粘贴视频链接，如 https://..."
        @input="updateValue('update:singleUrl', $event)"
      />
      <button class="action strong" :disabled="inspectLoading" @click="emit('inspect')">
        {{ inspectLoading ? '解析中...' : '解析视频信息 + 自动AI总结' }}
      </button>
      <p v-if="inspectError" class="error">{{ inspectError }}</p>
    </div>

    <div v-else class="field-group">
      <label>批量链接（每行一条）</label>
      <textarea
        :value="batchInput"
        rows="5"
        placeholder="https://example.com/video-1&#10;https://example.com/video-2"
        @input="updateValue('update:batchInput', $event)"
      />
      <p class="hint">当前识别 {{ parsedBatchUrls.length }} 条链接</p>
    </div>

    <div class="field-group">
      <label>目标格式（可选）</label>
      <select :value="selectedFormatId" @change="updateValue('update:selectedFormatId', $event)">
        <option value="">自动选择（推荐）</option>
        <option v-for="fmt in inspectInfo?.formats || []" :key="`${fmt.format_id}-${fmt.ext}`" :value="fmt.format_id">
          {{ fmt.format_id }} · {{ fmt.ext }} · {{ fmt.resolution || '未知分辨率' }}
        </option>
      </select>
    </div>

    <div class="submit-row">
      <button
        v-if="mode === 'single'"
        class="action"
        :disabled="actionLoading || !singleUrl.trim()"
        @click="emit('createSingleDownload')"
      >
        {{ actionLoading ? '提交中...' : '开始下载当前视频' }}
      </button>
      <button v-else class="action" :disabled="actionLoading" @click="emit('createBatchDownload')">
        {{ actionLoading ? '提交中...' : '开始批量下载' }}
      </button>
      <p v-if="actionError" class="error">{{ actionError }}</p>
    </div>

    <p v-if="downloadsDir" class="hint">默认下载目录：{{ downloadsDir }}</p>
  </aside>
</template>

<style scoped>
.panel {
  border: 1px solid #d7e2f3;
  background: #fff;
  border-radius: 16px;
  padding: 14px;
  box-shadow: 0 10px 28px rgba(21, 45, 90, 0.07);
}

.left-pane {
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-height: 0;
}

.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

h2 {
  margin: 0;
  font-size: 18px;
  color: #162544;
}

.mode-switch {
  border: 1px solid #d2dcee;
  border-radius: 999px;
  padding: 3px;
  display: flex;
  gap: 4px;
  background: #f7faff;
}

.mode-switch button {
  border: 0;
  background: transparent;
  border-radius: 999px;
  padding: 6px 10px;
  cursor: pointer;
  color: #5a6d96;
  font-size: 12px;
}

.mode-switch button.active {
  background: #1f6fff;
  color: #fff;
}

.hero-video {
  border: 1px solid #dbe4f4;
  border-radius: 12px;
  overflow: hidden;
  background: #f9fbff;
}

.hero-video-media {
  width: 100%;
  aspect-ratio: 16 / 9;
  background: #f2f6fd;
  display: flex;
  align-items: center;
  justify-content: center;
}

.hero-video img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.hero-video-info {
  padding: 10px;
}

.title {
  margin: 0 0 6px;
  font-size: 14px;
  font-weight: 700;
  color: #1d2a48;
}

.meta-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 4px;
}

.meta {
  margin: 0;
  color: #5a6d96;
  font-size: 12px;
}

.field-group {
  display: grid;
  gap: 6px;
}

label {
  font-size: 12px;
  color: #5a6d96;
}

input,
textarea,
select {
  border: 1px solid #d0daed;
  border-radius: 10px;
  background: #fff;
  color: #1d2a48;
  padding: 10px;
  font-size: 13px;
  outline: none;
}

input:focus,
textarea:focus,
select:focus {
  border-color: #91b3ff;
  box-shadow: 0 0 0 2px rgba(31, 111, 255, 0.14);
}

.submit-row {
  display: grid;
  gap: 6px;
}

.action {
  border: 0;
  border-radius: 10px;
  padding: 10px 12px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 700;
  color: #fff;
  background: #1f6fff;
}

.action.strong {
  background: linear-gradient(135deg, #1f6fff 0%, #33a0ff 100%);
}

.action:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.hint {
  margin: 0;
  color: #7084ad;
  font-size: 12px;
}

.error {
  margin: 0;
  color: #cf456b;
  font-size: 12px;
}

.empty {
  border: 1px dashed #d2deef;
  border-radius: 12px;
  padding: 10px;
  background: #fbfdff;
  color: #6a7ea7;
  font-size: 12px;
}
</style>
