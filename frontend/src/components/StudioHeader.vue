<script setup>
// 顶部状态栏仅负责展示汇总信息，不包含业务逻辑。
defineProps({
  runningCount: { type: Number, default: 0 },
  successCount: { type: Number, default: 0 },
  failedCount: { type: Number, default: 0 },
})
</script>

<template>
  <!-- 页面顶部：品牌 + 任务统计 -->
  <header class="top-nav">
    <div class="brand-wrap">
      <span class="badge">PRO</span>
      <div class="brand-text">
        <strong>万能视频下载器</strong>
        <span>下载与 AI 总结一体化工作台</span>
      </div>
    </div>
    <div class="quick-stats">
      <span>进行中 {{ runningCount }}</span>
      <span>成功 {{ successCount }}</span>
      <span>失败 {{ failedCount }}</span>
    </div>
  </header>
</template>

<style scoped>
/* 顶部容器 */
.top-nav {
  border-radius: 16px;
  border: 1px solid #d7e2f3;
  background: linear-gradient(180deg, #ffffff 0%, #f6f9ff 100%);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px;
  gap: 14px;
  box-shadow: 0 8px 24px rgba(21, 45, 90, 0.08);
}

/* 左侧品牌区 */
.brand-wrap {
  display: flex;
  align-items: center;
  gap: 10px;
}

.badge {
  border-radius: 999px;
  padding: 4px 10px;
  background: linear-gradient(130deg, #1f6fff, #4a8bff);
  color: #fff;
  font-size: 11px;
  font-weight: 700;
}

.brand-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.brand-text strong {
  color: #162544;
  font-size: 16px;
  line-height: 1.1;
}

.brand-text span {
  color: #62739a;
  font-size: 12px;
}

/* 右侧统计标签 */
.quick-stats {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.quick-stats span {
  border: 1px solid #d4dded;
  background: #f7faff;
  color: #43557d;
  border-radius: 999px;
  font-size: 12px;
  padding: 5px 10px;
  white-space: nowrap;
}

/* 小屏下改为纵向布局，避免挤压 */
@media (max-width: 960px) {
  .top-nav {
    flex-direction: column;
    align-items: flex-start;
  }

  .quick-stats {
    width: 100%;
  }
}
</style>
