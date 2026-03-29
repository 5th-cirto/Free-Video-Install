# AI 总结接口说明

本文档描述《万能视频下载站》当前 AI 总结能力的接口约定与联调方法。

## 1. 接口概览

- 协议：HTTP + SSE（Server-Sent Events）
- 路径：`POST /api/ai-summary/stream`
- 返回类型：`text/event-stream`
- 功能：输入视频链接，流式返回总结过程与最终结构化结果
- 相关接口：`POST /api/video/subtitles/download`（字幕文件下载，`txt/srt/vtt`）

## 2. 请求参数

请求体（JSON）：

```json
{
  "url": "https://www.bilibili.com/video/BV1HfXKBQEMg/",
  "language": "zh-CN"
}
```

字段说明：

- `url`（必填，string）：视频链接
- `language`（可选，string）：字幕语言偏好（如 `zh-CN`、`zh`、`en`）

## 3. SSE 事件协议

接口会按阶段持续推送事件，前端应按 `event` 类型处理：

- `stage`：阶段状态
- `delta`：模型增量文本（流式 token 片段）
- `partial_result`：结构化中间结果（用于前端实时渲染）
- `result`：最终结构化结果
- `error`：可读错误信息
- `done`：结束标记

### 3.1 stage 事件

常见阶段值：

- `started`：请求已接收
- `subtitle_ready`：字幕提取完成
- `summarizing`：模型生成中

示例：

```text
event: stage
data: {"stage":"subtitle_ready","language":"ai-zh","source":"bilibili_player_api","chars":2910,"segments":126}
```

### 3.2 delta 事件

用于显示流式生成过程（可选展示）：

```text
event: delta
data: {"text":"..."}
```

### 3.3 result 事件（核心）

### 3.3 partial_result 事件（新增）

用于在模型尚未完成时推送可解析的结构化中间态，前端可据此流式刷新“总结/核心要点”等内容：

```text
event: partial_result
data: {"summary":"...","outline":["..."],"key_points":["..."],"mindmap_mermaid":"..."}
```

说明：

- 该事件为“尽力解析”的中间态，字段可能阶段性为空或不完整
- 以最终 `result` 事件为准

### 3.4 result 事件（核心）

最终结构化输出：

```json
{
  "summary": "string",
  "outline": ["string"],
  "key_points": ["string"],
  "mindmap_mermaid": "mindmap\n  root((VideoSummary))\n    ...",
  "subtitle_text": "string",
  "subtitle_segments": [
    { "start": 0.0, "end": 2.8, "text": "..." }
  ],
  "language": "ai-zh",
  "subtitle_source": "bilibili_player_api"
}
```

字段说明：

- `summary`：摘要
- `outline`：大纲列表
- `key_points`：核心知识点列表
- `mindmap_mermaid`：Mermaid 思维导图源码
- `subtitle_text`：字幕全文
- `subtitle_segments`：时间戳字幕分段（秒）
- `language`：实际字幕语言
- `subtitle_source`：字幕来源（如 `manual_subtitle`、`automatic_caption`、`bilibili_player_api`）

### 3.5 error 事件

```text
event: error
data: {"message":"Current video has no available platform subtitles."}
```

### 3.6 done 事件

```text
event: done
data: {"ok":true}
```

或失败：

```text
event: done
data: {"ok":false}
```

## 4. 关键实现策略

- 字幕提取：
  - 主路径：`yt-dlp` 的 `subtitles/automatic_captions`
  - B 站兜底：`view + player/wbi/v2` 字幕接口
- 模型调用：
  - DeepSeek 官方 API（流式）
  - 默认模型：`deepseek-chat`
- 思维导图：
  - 模型优先返回 `mindmap_mermaid`
  - 若语法异常，前端可使用大纲自动兜底生成
  - 当前前端支持全屏预览与 SVG 下载

## 5. 环境变量

必需：

- `DEEPSEEK_API_KEY`

推荐：

- `DEEPSEEK_BASE_URL=https://api.deepseek.com`
- `DEEPSEEK_MODEL=deepseek-chat`
- `DEEPSEEK_TIMEOUT_SECONDS=120`
- `DEEPSEEK_PROXY_URL=`（有代理需求时填写）

字幕相关（按需）：

- `YTDLP_COOKIEFILE=`（cookie.txt 绝对路径）
- `YTDLP_COOKIES_FROM_BROWSER=`（如 `chrome`）

## 6. 联调建议

1. 先确认后端健康：`GET /api/health`
2. 再发起 `POST /api/ai-summary/stream`
3. 前端按事件流处理并在 `done` 时收敛状态
4. 若出现 `error`：
   - 先检查视频是否有平台字幕
   - 再检查 cookie 配置与网络代理
   - 最后检查 DeepSeek Key/连通性

## 7. 兼容与限制

- 当前不启用 Whisper，本能力仅依赖平台字幕
- 部分受限视频可能需要登录态 cookie
- 任务状态仅内存，不做持久化记录
- 思维导图高清 PNG 在当前版本未开放，建议优先使用 SVG 导出

