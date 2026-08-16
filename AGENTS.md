# AGENTS.md — dealradar (the live LLM price + quality service)

*2026-08-16 · The governing file for any agent working in this project. Read this FIRST, then `VISION.md`,
then the root `AGENTS.md` for the box rules. This file defines the ONE RULE + the **deterministic anti-mess
standard** shared with `sanskritbenchy`.*

---

## 0. THE ONE RULE

> **Nothing is "real" because a model is listed. It is real only when a logged test passes on real data,
> the price/quality resolves to a verified source, and the number is machine-computed — not asserted.**

## 1. THE DETERMINISTIC ANTI-MESS STANDARD (same as sanskritbenchy)

1. **Timestamp every build note / handover** (`HANDSOVER-YYYY-MM-DD.md` or `*YYYY-MM-DD*` header).
2. **Track every run + experiment with a log.** Run steps via `agent/run.py --step X` → logs to
   `data/agent-runs.jsonl` + `data/runs/agent-steps.jsonl`. Query with `python3 agent/trace.py`.
3. **Content-address every headline number.** Use `app/run_recorder.py`
   (`sha256(gold ‖ code ‖ config) → out_hash` + nanopublication). A number with no run record is theater.
4. **Register every doc/script in the MANIFEST** or `check.py` flags it.
5. **Audit on fixed data.** `agent/audit.py --bench suite` recomputes the tests and fails on mismatch.
6. **One concern = one doc; reference, don't copy.**

## 2. THE GATE

```bash
cd /root/dealradar
export PYTHONPATH=app:.
python3 app/test.py          # 65 PASS (the test suite)
python3 agent/audit.py --bench suite   # the golden-file audit
python3 agent/trace.py --all           # every run is logged
```

## 3. THE BOX RULES (from the root AGENTS.md)

- **Never `sleep` to wait**; **never `pkill`** (kill by exact PID).
- **RAM is the scarcest resource** — refresh/canary hit the network; run one at a time, ~2GB free.
- **Reuse, don't rebuild** (litellm, llm-prices, awesome-free-llm-apis are the sources).
- **Quality = measured, not marketing** (`quality_source=measured`).

## 4. THE STANDARD IN ONE SENTENCE

> **Timestamped, logged, content-addressed, registered** — every build note is dated, every run is in the
> trace, every number is a content-addressed nanopublication on fixed data, every doc is in the MANIFEST,
> and `test.py` + `audit.py` + `trace.py` enforce it deterministically.
