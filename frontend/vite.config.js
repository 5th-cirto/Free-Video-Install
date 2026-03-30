import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath, URL } from 'node:url'

import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const siteUrl = (env.VITE_PUBLIC_SITE_URL || '').replace(/\/$/, '')
  const rawOg = (env.VITE_PUBLIC_OG_IMAGE || '').trim()

  function resolveOgImageAbsolute(site, og) {
    if (!og || !site) return ''
    if (/^https?:\/\//i.test(og)) return og.replace(/\/$/, '')
    const p = og.startsWith('/') ? og : `/${og}`
    return `${site}${p}`
  }

  const ogImageAbs = resolveOgImageAbsolute(siteUrl, rawOg)

  return {
    plugins: [
      vue(),
      vueDevTools(),
      {
        name: 'seo-html-and-sitemap',
        transformIndexHtml(html) {
          const base = siteUrl ? `${siteUrl}/` : '/'
          let out = html.replaceAll('__SEO_PUBLIC_ROOT__', base)

          const ogMeta =
            ogImageAbs &&
            `    <meta property="og:image" content="${ogImageAbs}" />\n    <meta name="twitter:image" content="${ogImageAbs}" />`
          out = out.replace('__OG_IMAGE_META__', ogMeta || '')

          const twitterCard = ogImageAbs ? 'summary_large_image' : 'summary'
          out = out.replace('__TWITTER_CARD__', twitterCard)

          if (!siteUrl) {
            out = out.replace(/\s*<meta property="og:url" content="\/" \/>/i, '')
          }

          const ldMatch = out.match(
            /<script type="application\/ld\+json">\s*([\s\S]*?)\s*<\/script>/i,
          )
          if (ldMatch) {
            try {
              const data = JSON.parse(ldMatch[1])
              const graph = Array.isArray(data['@graph']) ? data['@graph'] : []
              if (ogImageAbs) {
                for (const node of graph) {
                  if (node && (node['@type'] === 'WebSite' || node['@type'] === 'WebApplication')) {
                    node.image = ogImageAbs
                  }
                }
              }
              const replaced = `<script type="application/ld+json">\n${JSON.stringify(data)}\n    </script>`
              out = out.replace(ldMatch[0], replaced)
            } catch {
              /* 保持原始 LD+JSON，避免构建失败 */
            }
          }

          return out
        },
        writeBundle(options) {
          if (!options.dir) return

          const llmsSrc = path.join(__dirname, 'public', 'llms.txt')
          if (fs.existsSync(llmsSrc)) {
            let body = fs.readFileSync(llmsSrc, 'utf8')
            const canonicalHost = (siteUrl || 'https://aivideofetch.cn').replace(/\/$/, '')
            body = body.replace(/https:\/\/aivideofetch\.cn/g, canonicalHost)
            fs.writeFileSync(path.join(options.dir, 'llms.txt'), body)
          }

          if (!siteUrl) return

          const indexUrl = `${siteUrl}/`
          const llmsUrl = `${siteUrl}/llms.txt`
          const lastmod = new Date().toISOString().slice(0, 10)
          const sitemap = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>${indexUrl}</loc>
    <lastmod>${lastmod}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>1.0</priority>
  </url>
  <url>
    <loc>${llmsUrl}</loc>
    <lastmod>${lastmod}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.5</priority>
  </url>
</urlset>
`
          fs.writeFileSync(path.join(options.dir, 'sitemap.xml'), sitemap.trimStart())
          const robots = `# 常见 AI / 检索爬虫（Allow 与全站一致；厂商实际 User-Agent 可能变更，请按需更新）
User-agent: GPTBot
Allow: /

User-agent: ChatGPT-User
Allow: /

User-agent: Google-Extended
Allow: /

User-agent: ClaudeBot
Allow: /

User-agent: anthropic-ai
Allow: /

User-agent: PerplexityBot
Allow: /

User-agent: Applebot-Extended
Allow: /

User-agent: *
Allow: /

Sitemap: ${siteUrl}/sitemap.xml

# GEO（生成式检索事实摘要）: ${siteUrl}/llms.txt
`
          fs.writeFileSync(path.join(options.dir, 'robots.txt'), robots)
        },
      },
    ],
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url)),
      },
    },
  }
})
