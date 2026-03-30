<script setup>
// SEO / GEO：结构化引导文案与关键词，表述与 llms.txt、需求文档一致（不虚构「1800+ 站」等）。
</script>

<template>
  <div class="landing-seo-wrap">
    <section class="landing-block" aria-labelledby="landing-howto-heading">
      <h2 id="landing-howto-heading" class="landing-h2">
        如何使用 <span class="landing-brand">万能视频下载总结器</span>
      </h2>
      <p class="landing-lead">
        只需 3 步：在已部署<strong>本地或自托管后端</strong>的前提下，完成链接解析、本地下载与（在具备平台字幕时）AI
        结构化总结。支持 YouTube、Bilibili等多数常见站点，具体以各平台策略与 yt-dlp 支持为准。
      </p>
      <ol class="landing-steps" aria-label="使用步骤">
        <li class="landing-step">
          <div class="landing-step-num" aria-hidden="true">1</div>
          <div class="landing-step-body">
            <h3 class="landing-step-title">复制视频链接</h3>
            <p class="landing-step-text">
              在目标平台打开视频，复制分享链接或浏览器地址栏中的视频 URL（如 YouTube、Bilibili等）。
            </p>
          </div>
        </li>
        <li class="landing-step">
          <div class="landing-step-num" aria-hidden="true">2</div>
          <div class="landing-step-body">
            <h3 class="landing-step-title">粘贴链接并解析</h3>
            <p class="landing-step-text">
              在工作台输入框粘贴链接，点击解析。系统将识别平台并展示标题、时长、封面及可选格式与清晰度列表。
            </p>
          </div>
        </li>
        <li class="landing-step">
          <div class="landing-step-num" aria-hidden="true">3</div>
          <div class="landing-step-body">
            <h3 class="landing-step-title">选择格式下载与查看 AI 总结</h3>
            <p class="landing-step-text">
              选择合适格式发起本地下载；解析成功后可在同屏查看基于<strong>平台字幕</strong>的 AI
              摘要、章节大纲、核心要点与思维导图（Mermaid），并支持导出字幕文件。
            </p>
          </div>
        </li>
      </ol>
      <p class="landing-footnote">
        当前阶段<strong>无独立账号体系</strong>；完整能力需本机/服务器运行后端。手机与其他设备可通过浏览器访问同一工作台（与网络可达性有关）。页面内容更新于 2026 年 3 月。
      </p>
    </section>

    <section class="landing-block landing-features" aria-labelledby="landing-features-heading">
      <h2 id="landing-features-heading" class="landing-h2">
        为什么选择 <span class="landing-brand">万能视频下载总结器</span>
      </h2>
      <p class="landing-lead landing-lead-tight">
        简洁的本地工作台：解析、下载、任务管理与 AI 结构化输出一体，适合学习笔记与素材整理场景。
      </p>
      <ul class="landing-cards" aria-label="产品亮点">
        <li class="landing-card">
          <div class="landing-card-icon landing-card-icon--globe" aria-hidden="true">
            <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10" />
              <path d="M2 12h20M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
            </svg>
          </div>
          <h3 class="landing-card-title">常见平台链接解析</h3>
          <p class="landing-card-text">
            依托 yt-dlp 生态解析多数主流站点（如 YouTube、Bilibili等）；能否下载与总结受平台规则、网络与字幕可用性影响。
          </p>
        </li>
        <li class="landing-card">
          <div class="landing-card-icon landing-card-icon--bolt" aria-hidden="true">
            <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M13 2L3 14h8l-1 8 10-12h-8l1-8z" />
            </svg>
          </div>
          <h3 class="landing-card-title">解析与落盘一体化</h3>
          <p class="landing-card-text">
            单条与批量任务、进度与本地目录展示；格式策略可减少「仅有画面无声音」问题，需要时使用 ffmpeg 合并音画。
          </p>
        </li>
        <li class="landing-card">
          <div class="landing-card-icon landing-card-icon--device" aria-hidden="true">
            <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="5" y="2" width="14" height="20" rx="2" ry="2" />
              <path d="M12 18h.01" />
            </svg>
          </div>
          <h3 class="landing-card-title">浏览器即可操作</h3>
          <p class="landing-card-text">
            Vue 响应式界面，桌面与手机浏览器均可使用工作台；下载文件保存在您配置的本机目录，无需额外安装独立 App。
          </p>
        </li>
        <li class="landing-card">
          <div class="landing-card-icon landing-card-icon--film" aria-hidden="true">
            <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="2" y="7" width="20" height="10" rx="1" />
              <path d="M7 7v10M17 7v10M2 12h20" />
            </svg>
          </div>
          <h3 class="landing-card-title">多档清晰度与格式</h3>
          <p class="landing-card-text">
            解析结果中可选不同画质与封装格式，按需平衡体积与清晰度；具体可选集合由平台与提取器返回决定。
          </p>
        </li>
        <li class="landing-card">
          <div class="landing-card-icon landing-card-icon--ai" aria-hidden="true">
            <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 8V4H8" />
              <rect x="4" y="8" width="16" height="12" rx="2" />
              <path d="M9 16h.01M15 16h.01M12 12v4" />
            </svg>
          </div>
          <h3 class="landing-card-title">AI 视频总结与导图</h3>
          <p class="landing-card-text">
            在视频具备<strong>平台内嵌字幕</strong>时，流式生成摘要、大纲、要点与 Mermaid 思维导图，并支持字幕 TXT / SRT / VTT 导出，便于复习与归档。
          </p>
        </li>
      </ul>
    </section>
  </div>
