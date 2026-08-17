"""app/db.py — SQLite kernel for Deal Radar V2.

WAL mode, strict typing, content-addressed observations.
All writes go through this module. Reads can use raw sqlite3 for performance.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "deal-radar.sqlite3"

SCHEMA_VERSION = 2


def connect(db_path: str | Path | None = None) -> sqlite3.Connection:
    path = str(db_path or DB_PATH)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.row_factory = sqlite3.Row
    return conn


def migrate(conn: sqlite3.Connection) -> None:
    """Apply schema.sql if not already applied."""
    schema_path = ROOT / "app" / "schema.sql"
    if not schema_path.exists():
        return
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'")
    if cur.fetchone() is None:
        conn.executescript(schema_path.read_text())
        conn.execute("INSERT INTO schema_version (version) VALUES (?)", (SCHEMA_VERSION,))
        conn.commit()


@contextmanager
def transaction(conn: sqlite3.Connection):
    """Context manager for a write transaction."""
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def content_hash(data) -> str:
    """SHA-256 content hash for deduplication."""
    return hashlib.sha256(json.dumps(data, sort_keys=True, default=str).encode()).hexdigest()


# --- Upsert helpers ---

def upsert_model(conn, model_id, canonical_name, author=None, family=None,
                 context_tokens=None, max_output_tokens=None, reasoning=False,
                 tool_call=False, structured_output=False, open_weights=False,
                 metadata=None):
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    conn.execute("""
        INSERT INTO models (model_id, canonical_name, author, family, context_tokens,
            max_output_tokens, reasoning, tool_call, structured_output, open_weights,
            metadata_json, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(model_id) DO UPDATE SET
            canonical_name=excluded.canonical_name, author=COALESCE(excluded.author, models.author),
            family=COALESCE(excluded.family, models.family),
            context_tokens=COALESCE(excluded.context_tokens, models.context_tokens),
            max_output_tokens=COALESCE(excluded.max_output_tokens, models.max_output_tokens),
            reasoning=excluded.reasoning OR models.reasoning,
            tool_call=excluded.tool_call OR models.tool_call,
            structured_output=excluded.structured_output OR models.structured_output,
            open_weights=excluded.open_weights OR models.open_weights,
            metadata_json=json_patch(models.metadata_json, excluded.metadata_json),
            updated_at=excluded.updated_at
    """, (model_id, canonical_name, author, family, context_tokens, max_output_tokens,
          int(reasoning), int(tool_call), int(structured_output), int(open_weights),
          json.dumps(metadata or {}), now, now))


def upsert_provider(conn, provider_id, name, kind="api", homepage=None, api_base=None, metadata=None):
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    conn.execute("""
        INSERT INTO providers (provider_id, name, kind, homepage, api_base, metadata_json)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(provider_id) DO UPDATE SET
            name=excluded.name, kind=excluded.kind,
            homepage=COALESCE(excluded.homepage, providers.homepage),
            api_base=COALESCE(excluded.api_base, providers.api_base)
    """, (provider_id, name, kind, homepage, api_base, json.dumps(metadata or {})))


def upsert_offer(conn, offer_id, provider_id, model_id=None, provider_model_slug=None,
                 plan_id=None, offer_kind="metered_api", region=None, currency="USD",
                 active=True, metadata=None):
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    conn.execute("""
        INSERT INTO offers (offer_id, provider_id, model_id, provider_model_slug, plan_id,
            offer_kind, region, currency, active, metadata_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(offer_id) DO UPDATE SET
            active=excluded.active, metadata_json=json_patch(offers.metadata_json, excluded.metadata_json)
    """, (offer_id, provider_id, model_id, provider_model_slug, plan_id,
          offer_kind, region, currency, int(active), json.dumps(metadata or {}), now))


def insert_observation(conn, source_id, source_type, url, http_status=None,
                       content_text=None, etag=None, last_modified=None, metadata=None):
    """Insert a source observation. Returns (observation_id, content_sha256)."""
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    sha = content_hash(content_text) if content_text else None
    cur = conn.execute("""
        INSERT INTO source_observations (source_id, source_type, url, fetched_at,
            http_status, etag, last_modified, content_sha256, extraction_status, metadata_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)
    """, (source_id, source_type, url, now, http_status, etag, last_modified,
          sha, json.dumps(metadata or {})))
    return cur.lastrowid, sha


def insert_snapshot_if_changed(conn, offer_id, snapshot_data, observation_id):
    """Insert offer snapshot only if economically different from previous. Returns True if new."""
    prev = conn.execute("""
        SELECT input_per_m, output_per_m, cache_read_per_m, free, requests_day
        FROM offer_snapshots WHERE offer_id=? ORDER BY snapshot_id DESC LIMIT 1
    """, (offer_id,)).fetchone()

    new_hash = content_hash(snapshot_data)
    if prev:
        prev_hash = content_hash({
            "i": prev["input_per_m"], "o": prev["output_per_m"],
            "c": prev["cache_read_per_m"], "f": prev["free"], "r": prev["requests_day"]
        })
        if prev_hash == new_hash:
            return False

    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    conn.execute("""
        INSERT INTO offer_snapshots (offer_id, observed_at, input_per_m, output_per_m,
            cache_read_per_m, cache_write_per_m, subscription_usd, included_nominal_usd,
            credits_included, usage_multiplier, requests_5h, requests_day, requests_week,
            requests_month, tokens_day, context_tokens, max_output_tokens, free,
            starts_at, expires_at, source_observation_id, parsed_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (offer_id, now,
          snapshot_data.get("input_per_m"), snapshot_data.get("output_per_m"),
          snapshot_data.get("cache_read_per_m"), snapshot_data.get("cache_write_per_m"),
          snapshot_data.get("subscription_usd"), snapshot_data.get("included_nominal_usd"),
          snapshot_data.get("credits_included"), snapshot_data.get("usage_multiplier"),
          snapshot_data.get("requests_5h"), snapshot_data.get("requests_day"),
          snapshot_data.get("requests_week"), snapshot_data.get("requests_month"),
          snapshot_data.get("tokens_day"), snapshot_data.get("context_tokens"),
          snapshot_data.get("max_output_tokens"), int(snapshot_data.get("free", False)),
          snapshot_data.get("starts_at"), snapshot_data.get("expires_at"),
          observation_id, json.dumps(snapshot_data)))
    return True


def insert_event(conn, event_id, offer_id=None, model_id=None, provider_id=None,
                 event_type=None, status="active", fact_basis="observed",
                 discount_fraction=None, usage_multiplier=None,
                 previous_value=None, current_value=None,
                 title=None, summary=None,
                 first_seen_at=None, last_seen_at=None,
                 starts_at=None, expires_at=None, confidence=1.0,
                 observation_id=None, metadata=None):
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    conn.execute("""
        INSERT OR IGNORE INTO promotion_events (event_id, offer_id, model_id, provider_id,
            event_type, status, fact_basis, discount_fraction, usage_multiplier,
            previous_value, current_value, title, summary, first_seen_at, last_seen_at,
            starts_at, expires_at, confidence, source_observation_id, corroboration_count,
            metadata_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
    """, (event_id, offer_id, model_id, provider_id, event_type, status, fact_basis,
          discount_fraction, usage_multiplier, previous_value, current_value,
          title, summary, first_seen_at or now, last_seen_at or now,
          starts_at, expires_at, confidence, observation_id, json.dumps(metadata or {})))


def json_patch(existing: str, patch: str) -> str:
    """Merge two JSON strings, patch wins."""
    try:
        base = json.loads(existing) if existing else {}
    except (json.JSONDecodeError, TypeError):
        base = {}
    try:
        p = json.loads(patch) if patch else {}
    except (json.JSONDecodeError, TypeError):
        p = {}
    base.update(p)
    return json.dumps(base)
