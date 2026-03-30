# 前端重构说明（Element Plus + App.vue 拆分）

## 本次重构目标

- 引入 Element Plus，统一前端交互控件。
- 将接口调用从 `App.vue` 抽离到 `frontend/src/api`。
- 将通用工具能力抽离到 `frontend/src/utils`。
- 预置业务域 composables，作为后续进一步瘦身 `App.vue` 的基础。

## 目录新增

- `frontend/src/api/client.js`
- `frontend/src/api/auth.js`
- `frontend/src/api/billing.js`
- `frontend/src/api/video.js`
- `frontend/src/api/aiSummary.js`
- `frontend/src/utils/axiosErrors.js`
- `frontend/src/utils/sse.js`
- `frontend/src/utils/format.js`
- `frontend/src/utils/download.js`
- `frontend/src/composables/useAuth.js`
- `frontend/src/composables/useBilling.js`
- `frontend/src/composables/useDownloads.js`
- `frontend/src/composables/useAiSummary.js`
- `frontend/src/components/dialogs/AuthDialog.vue`
- `frontend/src/components/dialogs/BillingDialog.vue`
- `frontend/src/components/dialogs/MindmapDialog.vue`

## 主要改动

1. **Element Plus 接入**
   - 安装依赖：`element-plus`、`@element-plus/icons-vue`
   - 在 `frontend/src/main.js` 注册 `ElementPlus` 并引入样式。

2. **API 分层**
   - `App.vue` 中原有接口路径调用已迁移到 `src/api/*` 模块。
   - 统一通过 `api/client.js` 处理 baseURL、鉴权头和基础错误转换。

3. **工具函数拆分**
   - 错误解析、SSE 包解析、格式化、Blob 下载等逻辑已迁出 `App.vue`。

4. **弹窗组件化**
   - 登录/注册/重置密码、账单历史、导图全屏弹窗拆为独立组件。
   - 弹窗交互统一改为 Element Plus `el-dialog` 体系。

5. **核心面板控件迁移**
   - `DownloadPanel.vue`：输入、文本域、选择器、按钮、错误提示改为 Element Plus。
   - `SummaryPanel.vue`：页签切换、操作按钮、错误提示改为 Element Plus。
   - `StudioHeader.vue`：登录/注册/账单/VIP 操作改为 Element Plus 按钮与 Tag。
   - `TaskCenterPanel.vue`：任务状态、进度、操作按钮改为 Element Plus 控件。

## 验证结果

- 构建验证：`npm run build` 通过。
- 代码诊断：本轮修改文件执行 lints 后无新增错误。

## 后续建议

- 继续把 `App.vue` 中剩余业务编排迁移到 `useAuth/useBilling/useDownloads/useAiSummary`，进一步减少单文件复杂度。
- 针对 AI SSE 和字幕下载 fallback 建立最小自动化用例，避免后续迭代回归。
