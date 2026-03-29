# AI 总结接口说明（基于当前后端代码）

本文档依据当前实现更新，参考：

- `api/routers/ai_summary.py`
- `api/routers/video.py`
- `api/schemas.py`
- `api/services/ai_summary.py`
- `api/services/subtitle_extractor.py`

## 1. 接口清单

### 1.1 AI 总结 SSE

- 方法：`POST`
- 路径：`/api/ai-summary/stream`
- Content-Type（请求）：`application/json`
- Content-Type（响应）：`text/event-stream`
- 说明：输入视频链接，按事件流返回总结过程与最终结构化结果

### 1.2 字幕文件下载（配套接口）

- 方法：`POST`
- 路径：`/api/video/subtitles/download`
- Content-Type（请求）：`application/json`
- Content-Type（响应）：
  - `txt` -> `text/plain; charset=utf-8`
  - `srt` -> `application/x-subrip; charset=utf-8`
  - `vtt` -> `text/vtt; charset=utf-8`
- 说明：按格式导出字幕文件，响应头包含 `Content-Disposition`

## 2. 请求参数定义

## 2.1 `POST /api/ai-summary/stream`

请求体：

```json
{
  "url": "https://www.bilibili.com/video/BV1HfXKBQEMg/",
  "language": "zh-CN"
}
```

字段：

- `url`（必填，string，最短 3 字符）：视频链接
- `language`（可选，string）：字幕语言偏好（如 `zh-CN`、`zh`、`en`）

## 2.2 `POST /api/video/subtitles/download`

请求体：

```json
{
  "url": "https://www.bilibili.com/video/BV1HfXKBQEMg/",
  "language": "zh-CN",
  "format": "srt"
}
```

字段：

- `url`（必填，string，最短 3 字符）：视频链接
- `language`（可选，string）：字幕语言偏好
- `format`（可选，enum）：`txt | srt | vtt`，默认 `srt`

## 3. SSE 事件协议

服务端通过以下事件类型输出：

- `stage`
- `delta`
- `partial_result`
- `result`
- `error`
- `done`

## 3.1 `stage`（阶段状态）

当前代码中的阶段值：

- `started`：请求已接收
- `subtitle_ready`：字幕提取成功
- `summarizing`：大模型总结中

示例：

```text
event: stage
data: {"stage":"subtitle_ready","language":"ai-zh","source":"bilibili_player_api","chars":2910,"segments":126}
```

字段补充：

- `language`：实际提取字幕语言
- `source`：字幕来源
- `chars`：字幕文本字符数
- `segments`：字幕分段数

## 3.2 `delta`（增量文本）

```text
event: delta
data: {"text":"..."}
```

说明：模型输出片段，适合打字机效果或调试原始流。

## 3.3 `partial_result`（结构化中间态）

```text
event: partial_result
data: {"summary":"...","outline":["..."],"key_points":["..."],"mindmap_mermaid":"..."}
```

说明：

- 基于当前累计文本做尽力解析，字段可能暂时为空或不完整
- 前端可据此流式刷新摘要/要点
- 最终以 `result` 事件为准

## 3.4 `result`（最终结构化结果）

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
- `outline`：章节/主题大纲
- `key_points`：核心要点
- `mindmap_mermaid`：Mermaid 导图源码
- `subtitle_text`：完整字幕文本
- `subtitle_segments`：字幕分段数组（秒级时间）
- `language`：实际字幕语言
- `subtitle_source`：字幕来源（如 `manual_subtitle`、`automatic_caption`、`bilibili_player_api`）

## 3.5 `error`（错误信息）

```text
event: error
data: {"message":"Current video has no available platform subtitles."}
```

说明：统一输出可读错误文本；随后通常会有 `done` 事件。

## 3.6 `done`（结束标记）

成功：

```text
event: done
data: {"ok":true}
```

失败：

```text
event: done
data: {"ok":false}
```

## 4. 字幕下载接口返回说明

## 4.1 成功

- 返回文件二进制流
- `Content-Disposition: attachment; filename="subtitle_xxx.srt"`

## 4.2 失败（HTTP 400/422）

常见原因：

- 字幕提取失败（`Subtitle extraction failed: ...`）
- 字幕导出失败（`Subtitle export failed: ...`）
- 字幕内容为空（`Subtitle content is empty.`）
- 参数格式错误（例如 `format` 不在 `txt/srt/vtt`）

## 5. 关键实现策略

- 字幕提取：
  - 主路径：`yt-dlp` 的 `subtitles` / `automatic_captions`
  - B 站兜底：`x/web-interface/view` + `x/player/wbi/v2`
- 模型调用：
  - DeepSeek 流式输出
  - 默认模型 `deepseek-chat`
- 结构化中间态：
  - 服务端在流式输出中对累计文本进行“尽力 JSON 解析”，生成 `partial_result`
- 导图策略：
  - 服务端返回 `mindmap_mermaid`
  - 前端可在语法异常时用 `outline/key_points` 兜底重建

## 6. 环境变量

必需：

- `DEEPSEEK_API_KEY`

推荐：

- `DEEPSEEK_BASE_URL=https://api.deepseek.com`
- `DEEPSEEK_MODEL=deepseek-chat`
- `DEEPSEEK_TIMEOUT_SECONDS=120`
- `DEEPSEEK_PROXY_URL=`（需要代理时填写）

字幕相关（按需）：

- `YTDLP_COOKIEFILE=`（cookie.txt 绝对路径）
- `YTDLP_COOKIES_FROM_BROWSER=`（如 `chrome`）

## 7. 联调建议

1. `GET /api/health` 检查后端服务
2. 用 `POST /api/ai-summary/stream` 验证 SSE 事件完整性（至少收到 `stage` + `done`）
3. 再测 `POST /api/video/subtitles/download` 的 `txt/srt/vtt` 三种格式
4. 出错排查顺序：
   - 视频是否存在平台字幕
   - cookie/登录态是否可用
   - 网络代理与 DeepSeek 连通性

## 8. 已知限制

- 当前不启用 Whisper，依赖平台字幕可用性
- 受限视频可能需要 cookie
- 任务状态仅内存存储，不持久化
- 思维导图高清 PNG 未开放，建议使用 SVG 导出

