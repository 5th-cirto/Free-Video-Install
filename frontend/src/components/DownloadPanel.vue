<script setup>
// 下载工作台：
// - 负责展示输入区、解析结果、格式选择、下载提交
// - 业务数据由父组件 App.vue 提供
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

// 事件全部向上抛给父组件，保持此组件为“展示 + 交互触发”角色。
const emit = defineEmits([
  'update:mode',
  'update:singleUrl',
  'update:batchInput',
  'update:selectedFormatId',
  'inspect',
  'createSingleDownload',
  'createBatchDownload',
])

// 统一处理 input/select 的值变更，减少模板里的重复代码。
function updateValue(eventName, event) {
  emit(eventName, event?.target?.value || '')
}

function updateModel(eventName, value) {
  emit(eventName, value || '')
}
</script>

<template>
  <!-- 左侧下载工作台 -->
  <aside class="panel left-pane">
    <div class="panel-head">
      <h2>下载工作台</h2>
      <div class="mode-switch">
        <el-segmented
          class="mode-segment"
          :model-value="mode"
          :options="[
            { label: '单条', value: 'single' },
            { label: '批量', value: 'batch' },
          ]"
          @update:model-value="emit('update:mode', $event)"
        />
      </div>
    </div>

    <!-- 解析成功后显示视频封面与元信息 -->
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

    <!-- 单条模式 -->
    <div v-if="mode === 'single'" class="field-group">
      <label>视频链接</label>
      <el-input
        :model-value="singleUrl"
        placeholder="粘贴视频链接，如 https://..."
        @update:model-value="updateModel('update:singleUrl', $event)"
      />
      <el-button class="action strong" type="primary" :loading="inspectLoading" @click="emit('inspect')">
        {{ inspectLoading ? '解析中...' : '解析视频信息 + 自动AI总结' }}
      </el-button>
      <el-alert v-if="inspectError" :title="inspectError" type="error" :closable="false" show-icon />
    </div>

    <!-- 批量模式 -->
    <div v-else class="field-group">
      <label>批量链接（每行一条）</label>
      <el-input
        :model-value="batchInput"
        type="textarea"
        :rows="5"
        placeholder="https://example.com/video-1&#10;https://example.com/video-2"
        @update:model-value="updateModel('update:batchInput', $event)"
      />
      <p class="hint">当前识别 {{ parsedBatchUrls.length }} 条链接</p>
    </div>

    <!-- 格式选择（作用于下载任务提交） -->
    <div class="field-group">
      <label>目标格式（可选）</label>
      <el-select
        :model-value="selectedFormatId"
        placeholder="自动选择（推荐）"
        style="width: 100%"
        @update:model-value="updateModel('update:selectedFormatId', $event)"
      >
        <el-option label="自动选择（推荐）" value="" />
        <el-option
          v-for="fmt in inspectInfo?.formats || []"
          :key="`${fmt.format_id}-${fmt.ext}`"
          :label="`${fmt.format_id} · ${fmt.ext} · ${fmt.resolution || '未知分辨率'}`"
          :value="fmt.format_id"
        />
      </el-select>
    </div>

    <!-- 下载提交按钮 -->
    <div class="submit-row">
      <el-button
        v-if="mode === 'single'"
        class="action"
        type="primary"
        :loading="actionLoading"
        :disabled="!singleUrl.trim()"
        @click="emit('createSingleDownload')"
      >
        {{ actionLoading ? '提交中...' : '开始下载当前视频' }}
      </el-button>
      <el-button v-else class="action" type="primary" :loading="actionLoading" @click="emit('createBatchDownload')">
        {{ actionLoading ? '提交中...' : '开始批量下载' }}
      </el-button>
      <el-alert v-if="actionError" :title="actionError" type="error" :closable="false" show-icon />
    </div>

    <p v-if="downloadsDir" class="hint">默认下载目录：{{ downloadsDir }}</p>
  </aside>
</template>

<style scoped>
/* 基础卡片容器 */
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

/* 头部：标题 + 模式切换 */
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

/* 模式切换按钮组 */
.mode-switch {
  border: 0;
  border-radius: 10px;
  padding: 0;
  display: flex;
  background: transparent;
}

:deep(.mode-segment.el-segmented) {
  --el-segmented-bg-color: #f7faff;
  --el-border-color: #d2dcee;
  --el-segmented-item-selected-color: #ffffff;
  border-radius: 10px;
  padding: 3px;
  min-height: 34px;
}

:deep(.mode-segment .el-segmented__item) {
  border-radius: 8px;
  color: #5a6d96;
  font-size: 12px;
  font-weight: 600;
}

:deep(.mode-segment .el-segmented__item.is-selected) {
  background: #1f6fff;
  color: #fff;
  box-shadow: none;
}

/* 视频封面卡片：封面完整显示，不裁切 */
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

/* 表单区域 */
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

/* 统一主操作按钮 */
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
