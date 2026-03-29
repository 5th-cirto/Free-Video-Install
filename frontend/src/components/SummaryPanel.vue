<script setup>
// AI 总结展示区：
// - 负责展示不同页签（摘要/大纲/导图/字幕）
// - 只做展示与事件转发，不直接调用 API
defineProps({
  aiStage: { type: String, default: '' },
  aiLoading: { type: Boolean, default: false },
  aiError: { type: String, default: '' },
  aiViewTab: { type: String, default: 'summary' },
  hasAiContent: { type: Boolean, default: false },
  aiStreamingSummary: { type: String, default: '' },
  aiStreamingKeyPoints: { type: Array, default: () => [] },
  aiRaw: { type: String, default: '' },
  aiDisplayResult: { type: Object, default: () => ({}) },
  aiResult: { type: Object, default: null },
  mindmapSvg: { type: String, default: '' },
  mindmapRenderHint: { type: String, default: '' },
  mindmapRenderError: { type: String, default: '' },
  formatTimestamp: { type: Function, required: true },
})

// 向父组件抛出操作事件（切 tab、下载导图、下载字幕等）。
const emit = defineEmits([
  'update:aiViewTab',
  'openMindmapFullscreen',
  'downloadMindmapSvg',
  'downloadSubtitleFile',
])
</script>

<template>
  <!-- 右侧 AI 总结区 -->
  <section class="panel right-pane">
    <div class="panel-head">
      <h2>AI 总结结果</h2>
      <div class="status-tags">
        <span v-if="aiStage">阶段 {{ aiStage }}</span>
        <span v-if="aiLoading">生成中</span>
      </div>
    </div>

    <p v-if="aiError" class="error">{{ aiError }}</p>

    <!-- 结果页签切换 -->
    <div class="result-tabs">
      <button :class="{ active: aiViewTab === 'summary' }" @click="emit('update:aiViewTab', 'summary')">总结摘要</button>
      <button :class="{ active: aiViewTab === 'outline' }" @click="emit('update:aiViewTab', 'outline')">章节总结</button>
      <button :class="{ active: aiViewTab === 'mindmap' }" @click="emit('update:aiViewTab', 'mindmap')">思维导图</button>
      <button :class="{ active: aiViewTab === 'subtitle' }" @click="emit('update:aiViewTab', 'subtitle')">字幕内容</button>
    </div>

    <!-- 有内容时显示结果，无内容时显示占位提示 -->
    <div class="result-body" v-if="hasAiContent">
      <!-- 摘要页签 -->
      <div v-if="aiViewTab === 'summary'">
        <p class="meta"><strong>总结</strong></p>
        <p class="content-text">{{ aiStreamingSummary || '等待结构化总结输出...' }}</p>
        <div class="list-box" v-if="aiStreamingKeyPoints.length">
          <p class="meta"><strong>核心要点</strong></p>
          <ul>
            <li v-for="(item, idx) in aiStreamingKeyPoints" :key="`point-${idx}`">{{ item }}</li>
          </ul>
        </div>
        <details v-if="aiRaw" class="raw-debug">
          <summary>查看流式原始输出</summary>
          <pre class="raw-box">{{ aiRaw }}</pre>
        </details>
      </div>

      <!-- 大纲页签 -->
      <div v-if="aiViewTab === 'outline'" class="list-box">
        <p class="meta"><strong>章节大纲</strong></p>
        <ul v-if="aiDisplayResult.outline?.length">
          <li v-for="(item, idx) in aiDisplayResult.outline" :key="`outline-${idx}`">{{ item }}</li>
        </ul>
        <p v-else class="hint">等待大纲流式输出...</p>
      </div>

      <!-- 导图页签 -->
      <div v-if="aiViewTab === 'mindmap'" class="list-box">
        <div class="mindmap-actions">
          <button class="open-btn" :disabled="!mindmapSvg" @click="emit('openMindmapFullscreen')">全屏预览</button>
          <button class="open-btn" :disabled="!mindmapSvg" @click="emit('downloadMindmapSvg')">下载 SVG</button>
        </div>
        <div v-if="mindmapSvg" class="mindmap-preview" v-html="mindmapSvg"></div>
        <p v-else class="hint">等待导图渲染...</p>
        <p v-if="mindmapRenderHint" class="hint">{{ mindmapRenderHint }}</p>
        <p v-if="mindmapRenderError" class="error">{{ mindmapRenderError }}</p>
      </div>

      <!-- 字幕页签 -->
      <div v-if="aiViewTab === 'subtitle'" class="list-box">
        <p class="meta"><strong>字幕分段</strong></p>
        <div class="mindmap-actions">
          <button class="open-btn" @click="emit('downloadSubtitleFile', 'txt')">下载 TXT</button>
          <button class="open-btn" @click="emit('downloadSubtitleFile', 'srt')">下载 SRT</button>
          <button class="open-btn" @click="emit('downloadSubtitleFile', 'vtt')">下载 VTT</button>
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
</template>

