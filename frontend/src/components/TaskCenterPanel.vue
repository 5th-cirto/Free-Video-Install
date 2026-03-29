<script setup>
defineProps({
  expanded: { type: Boolean, default: false },
  runningCount: { type: Number, default: 0 },
  successCount: { type: Number, default: 0 },
  failedCount: { type: Number, default: 0 },
  tasks: { type: Array, default: () => [] },
})

const emit = defineEmits(['toggle', 'openLocalPath'])
</script>

<template>
  <section class="task-shell">
    <button class="task-summary" @click="emit('toggle')">
      <strong>任务中心</strong>
      <div class="chips">
        <span>进行中 {{ runningCount }}</span>
        <span>成功 {{ successCount }}</span>
        <span>失败 {{ failedCount }}</span>
      </div>
      <span class="arrow">{{ expanded ? '收起' : '展开' }}</span>
    </button>

    <div v-if="expanded" class="task-panel">
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
              @click="emit('openLocalPath', task.result.filepath)"
            >
              打开文件位置
            </button>
            <span v-else-if="task.error" class="error">原因: {{ task.error }}</span>
          </div>
        </article>
      </div>
    </div>
  </section>
</template>

<style scoped>
.task-shell {
  border: 1px solid #d7e2f3;
  border-radius: 16px;
  background: #fff;
  box-shadow: 0 10px 28px rgba(21, 45, 90, 0.07);
}

.task-summary {
  width: 100%;
  border: 0;
  background: linear-gradient(180deg, #ffffff 0%, #f7faff 100%);
  border-radius: 16px;
  padding: 10px 12px;
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
}

.task-summary strong {
  color: #162544;
  font-size: 14px;
  margin-right: 2px;
}

.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  flex: 1;
}

.chips span {
  border: 1px solid #d4dded;
  background: #fff;
  color: #43557d;
  border-radius: 999px;
  font-size: 11px;
  padding: 4px 8px;
}

.arrow {
  color: #50638d;
  font-size: 12px;
}

.task-panel {
  border-top: 1px solid #e2e9f6;
  padding: 10px 12px 12px;
}

.task-list {
  max-height: 230px;
  overflow: auto;
  display: grid;
  gap: 8px;
}

.task-item {
  border: 1px solid #dbe4f4;
  border-radius: 10px;
  padding: 8px;
  background: #fbfdff;
}

.task-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  font-size: 12px;
  color: #2c3f66;
}

.pill {
  border-radius: 999px;
  font-size: 11px;
  padding: 3px 7px;
}

.pill.queued,
.pill.running {
  color: #1163b8;
  background: #e8f3ff;
}

.pill.success {
  color: #1f7e44;
  background: #eaf9ef;
}

.pill.failed {
  color: #b93758;
  background: #fdeef2;
}

.progress {
  width: 100%;
  height: 7px;
  border-radius: 999px;
  overflow: hidden;
  background: #e7edf8;
  margin-top: 6px;
}

.bar {
  height: 100%;
  background: linear-gradient(90deg, #1f6fff, #5bb7ff);
}

.task-meta {
  margin-top: 6px;
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
  align-items: center;
  color: #566a92;
  font-size: 12px;
}

.open-btn {
  border: 1px solid #c9d5eb;
  border-radius: 8px;
  background: #fff;
  color: #36507e;
  font-size: 12px;
  padding: 6px 9px;
  cursor: pointer;
}

.error {
  color: #cf456b;
}

.empty {
  color: #6a7ea7;
  font-size: 12px;
  padding: 8px 0;
}
</style>
