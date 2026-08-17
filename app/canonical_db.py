"""app/canonical_db.py — SQLite canonical truth for LLM Deals.

One database owns all truth:
  Source → Observation → Claim → Offer → DealEvent → Verification → Projection

JSON snapshots become exports, not truth.
"""
from __future__ import annotations

import json
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "llmdeals.sqlite3"


def connect(db_path: str | Path | None = None) -> sqlite3.Connection:
    path = str(db_path or DB_PATH)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    return conn


def migrate(conn: sqlite3.Connection):
    """Apply schema."""
    schema_path = ROOT / "app" / "schema_canonical.sql"
    if schema_path.exists():
        conn.executescript(schema_path.read_text())


@contextmanager
def transaction(conn: sqlite3.Connection):
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def generate_offer_id(provider_id: str, model_id: str, offer_type: str,
                      region: str = "global") -> str:
    """Generate stable offer_id: provider:model:offer_type:region"""
    model_clean = (model_id or "").lower().replace("/", ":")
    return "%s:%s:%s:%s" % (provider_id, model_clean, offer_type, region)


def upsert_offer(conn, offer_id: str, provider_id: str, model_id: str,
                 offer_type: str = "metered_api", input_per_m: float = None,
                 output_per_m: float = None, free: bool = False,
                 context_tokens: int = None, requests_per_day: int = None,
                 source_url: str = None, region: str = "global"):
    """Insert or update an offer."""
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    conn.execute("""
        INSERT INTO offers (offer_id, provider_id, model_id, offer_type,
            input_per_m, output_per_m, free, context_tokens, requests_per_day,
            source_url, region, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(offer_id) DO UPDATE SET
            input_per_m = COALESCE(excluded.input_per_m, input_per_m),
            output_per_m = COALESCE(excluded.output_per_m, output_per_m),
            free = excluded.free,
            context_tokens = COALESCE(excluded.context_tokens, context_tokens),
            requests_per_day = COALESCE(excluded.requests_per_day, requests_per_day),
            source_url = COALESCE(excluded.source_url, source_url),
            updated_at = excluded.updated_at
    """, (offer_id, provider_id, model_id, offer_type,
          input_per_m, output_per_m, int(free), context_tokens, requests_per_day,
          source_url, region, now, now))


def upsert_source(conn, source_id: str, adapter_module: str, cadence_minutes: int,
                  priority: int = 1, enabled: bool = True):
    """Insert or update source registry."""
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    conn.execute("""
        INSERT INTO sources (source_id, adapter_module, cadence_minutes, priority, enabled,
            last_fetch_at, consecutive_failures, created_at)
        VALUES (?, ?, ?, ?, ?, 0, 0, ?)
        ON CONFLICT(source_id) DO UPDATE SET
            adapter_module = excluded.adapter_module,
            cadence_minutes = excluded.cadence_minutes,
            priority = excluded.priority,
            enabled = excluded.enabled
    """, (source_id, adapter_module, cadence_minutes, priority, int(enabled), now))


def update_source_fetch(conn, source_id: str, success: bool):
    """Update source fetch timestamp and failure count."""
    now = time.time()
    if success:
        conn.execute("""
            UPDATE sources SET last_fetch_at = ?, consecutive_failures = 0,
                last_success_at = ? WHERE source_id = ?
        """, (now, now, source_id))
    else:
        conn.execute("""
            UPDATE sources SET last_fetch_at = ?, consecutive_failures = consecutive_failures + 1
            WHERE source_id = ?
        """, (now, source_id))


def get_source_schedule(conn) -> list[dict]:
    """Get sources that are due for polling."""
    now = time.time()
    rows = conn.execute("""
        SELECT source_id, adapter_module, cadence_minutes, priority, last_fetch_at
        FROM sources WHERE enabled = 1
        ORDER BY priority DESC, last_fetch_at ASC
    """).fetchall()
    due = []
    for row in rows:
        elapsed = now - (row["last_fetch_at"] or 0)
        if elapsed >= row["cadence_minutes"] * 60:
            due.append(dict(row))
    return due


def insert_observation(conn, source_id: str, url: str, status_code: int,
                       content_hash: str, model_count: int = 0):
    """Record a source observation."""
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    conn.execute("""
        INSERT INTO source_observations (source_id, url, fetched_at, http_status,
            content_hash, model_count)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (source_id, url, now, status_code, content_hash, model_count))
    return conn.execute("SELECT last_insert_rowid()").fetchone()[0]


def get_all_offers(conn) -> list[dict]:
    """Get all offers from canonical DB."""
    rows = conn.execute("SELECT * FROM offers ORDER BY provider_id, model_id").fetchall()
    return [dict(r) for r in rows]


def get_offer_count(conn) -> int:
    return conn.execute("SELECT COUNT(*) FROM offers").fetchone()[0]


def get_free_count(conn) -> int:
    return conn.execute("SELECT COUNT(*) FROM offers WHERE free = 1").fetchone()[0]


def get_provider_count(conn) -> int:
    return conn.execute("SELECT COUNT(DISTINCT provider_id) FROM offers").fetchone()[0]
