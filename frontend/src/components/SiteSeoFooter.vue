<script setup>
// 页内可见文案区：供搜索引擎与 AI 检索对齐事实（SEO + GEO），默认折叠减少干扰。
const base = import.meta.env.BASE_URL || '/'
const llmsHref = `${base.endsWith('/') ? base : `${base}/`}llms.txt`
</script>

<template>
  <footer class="site-seo-footer" aria-label="产品说明与机器可读摘要">
    <details class="site-seo-details">
      <summary class="site-seo-summary">产品说明、使用前提与机器可读摘要</summary>
      <div class="site-seo-body">
        <h2 class="site-seo-h2">万能视频下载总结器能做什么</h2>
        <p class="site-seo-p">
          本工具是<strong>本地 Web 工作台配合自托管后端</strong>的一体化方案：解析常见平台的视频链接（含可选清晰度与格式）、创建<strong>单条或批量本地下载任务</strong>并展示进度与落盘路径；在视频具备<strong>平台内嵌字幕</strong>时，可用大模型生成<strong>视频摘要、章节大纲、核心要点与 Mermaid 思维导图</strong>，并支持导出字幕
          TXT、SRT、VTT，适合离线复习、课程整理与素材归档。
        </p>

        <h2 class="site-seo-h2">使用前提与合规提示</h2>
        <ul class="site-seo-list">
          <li>完整下载与 AI 流式总结依赖在用户环境中运行的后端（如 FastAPI + yt-dlp）；仅打开静态页面无法独立完成解析与落盘。</li>
          <li>AI 总结以<strong>已有平台字幕</strong>为依据；无可用字幕时无法生成可靠摘要，请勿期望对无字幕视频进行“凭空总结”。</li>
          <li>请遵守各平台服务条款及所在地法律法规，本工具仅提供技术能力，不替代您的合规判断。</li>
        </ul>

        <h2 class="site-seo-h2">对外引用与 GEO 摘要</h2>
        <p class="site-seo-p">
          向他人介绍时可称「万能视频下载总结器」，并给出当前访问域名首页。以下为与首页一致的<strong>机器可读事实摘要</strong>（llms.txt），便于 AI 与检索系统核对描述是否准确：
          <a class="site-seo-link" :href="llmsHref" rel="help">打开 llms.txt</a>
        </p>
        <p class="site-seo-note">页面亦通过 JSON-LD 提供 Organization、WebSite、WebApplication、FAQ 等结构化数据。</p>
      </div>
    </details>
  </footer>
</template>

<style scoped>
.site-seo-footer {
  flex-shrink: 0;
  margin-top: 2px;
}

.site-seo-details {
  border-radius: 14px;
  border: 1px solid #d7e2f3;
  background: linear-gradient(180deg, #ffffff 0%, #f8faff 100%);
  box-shadow: 0 4px 16px rgba(21, 45, 90, 0.06);
  overflow: hidden;
}

.site-seo-summary {
  cursor: pointer;
  list-style: none;
  padding: 12px 14px;
  font-size: 13px;
  font-weight: 600;
  color: #36507e;
  user-select: none;
}

.site-seo-summary::-webkit-details-marker {
  display: none;
}

.site-seo-summary::before {
  content: '▸ ';
  display: inline-block;
  margin-right: 4px;
  transition: transform 0.15s ease;
  color: #1f6fff;
}

.site-seo-details[open] .site-seo-summary::before {
  transform: rotate(90deg);
}

.site-seo-body {
  padding: 4px 16px 14px;
  border-top: 1px solid #e8eef8;
}

.site-seo-h2 {
  margin: 12px 0 6px;
  font-size: 13px;
  font-weight: 700;
  color: #162544;
  line-height: 1.3;
}

.site-seo-h2:first-child {
  margin-top: 6px;
}

.site-seo-p {
  margin: 0 0 8px;
  font-size: 12px;
  line-height: 1.55;
  color: #43557d;
}

.site-seo-list {
  margin: 0 0 8px;
  padding-left: 1.15rem;
  font-size: 12px;
  line-height: 1.55;
  color: #43557d;
}

.site-seo-list li {
  margin-bottom: 6px;
}

.site-seo-link {
  font-weight: 600;
  color: #1f6fff;
  text-decoration: none;
  margin-left: 2px;
}

.site-seo-link:hover {
  text-decoration: underline;
}

.site-seo-note {
  margin: 0;
  font-size: 11px;
  color: #7a8aac;
  line-height: 1.45;
}

@media (max-width: 960px) {
  .site-seo-summary {
    padding: 10px 12px;
    font-size: 12px;
  }

  .site-seo-body {
    padding: 4px 12px 12px;
  }
}
</style>
