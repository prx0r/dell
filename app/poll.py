"""Poll scheduler for determining which sources are due for polling."""

import os
import time
import json
import logging

# Load .env
from pathlib import Path as _Path
_env = _Path(__file__).resolve().parents[1] / ".env"
if _env.exists():
    for line in _env.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())
import argparse
from typing import Optional
from pathlib import Path

import discovery
import source_health

logger = logging.getLogger(__name__)

CONFIG_PATH = Path(__file__).parent.parent / "sources.json"
STATE_PATH = Path(__file__).parent.parent / "poll_state.json"

DEFAULT_CADENCE_SECONDS = 3600


def _load_config() -> dict:
    """Load sources configuration."""
    if not CONFIG_PATH.exists():
        return {"sources": []}
    try:
        return json.loads(CONFIG_PATH.read_text())
    except Exception as exc:
        logger.error("Failed to load config: %s", exc)
        return {"sources": []}


def _load_state() -> dict:
    """Load poll state (last poll times per source)."""
    if not STATE_PATH.exists():
        return {}
    try:
        return json.loads(STATE_PATH.read_text())
    except Exception as exc:
        logger.error("Failed to load poll state: %s", exc)
        return {}


def _save_state(state: dict) -> None:
    """Persist poll state."""
    try:
        STATE_PATH.write_text(json.dumps(state, indent=2))
    except Exception as exc:
        logger.error("Failed to save poll state: %s", exc)


def _get_due_sources(config: dict, state: dict) -> list[dict]:
    """Determine which sources are due for polling based on cadence."""
    now = time.time()
    due = []

    for source in config.get("sources", []):
        source_id = source.get("id", "unknown")
        cadence = source.get("cadence_seconds", DEFAULT_CADENCE_SECONDS)
        last_poll = state.get(source_id, {}).get("last_poll_time", 0)
        elapsed = now - last_poll

        if elapsed >= cadence:
            due.append(source)
            logger.debug(
                "Source %s is due: elapsed=%.0fs >= cadence=%ds",
                source_id,
                elapsed,
                cadence,
            )
        else:
            remaining = cadence - elapsed
            logger.debug(
                "Source %s not due yet: %.0fs remaining",
                source_id,
                remaining,
            )

    return due


def _update_state(state: dict, source_id: str) -> dict:
    """Update poll state for a source after polling."""
    if source_id not in state:
        state[source_id] = {}
    state[source_id]["last_poll_time"] = time.time()
    state[source_id]["poll_count"] = state[source_id].get("poll_count", 0) + 1
    return state


def poll_due() -> dict:
    """Poll all sources that are due based on their configured cadence.

    Returns:
        Report dict with fields:
            timestamp, sources_due, sources_polled, report (from discovery)
    """
    logger.info("=== Poll Due: checking for due sources ===")
    config = _load_config()
    state = _load_state()

    due_sources = _get_due_sources(config, state)

    if not due_sources:
        logger.info("No sources due for polling")
        return {
            "timestamp": time.time(),
            "sources_due": 0,
            "sources_polled": 0,
            "report": None,
            "message": "No sources due",
        }

    logger.info("Found %d due sources", len(due_sources))

    report = discovery.run_discovery(sources=due_sources)

    for source in due_sources:
        source_id = source.get("id", "unknown")
        state = _update_state(state, source_id)

    _save_state(state)

    result = {
        "timestamp": time.time(),
        "sources_due": len(due_sources),
        "sources_polled": report.get("sources_processed", 0),
        "report": report,
    }

    logger.info(
        "=== Poll Due complete: %d due, %d processed ===",
        result["sources_due"],
        result["sources_polled"],
    )
    return result


def poll_all() -> dict:
    """Poll all configured sources regardless of cadence.

    Returns:
        Report dict from run_discovery.
    """
    logger.info("=== Poll All: polling all sources ===")
    config = _load_config()
    state = _load_state()

    all_sources = config.get("sources", [])
    if not all_sources:
        logger.warning("No sources configured")
        return {
            "timestamp": time.time(),
            "sources_due": 0,
            "sources_polled": 0,
            "report": None,
            "message": "No sources configured",
        }

    report = discovery.run_discovery(sources=all_sources)

    for source in all_sources:
        source_id = source.get("id", "unknown")
        state = _update_state(state, source_id)

    _save_state(state)

    result = {
        "timestamp": time.time(),
        "sources_due": len(all_sources),
        "sources_polled": report.get("sources_processed", 0),
        "report": report,
    }

    logger.info(
        "=== Poll All complete: %d processed ===",
        result["sources_polled"],
    )
    return result


def poll_source(source_id: str) -> dict:
    """Poll a specific source by ID.

    Args:
        source_id: The identifier of the source to poll.

    Returns:
        Report dict from run_discovery for just that source.
    """
    logger.info("=== Poll Source: %s ===", source_id)
    config = _load_config()
    state = _load_state()

    source = None
    for s in config.get("sources", []):
        if s.get("id") == source_id:
            source = s
            break

    if source is None:
        logger.error("Source %s not found in config", source_id)
        return {
            "timestamp": time.time(),
            "sources_due": 0,
            "sources_polled": 0,
            "report": None,
            "message": f"Source {source_id} not found",
        }

    report = discovery.run_discovery(sources=[source])
    state = _update_state(state, source_id)
    _save_state(state)

    return {
        "timestamp": time.time(),
        "sources_due": 1,
        "sources_polled": report.get("sources_processed", 0),
        "report": report,
    }


def _setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Deal Radar Poll Scheduler")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--due", action="store_true", help="Poll only sources that are due")
    group.add_argument("--all", action="store_true", dest="all_sources", help="Poll all sources")
    group.add_argument("--source", type=str, help="Poll a specific source by ID")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable debug logging")

    args = parser.parse_args()
    _setup_logging(args.verbose)

    if args.due:
        result = poll_due()
    elif args.all_sources:
        result = poll_all()
    elif args.source:
        result = poll_source(args.source)
    else:
        parser.print_help()
        return

    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
