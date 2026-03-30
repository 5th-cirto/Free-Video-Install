<script setup>
// 页内锚点导航：便于用户滚动浏览，便于爬虫理解页面结构（主题大纲）。
const links = [
  { href: '#section-guide', label: '使用说明' },
  { href: '#section-workspace', label: '工作台' },
  { href: '#section-tasks', label: '任务中心' },
  { href: '#section-more', label: '更多说明' },
]
</script>

<template>
  <nav class="in-page-nav" aria-label="本页目录">
    <ul class="in-page-nav-list">
      <li v-for="item in links" :key="item.href">
        <a class="in-page-nav-link" :href="item.href">{{ item.label }}</a>
      </li>
    </ul>
  </nav>
</template>

<style scoped>
.in-page-nav {
  flex-shrink: 0;
  position: sticky;
  top: 0;
  z-index: 20;
  margin: 0 -2px;
  padding: 8px 10px;
  border-radius: 12px;
  border: 1px solid #d7e2f3;
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(8px);
  box-shadow: 0 4px 20px rgba(21, 45, 90, 0.06);
}

.in-page-nav-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px 10px;
  justify-content: center;
}

.in-page-nav-link {
  display: inline-block;
  padding: 6px 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
  color: #36507e;
  text-decoration: none;
  border: 1px solid #dbe4f4;
  background: #f7faff;
  transition: background 0.15s ease, color 0.15s ease, border-color 0.15s ease;
}

.in-page-nav-link:hover {
  color: #1f6fff;
  border-color: #b8d0f5;
  background: #eef4ff;
}

@media (max-width: 560px) {
  .in-page-nav-list {
    justify-content: flex-start;
  }

  .in-page-nav-link {
    font-size: 11px;
    padding: 5px 10px;
  }
}
</style>
