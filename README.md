# 万能视频下载站（MVP）

一个基于 `FastAPI + yt-dlp + Vue3` 的本地可运行视频下载工具，支持单条/批量下载、格式选择、任务进度查看、封面预览与本地落盘。

## 功能特性

- 多平台链接解析（标题、时长、封面、格式列表）
- 单条下载 + 批量下载
- 下载任务状态跟踪（`queued / running / success / failed`）
- 分离流自动处理（仅视频会自动补音频并合并）
- 封面代理加载（提升显示稳定性）
- 一键打开本地文件位置

## 技术栈

- 后端：`FastAPI`、`yt-dlp`、`httpx`
- 前端：`Vue 3`、`Vite`
- 任务执行：`ThreadPoolExecutor`（轻量内存任务管理）

## 项目结构

```text
free-video-installer/
├─ api/                       # FastAPI 后端
│  ├─ main.py                 # 应用入口
│  ├─ routers/video.py        # 视频相关接口
│  └─ services/               # 下载与任务服务
├─ frontend/                  # Vue 前端
│  └─ src/App.vue             # 主页面
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
- `POST /api/video/inspect`
- `POST /api/video/download`
- `POST /api/video/download/batch`
- `GET /api/video/tasks`
- `GET /api/video/tasks/{task_id}`
- `GET /api/video/config`
- `POST /api/video/open-path`
- `GET /api/video/thumbnail`

## 配置说明

可通过 `.env` 配置：

- `APP_ENV`
- `FRONTEND_ORIGIN`
- `DOWNLOADS_DIR`
- `MAX_PARALLEL_DOWNLOADS`
- `REQUEST_TIMEOUT_SECONDS`

参考模板：`.env.example`

## 现阶段限制

- 任务状态仅存内存，重启后丢失
- 暂无账号体系、支付、配额控制
- 暂无任务持久化与监控告警

## 文档

- `docs/需求分析文档.md`
- `docs/方案设计文档.md`
- `docs/项目总结文档.md`

## 后续规划

- 数据库持久化（用户/任务/订阅）
- 异步任务队列（Redis + Worker）
- 会员体系（支付、配额、并发）
- AI 能力（视频总结、字幕翻译）

## 合规说明

本项目仅提供下载技术能力，请在合法合规前提下使用，遵守目标平台服务条款与当地法律法规。