</template>

<style scoped>
.landing-seo-wrap {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.landing-block {
  border-radius: 16px;
  border: 1px solid #d7e2f3;
  background: linear-gradient(180deg, #ffffff 0%, #f6f9ff 100%);
  padding: 16px 18px 18px;
  box-shadow: 0 8px 24px rgba(21, 45, 90, 0.07);
}

.landing-h2 {
  margin: 0 0 8px;
  font-size: clamp(1.05rem, 2vw, 1.25rem);
  font-weight: 800;
  color: #162544;
  letter-spacing: -0.02em;
  font-family: 'Lexend', 'Manrope', sans-serif;
}

.landing-brand {
  color: #1f6fff;
  font-weight: 800;
}

.landing-lead {
  margin: 0 0 16px;
  font-size: 13px;
  line-height: 1.55;
  color: #4a5d86;
  max-width: 72rem;
}

.landing-lead-tight {
  margin-bottom: 14px;
}

.landing-steps {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

@media (max-width: 900px) {
  .landing-steps {
    grid-template-columns: 1fr;
  }
}

.landing-step {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  margin: 0;
  padding: 14px;
  border-radius: 12px;
  background: #fff;
  border: 1px solid #e3ebf7;
  min-height: 100%;
  box-sizing: border-box;
}

.landing-step-num {
  flex-shrink: 0;
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: linear-gradient(140deg, #e8f0ff, #d4e4ff);
  color: #1f6fff;
  font-weight: 800;
  font-size: 15px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: 'Lexend', sans-serif;
}

.landing-step-title {
  margin: 0 0 6px;
  font-size: 14px;
  font-weight: 700;
  color: #1d2a48;
}

.landing-step-text {
  margin: 0;
  font-size: 12px;
  line-height: 1.5;
  color: #516289;
}

.landing-footnote {
  margin: 14px 0 0;
  font-size: 12px;
  line-height: 1.45;
  color: #7a8aac;
}

.landing-cards {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 10px;
}

@media (max-width: 1100px) {
  .landing-cards {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 560px) {
  .landing-cards {
    grid-template-columns: 1fr;
  }
}

.landing-card {
  margin: 0;
  padding: 14px 12px;
  border-radius: 12px;
  background: #fff;
  border: 1px solid #e8eef8;
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-height: 100%;
  box-sizing: border-box;
}

.landing-card-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.landing-card-icon--globe {
  background: #e8f2ff;
  color: #1f6fff;
}
.landing-card-icon--bolt {
  background: #fff4e6;
  color: #e07000;
}
.landing-card-icon--device {
  background: #f0e8ff;
  color: #6b4bd6;
}
.landing-card-icon--film {
  background: #e8faf5;
  color: #0d8f6e;
}
.landing-card-icon--ai {
  background: #e8f7ff;
  color: #0088cc;
}

.landing-card-title {
  margin: 0;
  font-size: 13px;
  font-weight: 700;
  color: #1d2a48;
  line-height: 1.3;
}

.landing-card-text {
  margin: 0;
  font-size: 12px;
  line-height: 1.5;
  color: #516289;
  flex: 1;
}

@media (max-width: 960px) {
  .landing-block {
    padding: 14px 12px 14px;
  }
}
</style>
