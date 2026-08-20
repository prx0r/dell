# Dell Source Audit & Cleanup Results

## Summary

Successfully audited and cleaned up Dell data sources from **52 to 21 active sources**.

### Sources Killed (31 total)

#### Redundant Sources (same data, different adapters)
- `awesome-free-llm-apis` - Same URL as `mnfst-free-apis`, kept mnfst version
- `genai-prices` - Only extraction patterns, no actual pricing data
- `context-engineering` - Not relevant to LLM pricing (extracts AGENTS.md patterns)
- `new-providers` - Static config, never changes
- `decentralized-compute` - Static config, never changes
- `mcp-registry` - MCP server catalog, not LLM pricing

#### Covered by litellm (20+ international providers)
- `sakura-ai`, `scaleway`, `ovhcloud`, `akashml`, `perplexity`
- `upstage`, `xiaomi`, `minimax`, `baidu`, `tencent`
- `moonshot`, `infini`, `aion`, `maritaca`, `sarvam`
- `typhoon`, `kilo`, `chutes`, `aethir`, `nosana`
- `nebius`, `io-net`

### Active Sources (21 total)

#### HIGH VALUE - Direct Providers (5)
| Source | Why Keep |
|--------|----------|
| `opencode-go` | Unique OpenCode promotions, usage multipliers |
| `opencode-zen` | OpenCode-specific data |
| `nous-portal` | Nous-specific model catalog |
| `sensenova` | SenseNova-specific data |
| `zai` | Z.AI-specific data |

#### HIGH VALUE - Aggregators (4)
| Source | Why Keep |
|--------|----------|
| `openrouter-models` | Live pricing, free tier detection |
| `hf-router` | Per-provider latency/throughput |
| `artificial-analysis` | Measured benchmarks (TTFT, throughput) |
| `models-dev` | Capabilities, modalities, benchmarks |

#### HIGH VALUE - Pricing Databases (2)
| Source | Why Keep |
|--------|----------|
| `litellm-prices` | 3000+ models, richest structured data |
| `price-performance` | Intelligence scores, parameter counts |

#### HIGH VALUE - Community/Signal (4)
| Source | Why Keep |
|--------|----------|
| `rss-feeds` | Temporal deal detection |
| `hackernews` | Community signals |
| `vercel-changelog` | Launch pricing windows |
| `mnfst-free-apis` | Community-curated free tiers |

#### MEDIUM VALUE - Decentralized (2)
| Source | Why Keep |
|--------|----------|
| `bittensor-subnets` | Decentralized compute data |

#### MEDIUM VALUE - International (4)
| Source | Why Keep |
|--------|----------|
| `alibaba` | Alibaba Bailian-specific data |
| `siliconflow` | SiliconFlow-specific data |
| `nvidia` | NVIDIA NIM-specific data |
| `novita` | Novita-specific data |

#### MEDIUM VALUE - Browser Automation (1)
| Source | Why Keep |
|--------|----------|
| `ego-lite-browser` | Replaces opencode-go if reliable |

## Next Steps: Blog Setup

The Dell web frontend (`/mnt/HC_Volume_106427611/dell/web/`) is currently:
- **Framework**: Astro 5.18.2 (static output)
- **Pages**: `index.astro`, `deals.astro`, `rss.xml.ts`
- **No blog setup yet**

### Recommended Blog Implementation

1. **Create blog directory structure**:
   ```
   web/src/content/blog/
   web/src/pages/blog/
   web/src/pages/blog/[...slug].astro
   ```

2. **Add blog content collections**:
   - `web/src/content/config.ts` - Define blog schema
   - `web/src/content/blog/` - Markdown/MDX files

3. **Blog topics for Dell**:
   - "Best Free LLM APIs in 2026"
   - "How to Choose the Cheapest LLM Provider"
   - "LLM Pricing Comparison Guide"
   - "Decentralized AI Compute: Akash vs Bittensor vs Nosana"
   - "OpenCode Go: Free Usage Multipliers Explained"

4. **SEO optimization**:
   - JSON-LD structured data
   - Canonical URLs
   - Sitemap generation
   - OpenGraph/Twitter cards

5. **Integration with Dell data**:
   - Auto-generate blog posts from deal data
   - "Weekly Deal Roundup" posts
   - "New Provider Spotlight" posts

## Files Modified

### Registry Cleanup
- `app/sources/registry.py` - Reduced from 52 to 21 active sources

### Documentation Created
- `SOURCE_AUDIT_RESULTS.md` - This file

## Current Status

### Database
- **8,609 offers** from 21 active sources
- **2,096 free offers**
- **236 providers**
- All 14/14 Proof Kernel gates passing

### API
- All endpoints working
- Cron polling: 66.9s for 2 sources, 5,224 offers

### Next Development Priority
1. **Blog setup** - Add content marketing
2. **DuckDB migration** - When dataset exceeds 50K offers
3. **Real-time updates** - WebSocket for live deal notifications
4. **MCP server enhancement** - More tools for Hermes agents