<style scoped>
/* 基础卡片 */
.panel {
  border: 1px solid #d7e2f3;
  background: #fff;
  border-radius: 16px;
  padding: 14px;
  box-shadow: 0 10px 28px rgba(21, 45, 90, 0.07);
}

/* 右栏纵向布局，主体内容允许内部滚动 */
.right-pane {
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.panel-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}

h2 {
  margin: 0;
  font-size: 18px;
  color: #162544;
}

.status-tags {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.status-tags span {
  border: 1px solid #d4dded;
  background: #f7faff;
  color: #43557d;
  border-radius: 999px;
  font-size: 11px;
  padding: 5px 9px;
}

/* 页签样式 */
.result-tabs {
  margin-top: 10px;
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.result-tabs button {
  border: 1px solid #d2dcee;
  border-radius: 999px;
  background: #f7faff;
  color: #5a6d96;
  cursor: pointer;
  padding: 6px 10px;
  font-size: 12px;
}

.result-tabs .active {
  border-color: #1f6fff;
  background: #1f6fff;
  color: #fff;
}

.result-body {
  margin-top: 10px;
  border: 1px solid #dbe4f4;
  border-radius: 12px;
  background: #fbfdff;
  padding: 12px;
  flex: 1;
  min-height: 0;
  overflow: auto;
}

.meta {
  margin: 0;
  color: #50638d;
  font-size: 13px;
}

/* 结果内容基础排版 */
.content-text {
  margin: 6px 0 0;
  font-size: 14px;
  color: #243457;
  line-height: 1.55;
}

.list-box ul {
  margin: 8px 0 0;
  padding-left: 18px;
}

.list-box li {
  color: #2c3f66;
  margin-bottom: 4px;
  line-height: 1.5;
  font-size: 13px;
}

.mindmap-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 8px;
}

.open-btn {
  border: 1px solid #c9d5eb;
  border-radius: 8px;
  background: #fff;
  color: #36507e;
  cursor: pointer;
  font-size: 12px;
  padding: 7px 10px;
}

.open-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.mindmap-preview,
.segments-box {
  border: 1px solid #dbe4f4;
  border-radius: 10px;
  background: #fff;
  padding: 10px;
  max-height: 100%;
  overflow: auto;
}

.segment-line {
  margin: 0 0 7px;
  color: #2d4069;
  font-size: 12px;
  line-height: 1.5;
}

.raw-debug {
  margin-top: 10px;
}

.raw-debug summary {
  cursor: pointer;
  color: #5a6d96;
  font-size: 12px;
}

.raw-box {
  white-space: pre-wrap;
  border: 1px solid #dbe4f4;
  border-radius: 10px;
  background: #fff;
  color: #2d4069;
  font-size: 12px;
  padding: 10px;
  max-height: 180px;
  overflow: auto;
}

.hint {
  margin: 0;
  color: #7084ad;
  font-size: 12px;
}

.error {
  margin: 6px 0 0;
  color: #cf456b;
  font-size: 12px;
}

.empty {
  border: 1px dashed #d2deef;
  border-radius: 12px;
  padding: 12px;
  margin-top: 10px;
  background: #fbfdff;
  color: #6a7ea7;
  font-size: 12px;
}
</style>
