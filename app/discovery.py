"""app/discovery.py — Full discovery pipeline orchestrator.

Writes to canonical SQLite DB. JSON snapshots become exports.
"""
from __future__ import annotations

import os
from pathlib import Path as _Path

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

import canonical_db
import promo_extract
import source_diff
import source_health
import event_recorder
import discovery_claims
from sources import registry

ROOT = Path(__file__).resolve().parents[1]
logger = logging.getLogger(__name__)


def run_discovery(sources: list[str] | None = None) -> dict:
    """Run the full discovery pipeline. Writes to canonical SQLite DB."""
    if sources is None:
        sources = [s.source_id for s in registry.get_due_sources()]

    conn = canonical_db.connect()
    canonical_db.migrate(conn)

    t0 = time.time()
    all_offers = []
    all_events = []
    errors = []

    for source_id in sources:
        adapter = registry.get_adapter(source_id)
        if not adapter:
            errors.append("No adapter for %s" % source_id)
            continue

        src_entry = registry.SOURCES.get(source_id)
        if not src_entry:
            continue

        logger.info("Processing %s", source_id)
        t_start = time.time()

        try:
            observations = adapter.fetch()
            latency = (time.time() - t_start) * 1000

            success = any(o.status is not None and not o.text.startswith("FETCH_ERROR")
                          and "MISSING_KEY" not in o.text and "RATE_LIMITED" not in o.text
                          for o in observations)

            # Record ALL observations (P0.6 fix — not just first)
            obs_ids = []
            for obs in observations:
                if obs.status is not None and not obs.text.startswith("FETCH_ERROR"):
                    obs_id = canonical_db.insert_observation(
                        conn, source_id, obs.url or "",
                        obs.status or 0, obs.sha256, 0)
                    obs_ids.append(obs_id)

            # Record fetch status
            source_health.record_fetch(source_id, success, latency,
                                       None if success else "fetch failed")
            canonical_db.update_source_fetch(conn, source_id, success)

            if not success:
                errors.append("Fetch failed for %s" % source_id)
                registry.record_fetch(source_id, False)
                continue

            registry.record_fetch(source_id, True)

            # Extract offers from ALL observations (not just first)
            source_offers = []
            all_claims = []
            for obs in observations:
                if obs.status is not None and not obs.text.startswith("FETCH_ERROR"):
                    offers = adapter.extract(obs)
                    source_offers.extend(offers)

                    # Extract claims from this observation (P0.4)
                    if obs_ids:
                        claims = discovery_claims.extract_claims_from_adapter(adapter, obs)
                        discovery_claims.commit_claims(conn, claims, obs_ids[-1])
                        all_claims.extend(claims)

            # Deduplicate by offer_id
            seen = set()
            unique = []
            for o in source_offers:
                oid = canonical_db.generate_offer_id(
                    o.provider_id, o.model_id, o.offer_kind, None)
                if oid not in seen:
                    seen.add(oid)
                    o_dict = o.__dict__.copy()
                    o_dict["offer_id"] = oid
                    unique.append(o_dict)
            source_offers = unique

            # Write to canonical DB with ALL adapter data
            for o in source_offers:
                meta = o.get("metadata", {})
                canonical_db.upsert_offer(
                    conn, o["offer_id"], o.get("provider_id", ""),
                    o.get("model_id", ""), o.get("offer_kind", "metered_api"),
                    o.get("input_per_m"), o.get("output_per_m"),
                    o.get("free", False), o.get("context_tokens"),
                    o.get("requests_per_day"),
                    source_url=meta.get("source_url"),
                    region=None,
                    cache_read_per_m=o.get("cache_read_per_m"),
                    requests_per_5h=o.get("requests_per_5h") or meta.get("requests_per_5h"),
                    requests_per_minute=o.get("requests_minute"),
                    quota_scope=meta.get("scope"),
                    quota_window_hours=meta.get("window_hours"),
                    usage_multiplier=o.get("usage_multiplier") or meta.get("multiplier"),
                    capacity_multiplier=meta.get("capacity_multiplier"),
                    max_output_tokens=o.get("max_output_tokens"),
                    automation_allowed=meta.get("automation_allowed"),
                    deal_type=o.get("offer_kind"),
                    metadata_json=json.dumps(meta))

            # Record promotion events (P0.12)
            for obs in observations:
                if obs.status is not None and not obs.text.startswith("FETCH_ERROR"):
                    events = promo_extract.extract_promotions(obs.text, source_id)
                    for event in events:
                        event_recorder.record_event(
                            conn, source_id, event.get("event_type", "unknown"),
                            current_value=event, source_url=obs.url or "")

            all_offers.extend(source_offers)
            logger.info("%s: %d offers, %d claims", source_id, len(source_offers), len(all_claims))

        except Exception as e:
            logger.error("Error processing %s: %s", source_id, e)
            errors.append("%s: %s" % (source_id, str(e)[:100]))

    conn.commit()

    # Export snapshots for backward compatibility
    _export_snapshots(conn)

    elapsed = time.time() - t0
    report = {
        "timestamp": time.time(),
        "elapsed_seconds": round(elapsed, 2),
        "sources_processed": len([e for e in errors if "No adapter" not in e]),
        "offers_found": len(all_offers),
        "events_found": len(all_events),
        "errors": errors,
        "canonical_db": str(canonical_db.DB_PATH),
    }

    logger.info("Pipeline done: %d sources, %d offers in %.2fs",
                report["sources_processed"], report["offers_found"], elapsed)
    return report


def _export_snapshots(conn):
    """Export canonical DB to JSON snapshots for backward compatibility."""
    snapshots_dir = ROOT / "snapshots"
    snapshots_dir.mkdir(parents=True, exist_ok=True)

    # Export by provider
    rows = conn.execute("SELECT DISTINCT provider_id FROM offers").fetchall()
    for row in rows:
        provider_id = row["provider_id"]
        offers = conn.execute(
            "SELECT * FROM offers WHERE provider_id = ?", (provider_id,)).fetchall()
        snapshot = {
            "offers": [dict(r) for r in offers],
            "exported_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        path = snapshots_dir / ("%s.json" % provider_id)
        with open(path, "w") as f:
            json.dump(snapshot, f)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    import sys
    sources = sys.argv[1:] if len(sys.argv) > 1 else None
    run_discovery(sources)

# Integration point for source_diff (P0.12)
# After extracting offers, compare with previous snapshot
# and record changes as deal_events
