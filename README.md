# 万能视频下载站（MVP）

一个基于 `FastAPI + yt-dlp + Vue3` 的本地可运行视频下载工具，支持单条/批量下载、格式选择、任务进度查看、封面预览、本地落盘，以及 AI 视频总结（SSE 流式）。

## 功能特性

- 多平台链接解析（标题、时长、封面、格式列表）
- 单条下载 + 批量下载
- 下载任务状态跟踪（`queued / running / success / failed`）
- 分离流自动处理（仅视频会自动补音频并合并）
- 封面代理加载（提升显示稳定性）
- 一键打开本地文件位置
- AI 视频总结（SSE 流式输出：`summary / outline / key_points`）
- 平台字幕优先提取（含 B 站字幕 API 兜底，不启用 Whisper）
- 字幕文本输出（时间戳分段：`subtitle_segments`）
- 思维导图输出（`mindmap_mermaid`），前端可视化渲染
- 前端工作台 V2（浅色紧凑布局，桌面端 `40%:60%`，任务中心次级折叠）
- 邮箱密码账号体系（注册/登录，JWT 鉴权）
- 会员支付（Stripe Checkout，CNY，Webhook 验签与幂等）
- AI 额度策略（免费用户每日 5 次，VIP 不限）
- 密码找回（邮箱重置链接）
- 账单/订单历史查询

## 技术栈

- 后端：`FastAPI`、`yt-dlp`、`httpx`
- 前端：`Vue 3`、`Vite`、`axios`
- 任务执行：`ThreadPoolExecutor`（轻量内存任务管理）

## 项目结构

```text
free-video-installer/
├─ api/                       # FastAPI 后端
│  ├─ main.py                 # 应用入口
│  ├─ routers/video.py        # 下载相关接口
│  ├─ routers/ai_summary.py   # AI 总结 SSE 接口
│  └─ services/               # 下载/字幕/总结服务
├─ frontend/                  # Vue 前端
│  └─ src/
│     ├─ App.vue              # 页面壳层与状态编排
│     └─ components/          # 工作台头部/下载区/总结区/任务中心
├─ docs/                      # 需求/方案/总结文档
├─ downloads/                 # 下载输出目录（运行时生成）
├─ requirements.txt
└─ .env.example
```

## 环境要求

- Python 3.10+（建议）
- Node.js 20+
- `ffmpeg`（必须，用于音视频合并）

> 说明：如果缺少 `ffmpeg`，部分平台分离流会出现“只有画面没声音”或合并失败。

## 快速开始

### 1) 安装后端依赖

```powershell
cd d:\vue_project\free-video-installer
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
```

### 2) 启动后端

```powershell
cd d:\vue_project\free-video-installer
.\.venv\Scripts\python -m uvicorn api.main:app --host 127.0.0.1 --port 8000
```

### 3) 启动前端

```powershell
cd d:\vue_project\free-video-installer\frontend
npm install
npm run dev
```

打开 `http://localhost:5173` 即可使用。

## 关键接口

- `GET /api/health`
- `POST /api/auth/register`
- `POST /api/auth/login`
- `GET /api/auth/me`
- `POST /api/auth/request-password-reset`
- `POST /api/auth/reset-password`
- `POST /api/video/inspect`
- `POST /api/video/download`
- `POST /api/video/download/batch`
- `GET /api/video/tasks`
- `GET /api/video/tasks/{task_id}`
- `GET /api/video/config`
- `POST /api/video/open-path`
- `GET /api/video/thumbnail`
- `POST /api/ai-summary/stream`（SSE）
- `POST /api/video/subtitles/download`（字幕导出：`txt/srt/vtt`）
- `POST /api/billing/checkout-session`
- `GET /api/billing/membership-status`
- `GET /api/billing/orders`
- `POST /api/billing/webhook`

### AI 总结结果字段（`result` 事件）

- `summary`：摘要
- `outline`：大纲列表
- `key_points`：核心要点列表
- `mindmap_mermaid`：Mermaid 思维导图源码
- `subtitle_text`：字幕全文文本
- `subtitle_segments`：带时间戳字幕分段（`start/end/text`）

## 配置说明

可通过 `.env` 配置：

- `APP_ENV`
- `FRONTEND_ORIGIN`
- `DOWNLOADS_DIR`
- `MAX_PARALLEL_DOWNLOADS`
- `REQUEST_TIMEOUT_SECONDS`
- `SQLITE_DB_PATH`
- `JWT_SECRET_KEY`
- `JWT_EXPIRE_MINUTES`
- `PASSWORD_BCRYPT_ROUNDS`
- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USER`
- `SMTP_PASSWORD`
- `SMTP_FROM_EMAIL`
- `SMTP_USE_TLS`
- `APP_PUBLIC_BASE_URL`
- `PASSWORD_RESET_TOKEN_EXPIRE_MINUTES`
- `DEEPSEEK_API_KEY`
- `DEEPSEEK_BASE_URL`
- `DEEPSEEK_MODEL`
- `DEEPSEEK_TIMEOUT_SECONDS`
- `DEEPSEEK_PROXY_URL`（可选，DeepSeek 显式代理）
- `STRIPE_SECRET_KEY`
- `STRIPE_WEBHOOK_SECRET`
- `STRIPE_PRICE_CNY_1M`
- `STRIPE_SUCCESS_URL`
- `STRIPE_CANCEL_URL`
- `YTDLP_COOKIEFILE`（可选，平台登录态 cookie 文件）
- `YTDLP_COOKIES_FROM_BROWSER`（可选，从浏览器读取 cookie）

参考模板：`.env.example`

## 现阶段限制

- 任务状态仅存内存，重启后丢失
- 暂无任务持久化与监控告警
- AI 总结依赖平台可用字幕；若平台未返回字幕则无法生成总结
- 密码重置依赖 SMTP 配置正确，邮件通道异常时无法完成找回流程

## 文档

- `docs/需求分析文档.md`
- `docs/方案设计文档.md`
- `docs/项目总结文档.md`
- `docs/AI总结接口说明.md`
- `docs/会员系统开发进度.md`
- `docs/前端重构说明-ElementPlus.md`

## 前端 UI V2 说明（2026-03）

- 页面拆分为组件化结构：工作台头部、下载工作台、AI 总结区、任务中心。
- 桌面端采用 `40%:60%` 左右分栏：左侧下载与视频信息，右侧总结结果。
- 移动端顺序为“下载工作台 -> AI 总结结果”，保证操作链路优先。
- 任务中心改为次级折叠面板，保留任务统计、进度、错误、打开文件位置。
- 去除“格式预览”块，避免首屏拥挤；视频封面改为完整展示（不裁切）。
- 前端请求统一迁移至 `axios`，并保持 AI SSE 增量事件解析。

## 前端请求说明

- 常规 JSON 接口：统一通过 `axios` 实例调用（集中 `baseURL` 与错误处理）。
- AI 总结接口：使用 `axios` + `onDownloadProgress` 解析 SSE 增量文本流。
- 字幕导出接口：使用 `axios` 的 `responseType: blob` 下载文件。

## 后续规划

- 数据库持久化（用户/任务/订阅）
- 异步任务队列（Redis + Worker）
- 会员体系增强（退款/争议单处理、更多套餐）
- AI 能力增强（视频总结、字幕翻译）

## 合规说明

本项目仅提供下载技术能力，请在合法合规前提下使用，遵守目标平台服务条款与当地法律法规。

