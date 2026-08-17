#!/usr/bin/env python3
"""app/cron_poll.py — Autonomous polling script for cron.

Usage:
    python3 -m app.cron_poll          # poll all due sources
    python3 -m app.cron_poll --all    # force poll all sources
    python3 -m app.cron_poll --source sensenova  # poll one source
"""
import sys
import os
import json
import time
import logging
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Load .env
_env = ROOT / ".env"
if _env.exists():
    for line in _env.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

sys.path.insert(0, str(ROOT / "app"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("cron_poll")

from sources import registry
import discovery
import source_health


def poll_all():
    """Poll all sources and write results."""
    t0 = time.time()
    report = discovery.run_discovery()
    elapsed = time.time() - t0

    # Write poll report
    report_path = ROOT / "data" / "poll-report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, default=str))

    logger.info("Poll complete: %d sources, %d offers, %d events in %.1fs",
                report.get("sources_processed", 0),
                report.get("offers_found", 0),
                report.get("events_found", 0),
                elapsed)
    return report


def poll_source(source_id):
    """Poll a single source."""
    adapter = registry.get_adapter(source_id)
    if not adapter:
        logger.error("No adapter for %s", source_id)
        return None

    t0 = time.time()
    try:
        obs = adapter.fetch()
        offers = []
        for o in obs:
            if o.status is not None and not o.text.startswith("FETCH_ERROR"):
                offers.extend(adapter.extract(o))
        registry.record_fetch(source_id, True)
        elapsed = time.time() - t0
        logger.info("Source %s: %d offers in %.1fs", source_id, len(offers), elapsed)
        return offers
    except Exception as e:
        registry.record_fetch(source_id, False)
        logger.error("Source %s failed: %s", source_id, e)
        return None


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--source", type=str)
    args = parser.parse_args()

    if args.source:
        poll_source(args.source)
    else:
        poll_all()
