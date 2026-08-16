---
name: deal-radar
description: "Drive the dealradar LLM price + quality service: pick the best model for a task, check live prices/canary, run the test gate, and audit for legitimacy — kanban-aware."
version: 1.0.0
date: 2026-08-16
author: dealradar
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [LLM, Pricing, Models, Routing, Benchmark, MCP]
    related_skills: [sanskrit-benchy]
---

# Deal-Radar (LLM price + quality service)

Drive the service at `/root/dealradar`. Board: `dealradar` (hermes kanban). The goal: aggregate all
machine-readable LLM pricing + measured quality into ONE canonical model DB and recommend the best model
for a task with full reasoning.

## The command map

| Command | What it does |
|---|---|
| `python3 agent/run.py --step report` | canonical model count + free-tier count |
| `--step recommend --task coding` | recommend the best model for a task |
| `--step refresh` | check live prices + drift |
| `--step canary` | probe the free providers (live) |
| `--step validate` | run all tests (the gate) |
| `--step watchdog` | refresh → canary → validate → report cycle |
| `python3 agent/audit.py --bench suite` | the golden-file audit (recompute on fixed data) |

## The MCP interface (primary)

`mcp/server.py` — 6 goal-oriented tools: `pick_model`, `check_live_prices`, `get_model_details`,
`get_free_sources`, `recommend_for_query`, `recommend_model_for_layer`.

## The standard loop

```bash
cd /root/dealradar
export PYTHONPATH=app:.

# 1. health + legitimacy
python3 agent/run.py --step report
python3 agent/audit.py --list

# 2. pick a model
python3 agent/run.py --step recommend --task coding

# 3. the gate
python3 agent/run.py --step validate
```

## Kanban (Phase P1–P5)

- P1 ingest Tier-1 providers · P2 LLM-reasons moat · P3 merge tension+routing · P4 layer integration ·
  P5 hardening+deploy. `hermes kanban list` to see; claim/comment/complete as gates pass.

## The honest rules

1. No claim without a logged test on real data (`agent/run.py --step validate`).
2. Every price/quality resolves to a verified source (`quality_source=measured`).
3. The golden audit recomputes on fixed data and fails on mismatch (`agent/audit.py`).
4. Box rules: refresh/canary hit the network — one at a time, ~2GB free.
5. Never fabricate a result; a failed step is logged as failed.
