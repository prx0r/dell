// astro.config.mjs — the deal-radar static site (0-JS, SEO-optimized for agents)
import { defineConfig } from 'astro/config';

// The site serves the canonical LLM-deal data as static pages: best models per task, the free-pool,
// rate limits. 0-JS reading (perf doctrine), semantically marked up, JSON-LD structured data,
// canonical URLs + robots + sitemap — so both humans and AGENTS (crawlers) can discover + parse it.
export default defineConfig({
  output: 'static',
  site: 'https://deal-radar.patala.org',
  compressHTML: true,
  build: { inlineStylesheets: 'auto' },
});
