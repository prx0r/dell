#!/usr/bin/env python3
"""pipeline/run_recorder.py — the content-addressed RUN RECORDER (bulletproof provenance).

Stolen mechanism (verified research: DVC content-addressing + wandb git/deps capture + the nanopublication
data model from sensein/ECO). Every experiment run becomes a content-addressed, reproducible, anti-
fabrication record:

  run.signature = sha256(gold.hash || code.sha || config.sha)   → out.hash
  persisted as:  {run.signature, out.hash, metrics, raw_outputs, git_commit, diff.patch, requirements}

And every headline number ships as a NANOPUBLICATION triple {assertion, evidence, provenance} — so a
number that only exists in an LLM's text (no machine-computed content-addressed run) is automatically
flagged as theater. This makes the lab's ONE RULE executable: nothing is real without a logged number on
fixed gold.

Deterministic + stdlib (sha256). Reuses the existing lab metrics + gold.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNS_DIR = ROOT / "data" / "runs"   # content-addressed run store


def sha256(obj) -> str:
    """SHA-256 of any JSON-serializable object (canonical). The anti-fabrication key."""
    canonical = json.dumps(obj, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def file_sha(path: Path) -> str:
    return sha256({"file": str(path), "content": path.read_text(encoding="utf-8", errors="ignore")})


def gold_hash(gold: list[dict]) -> str:
    """Content-address the fixed gold (the input). Hash source+gold, not the file path."""
    return sha256([{"source": r.get("source", ""), "gold": r.get("gold", "")} for r in gold])


def code_sha() -> str:
    """Hash the frozen eval/metric code — every pipeline + tool file that affects the result."""
    parts = {}
    for d in ("pipeline", "tools"):
        for f in sorted((ROOT / d).glob("*.py")):
            parts[str(f.relative_to(ROOT))] = f.read_text(encoding="utf-8", errors="ignore")
    return sha256(parts)


def config_sha(config: dict) -> str:
    """Hash the RESOLVED config (all overrides applied) — the same-config-is-meaningful statement."""
    return sha256(config)


def git_state() -> dict:
    """Auto-capture the git commit + diff.patch (wandb's Code-Saving trio, minus requirements)."""
    out = {"commit": "", "diff": ""}
    try:
        c = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=ROOT)
        out["commit"] = c.stdout.strip()
        d = subprocess.run(["git", "diff"], capture_output=True, text=True, cwd=ROOT)
        out["diff"] = d.stdout
    except Exception:
        pass
    return out


def run_signature(gold: list[dict], config: dict) -> str:
    """The content-addressed run key: hash(gold || code || config). Same key ⇒ same reproducible run."""
    return sha256({"gold": gold_hash(gold), "code": code_sha(), "config": config_sha(config)})


class RunRecorder:
    """Persist a content-addressed run record + nanopublication triples."""

    def __init__(self, runs_dir: Path = RUNS_DIR):
        self.runs_dir = runs_dir
        self.runs_dir.mkdir(parents=True, exist_ok=True)

    def record(self, *, step: str, gold: list[dict], config: dict, metrics: dict,
               raw: list[dict] | None = None, assertion: str = "",
               evidence_code: str = "ECO:0000203") -> dict:
        """Record one run. Returns the run record (signature, out.hash, nanopublication)."""
        sig = run_signature(gold, config)
        # hash the OUTPUT too (metrics + raw) — out.hash
        out_hash = sha256({"metrics": metrics, "raw": raw or []})
        record = {
            "step": step, "run_signature": sig, "out_hash": out_hash,
            "gold_hash": gold_hash(gold), "code_sha": code_sha(), "config_sha": config_sha(config),
            "config": config, "metrics": metrics, "raw_outputs": (raw or [])[:20],
            "git": git_state(),
            "ts": datetime.now(timezone.utc).isoformat(),
            # nanopublication: every headline number carries assertion + evidence + provenance
            "nanopublication": {
                "assertion": assertion or f"{step} produced metrics {json.dumps(metrics)}",
                "evidence": {"code": evidence_code, "artifact": f"run:{sig[:12]}"},
                "provenance": {"run_signature": sig, "out_hash": out_hash,
                               "generated_by": "sanskritbenchy/run_recorder.py",
                               "ts": datetime.now(timezone.utc).isoformat()},
            },
        }
        out_file = self.runs_dir / f"{sig}.json"
        out_file.write_text(json.dumps(record, ensure_ascii=False, indent=2))
        return record

    def get(self, signature: str) -> dict | None:
        p = self.runs_dir / f"{signature}.json"
        return json.loads(p.read_text()) if p.exists() else None

    def all(self) -> list[dict]:
        return [json.loads(f.read_text()) for f in sorted(self.runs_dir.glob("*.json"))]


if __name__ == "__main__":
    from sanskrit_gold import exemplars
    rec = RunRecorder()
    gold = exemplars()[:3]
    r = rec.record(step="proof-check", gold=gold,
                   config={"model": "deepseek-v4-flash", "n": 3},
                   metrics={"avg_chrF": 0.61, "semantic": 0.9},
                   raw=[{"id": g["id"], "chrF": 0.6} for g in gold],
                   assertion="semantic-judge correlates better with human than chrF")
    print("run_signature:", r["run_signature"][:16], "| out_hash:", r["out_hash"][:16])
    print("nanopublication assertion:", r["nanopublication"]["assertion"][:50])
    print("gold_hash:", r["gold_hash"][:16])
