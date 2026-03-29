import { createRouter, createWebHistory } from 'vue-router'

// 路由实例：
// - 当前项目为单页工作台，暂不拆分路由页面
// - 保留 router 以便后续扩展（如设置页、历史任务页）
const router = createRouter({
  // BASE_URL 由 Vite 注入，兼容不同部署路径。
  history: createWebHistory(import.meta.env.BASE_URL),
  // 当前无独立页面路由，统一由 App.vue 承载。
  routes: [],
})

export default router
