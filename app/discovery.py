"""app/discovery.py — Full discovery pipeline orchestrator.

Uses the source adapters from sources/ to fetch, extract, diff, and score deals.
"""
from __future__ import annotations

import os
from pathlib import Path as _Path

# Load .env file if present
_env_file = _Path(__file__).resolve().parents[1] / ".env"
if _env_file.exists():
    for line in _env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

import json
import logging
import time
from pathlib import Path

import db
import promo_extract
import source_diff
import deal_score
import source_health
from sources import registry

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOTS_DIR = ROOT / "snapshots"
EVENTS_DIR = ROOT / "events"


def _ensure_dirs():
    SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    EVENTS_DIR.mkdir(parents=True, exist_ok=True)


def _load_snapshot(source_id: str) -> dict | None:
    p = SNAPSHOTS_DIR / f"{source_id}.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except Exception:
        return None


def _save_snapshot(source_id: str, snapshot: dict):
    p = SNAPSHOTS_DIR / f"{source_id}.json"
    p.write_text(json.dumps(snapshot, indent=2, default=str))


def _save_events(source_id: str, events: list[dict]):
    if not events:
        return
    p = EVENTS_DIR / f"{source_id}_{int(time.time())}.json"
    p.write_text(json.dumps(events, indent=2, default=str))


def run_discovery(sources: list[str] | None = None) -> dict:
    """Run the full discovery pipeline using source adapters.

    Pipeline: fetch -> extract -> diff -> events -> score
    """
    _ensure_dirs()
    t0 = time.time()

    if sources is None:
        due = registry.get_due_sources()
        source_ids = [s.source_id for s in due]
    else:
        source_ids = sources

    all_offers = []
    all_events = []
    all_changes = []
    errors = []
    processed = 0

    for source_id in source_ids:
        adapter = registry.get_adapter(source_id)
        if not adapter:
            errors.append(f"No adapter for {source_id}")
            continue

        logger.info("Processing source: %s", source_id)
        start = time.time()

        try:
            # Fetch
            observations = adapter.fetch()
            latency_ms = (time.time() - start) * 1000

            success = any(o.status is not None and not o.text.startswith("FETCH_ERROR") for o in observations)
            source_health.record_fetch(source_id, success, latency_ms,
                                       None if success else "fetch failed")

            if not success:
                errors.append(f"Fetch failed for {source_id}")
                registry.record_fetch(source_id, False)
                continue

            registry.record_fetch(source_id, True)

            # Extract offers from observations
            source_offers = []
            for obs in observations:
                if obs.status is not None and not obs.text.startswith("FETCH_ERROR"):
                    offers = adapter.extract(obs)
                    source_offers.extend(offers)

            # Deduplicate: same model_id + provider_id = same offer
            seen = set()
            unique_offers = []
            for o in source_offers:
                key = f"{o.model_id}:{o.provider_id}"
                if key not in seen:
                    seen.add(key)
                    unique_offers.append(o)
            source_offers = unique_offers

            # Diff against previous snapshot
            prev = _load_snapshot(source_id)
            curr_hash = observations[0].sha256 if observations else ""

            if prev and prev.get("content_hash") == curr_hash:
                logger.info("Source %s: no change", source_id)
                continue

            # Extract promotion signals from text
            for obs in observations:
                if obs.status is not None and not obs.text.startswith("FETCH_ERROR"):
                    events = promo_extract.extract_promotions(obs.text, source_id)
                    all_events.extend(events)

            # Detect changes
            if prev and prev.get("offers"):
                changes = source_diff.diff_snapshots(prev["offers"], source_offers)
                all_changes.extend(changes)

            # Save snapshot
            _save_snapshot(source_id, {
                "content_hash": curr_hash,
                "offers": [{"provider_id": o.provider_id, "model_id": o.model_id,
                            "input_per_m": o.input_per_m, "output_per_m": o.output_per_m,
                            "cache_read_per_m": o.cache_read_per_m,
                            "free": o.free, "offer_kind": o.offer_kind,
                            "context_tokens": o.context_tokens,
                            "requests_day": o.requests_day,
                            "metadata": o.metadata} for o in source_offers],
                "timestamp": time.time(),
            })

            _save_events(source_id, all_events[-len(source_offers):])
            all_offers.extend(source_offers)
            processed += 1

            logger.info("Source %s: %d offers extracted", source_id, len(source_offers))

        except Exception as e:
            logger.error("Error processing %s: %s", source_id, e)
            errors.append(f"{source_id}: {e}")

    # Score deals
    scored = []
    if all_offers:
        offer_dicts = [{"provider_id": o.provider_id, "model_id": o.model_id,
                        "input_per_m": o.input_per_m, "output_per_m": o.output_per_m,
                        "free": o.free, "offer_kind": o.offer_kind,
                        "requests_day": o.requests_day} for o in all_offers]
        baseline = deal_score.calculate_market_baseline(offer_dicts)
        scored = deal_score.score_deals(offer_dicts, baseline)

    elapsed = time.time() - t0
    report = {
        "timestamp": time.time(),
        "elapsed_seconds": round(elapsed, 2),
        "sources_processed": processed,
        "offers_found": len(all_offers),
        "events_found": len(all_events),
        "changes_detected": len(all_changes),
        "scored_offers": scored[:20],
        "health_status": source_health.get_health(),
        "errors": errors,
    }

    logger.info("Pipeline done: %d sources, %d offers, %d events in %.2fs",
                processed, len(all_offers), len(all_events), elapsed)
    return report


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    srcs = sys.argv[1:] if len(sys.argv) > 1 else None
    r = run_discovery(srcs)
    print(json.dumps(r, indent=2, default=str))
