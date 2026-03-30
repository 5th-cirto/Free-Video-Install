<script setup>
const base = import.meta.env.BASE_URL || '/'
const llmsHref = `${base.endsWith('/') ? base : `${base}/`}llms.txt`
</script>

<template>
  <section class="tech-strip" aria-label="技术栈与事实摘要">
    <p class="tech-strip-line">
      <span class="tech-strip-label">技术栈</span>
      <span class="tech-strip-items">Vue 3 · Vite · FastAPI · yt-dlp · ffmpeg</span>
      <span class="tech-strip-sep" aria-hidden="true"></span>
      <span class="tech-strip-label">AI</span>
      <span class="tech-strip-items">基于平台字幕的流式总结（可对接 DeepSeek 等）</span>
    </p>
    <p class="tech-strip-sub">
      完整能力需在本地或自托管环境运行后端；面向 AI 检索的
      <a :href="llmsHref" class="tech-strip-a" rel="help">事实摘要 llms.txt</a>
    </p>
  </section>
</template>

<style scoped>
.tech-strip {
  flex-shrink: 0;
  padding: 12px 16px;
  border-radius: 12px;
  border: 1px dashed #c5d6ed;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.92) 0%, #f3f7fd 100%);
}

.tech-strip-line {
  margin: 0 0 6px;
  font-size: 12px;
  line-height: 1.55;
  color: #43557d;
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 6px 10px;
}

.tech-strip-label {
  font-weight: 700;
  color: #1d2a48;
  flex-shrink: 0;
}

.tech-strip-items {
  color: #516289;
}

.tech-strip-sep {
  display: none;
}

@media (min-width: 720px) {
  .tech-strip-sep {
    display: inline-block;
    width: 4px;
    height: 4px;
    border-radius: 50%;
    background: #b8c8e4;
    vertical-align: middle;
    margin: 0 2px 0 4px;
    flex-shrink: 0;
  }
}

.tech-strip-sub {
  margin: 0;
  font-size: 11px;
  color: #7a8aac;
  line-height: 1.45;
}

.tech-strip-a {
  font-weight: 600;
  color: #1f6fff;
  text-decoration: none;
}

.tech-strip-a:hover {
  text-decoration: underline;
}
</style>
