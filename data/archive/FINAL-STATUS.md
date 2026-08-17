# LLM Deals — Final Status

**Date:** 2026-08-17
**Git:** master @ c7e95d2
**Status:** OPERATIONAL

## System Summary

### Data
- **2396 offers** from 38 source adapters
- **632 free offers** with utility scoring
- **102 providers** with setup instructions
- **33 claims** + **131 events** in canonical DB
- **65 providers** actively polled

### APIs (5 surfaces)
| Port | API | Endpoints |
|------|-----|-----------|
| 8799 | V1 | 19 (deprecated) |
| 8800 | V2 | 16 (categories) |
| 8801 | V3 | 9 (scoring) |
| 8802 | Hot | 3 (router) |
| 8803 | Canonical | 12 (data layer) |

### MCP (9 tools)
get_dataset_stats, list_models, list_providers, get_provider_setup, find_inference_deals, recommend_model, explain_deal, get_deal_changes, get_dataset_stats

### Kanban (4 boards)
library-production, library-scout, library-verify, library-curate

### Testing
- **10/10 invariant tests** PASS
- **12/12 API endpoints** PASS
- **38/38 source adapters** functional
- **Hermes tested** — found DeepSeek as best deal for coding

## What Hermes Found
> "For 500 calls/day with coding + tool calling: Start with DeepSeek direct API. Free tier covers your needs initially. Off-peak pricing (50% off) for batch work."

## What's Next
1. Wire remaining discovery → claims → evidence
2. Add exponential backoff for sources
3. Add /v1/deals/expiring with real data
4. Add GitHub Actions CI
5. Gold fixture tests
6. Provider expansion (21 more from moreproviders.md)
