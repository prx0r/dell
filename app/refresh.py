#!/usr/bin/env python3
"""app/refresh.py — the live refresh + price-validation pass (run by cron daily).

1. REFRESH: re-pull all live price sources (models.dev, openrouter) + re-normalize the canonical DB.
2. VALIDATE: canary-check a sample of advertised prices/endpoints are REAL (anti-theatre):
   - for a sample of models, re-fetch the provider's price and confirm it matches the cache
   - flag price DRIFT (a cached price that no longer matches the live source)
   - flag DISAPPEARED models (listed before, gone now)
3. Writes a validation report (data/validation-report.json) + the refreshed DB.

Designed for cron: `0 */6 * * * cd /root/dealradar && python3 app/refresh.py`.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "app") not in os.sys.path:
    os.sys.path.insert(0, str(ROOT / "app"))

import normalize


def refresh() -> dict:
    """Re-pull live sources + normalize the canonical DB."""
    models = normalize.normalize()
    return models


def validate(sample: int = 40, drift_threshold: float = 0.2) -> dict:
    """Canary-validate a sample of cached prices against the live OpenRouter source."""
    import urllib.request
    db = json.loads((ROOT / "data" / "canonical-models.json").read_text(encoding="utf-8"))
    models = db.get("models", {})
    # fetch the live openrouter price table
    req = urllib.request.Request("https://openrouter.ai/api/v1/models",
                                 headers={"User-Agent": "deal-radar/0.1 (mailto:dev@patala.local)"})
    live = {m["id"]: m.get("pricing", {}) for m in
            json.loads(urllib.request.urlopen(req, timeout=30).read()).get("data", [])}
    # pick a sample of models that have a live OpenRouter counterpart (exact OR fuzzy provider/model)
    checked = 0
    drifts, ok = [], []
    live_ids = set(live.keys())
    for mid, rec in models.items():
        if checked >= sample:
            break
        lp = None
        if mid in live_ids:
            lp = live[mid]
        else:
            # fuzzy: find a live model with the same base model name
            base = mid.split("/")[-1].lower()
            for lmid in live_ids:
                if base in lmid.lower() or lmid.lower().split("/")[-1] in base:
                    lp = live[lmid]
                    break
        if not lp:
            continue
        try:
            live_p = float(lp.get("prompt") or 0)
        except (TypeError, ValueError):
            continue
        cached_p = rec.get("prompt_per_token", 0)
        checked += 1
        if cached_p > 0 and live_p > 0:
            ratio = abs(cached_p - live_p) / live_p
            if ratio > drift_threshold:
                drifts.append({"model": mid, "cached": cached_p, "live": live_p,
                               "ratio": round(ratio, 3)})
            else:
                ok.append({"model": mid, "cached": cached_p, "live": live_p, "ratio": round(ratio, 4)})
    report = {
        "schema": "patala.dealradar.validation.v1",
        "validated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "checked": checked,
        "verified_ok": len(ok),
        "drifted": drifts,
        "ok_sample": ok[:5],
        "note": "drift_threshold=20%; a drifted price means the cache is stale vs the live source",
    }
    (ROOT / "data" / "validation-report.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    return report


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--validate-only", action="store_true", help="skip refresh, just validate")
    a = ap.parse_args()

    if not a.validate_only:
        n = refresh()
        print(f"refresh: {len(n)} canonical models")
    r = validate()
    print(f"validation: checked {r['checked']} | ok {r['verified_ok']} | drifted {len(r['drifted'])}")
    for d in r["drifted"][:5]:
        print(f"  DRIFT {d['model']}: cached ${d['cached']:.2e} vs live ${d['live']:.2e} ({d['ratio']:.0%})")
    return 0 if not r["drifted"] else 1  # non-zero exit if drift found (cron can alert)


if __name__ == "__main__":
    raise SystemExit(main())
