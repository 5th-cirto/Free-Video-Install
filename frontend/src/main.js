import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import './styles/tailwind.css'

import App from './App.vue'
import router from './router'

// 创建 Vue 应用实例，App.vue 作为整个前端入口页面。
const app = createApp(App)

// 注册全局状态管理（当前项目使用较轻，后续扩展时可继续复用 Pinia）。
app.use(createPinia())
// 注册路由（当前无业务路由页面，保留该结构便于未来扩展）。
app.use(router)
// 注册 Element Plus 组件库，统一表单/弹窗/交互控件体验。
app.use(ElementPlus)

// 挂载到 index.html 中的 #app 容器。
app.mount('#app')
