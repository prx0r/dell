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

from offer_id import OfferId

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


# Lifecycle/oracle columns added to `offers` after the initial subset schema.
_OFFERS_ORACLE_COLUMNS = [
    "first_seen_at TEXT",
    "last_verified_at TEXT",
    "next_check_at TEXT",
    "discovered_by TEXT",
    "value_state TEXT DEFAULT 'UNKNOWN'",
    "lifecycle_state TEXT DEFAULT 'ACTIVE_UNVERIFIED'",
    "last_source_success_at TEXT",
    "stale_reason TEXT",
    "valid_from TEXT",
    "valid_until TEXT",
    "superseded_at TEXT",
]


def migrate(conn: sqlite3.Connection):
    """Apply schema (idempotent). Creates missing tables/indexes and adds any
    `offers` columns introduced after the initial subset schema, so existing
    databases are upgraded in place without losing data."""
    schema_path = ROOT / "app" / "schema_canonical.sql"
    if schema_path.exists():
        conn.executescript(schema_path.read_text())

    existing = {r["name"] for r in conn.execute("PRAGMA table_info(offers)").fetchall()}
    for col_def in _OFFERS_ORACLE_COLUMNS:
        col = col_def.split()[0]
        if col not in existing:
            conn.execute("ALTER TABLE offers ADD COLUMN %s" % col_def)
            existing.add(col)

    _seed_oracle_data(conn)


def _seed_oracle_data(conn: sqlite3.Connection):
    """Idempotently seed the oracle lookup tables (freshness policies + source
    authority) that migration 0007 inserts, so databases built from
    schema_canonical.sql are functionally equivalent to migrated ones."""
    if conn.execute("SELECT COUNT(*) FROM freshness_policies").fetchone()[0] == 0:
        now = "datetime('now')"
        conn.executescript("""
            INSERT INTO freshness_policies (claim_type, source_type, ttl_seconds, description, created_at)
            VALUES
                ('model_author', 'official_api', 31536000, 'permanent', datetime('now')),
                ('context_window', 'official_api', 2592000, 'weeks/months', datetime('now')),
                ('list_price', 'official_api', 86400, 'hours/day', datetime('now')),
                ('flash_promo', 'official_api', 3600, 'minutes/hours', datetime('now')),
                ('availability', 'official_api', 300, 'minutes', datetime('now')),
                ('throughput', 'official_api', 60, 'seconds/minutes', datetime('now')),
                ('rate_limit', 'official_api', 86400, 'hours/day', datetime('now')),
                ('endpoint_reachable', 'probe', 60, 'seconds/minutes', datetime('now')),
                ('list_price', 'aggregator', 43200, 'hours (aggregator less fresh)', datetime('now')),
                ('availability', 'aggregator', 600, 'minutes (aggregator less fresh)', datetime('now'));
        """)

    if conn.execute("SELECT COUNT(*) FROM source_authority").fetchone()[0] == 0:
        conn.executescript("""
            INSERT INTO source_authority (source_id, claim_type, authority_level, confidence, notes, created_at)
            VALUES
                ('openrouter', 'price', 'primary', 0.95, 'OpenRouter API is authoritative for OpenRouter prices', datetime('now')),
                ('openrouter', 'availability', 'primary', 0.9, 'OpenRouter API is authoritative for endpoint availability', datetime('now')),
                ('openrouter', 'checkpoint', 'secondary', 0.7, 'OpenRouter reports but not authoritative for checkpoint details', datetime('now')),
                ('artificial_analysis', 'speed', 'primary', 0.85, 'AA measures actual speed', datetime('now')),
                ('artificial_analysis', 'quality', 'secondary', 0.7, 'AA benchmarks but not definitive', datetime('now')),
                ('models_dev', 'context_window', 'primary', 0.9, 'models.dev tracks context windows', datetime('now'));
        """)
    conn.commit()


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
    """Generate stable offer_id — use OfferId.create() instead."""
    return OfferId.create(provider_id, model_id, offer_type, region)


def upsert_offer(conn, offer_id: str, provider_id: str, model_id: str = None,
                 offer_type: str = "metered_api", input_per_m: float = None,
                 output_per_m: float = None, free: bool = False,
                 context_tokens: int = None, requests_per_day: int = None,
                 source_url: str = None, region: str = None,
                 # Rich fields
                 cache_read_per_m: float = None, cache_write_per_m: float = None,
                 requests_per_5h: int = None, requests_per_minute: int = None,
                 tokens_per_day: int = None, quota_scope: str = None,
                 quota_window_hours: float = None, subscription_usd: float = None,
                 credits_included: float = None, usage_multiplier: float = None,
                 capacity_multiplier: float = None, max_output_tokens: int = None,
                 automation_allowed: int = None, requires_card: int = None,
                 requires_phone: int = None, requires_kyc: int = None,
                 starts_at: str = None, expires_at: str = None,
                 expiry_precision: str = None, deal_type: str = None,
                 deal_status: str = "active", metadata_json: str = "{}"):
    """Insert or update an offer. Preserves ALL adapter data."""
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    conn.execute("""
        INSERT INTO offers (offer_id, provider_id, model_id, offer_type,
            input_per_m, output_per_m, cache_read_per_m, cache_write_per_m,
            free, requests_per_day, requests_per_5h, requests_per_minute,
            tokens_per_day, quota_scope, quota_window_hours,
            subscription_usd, credits_included, usage_multiplier, capacity_multiplier,
            context_tokens, max_output_tokens,
            region, automation_allowed, requires_card, requires_phone, requires_kyc,
            starts_at, expires_at, expiry_precision,
            deal_type, deal_status,
            source_url, metadata_json, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(offer_id) DO UPDATE SET
            input_per_m = COALESCE(excluded.input_per_m, input_per_m),
            output_per_m = COALESCE(excluded.output_per_m, output_per_m),
            cache_read_per_m = COALESCE(excluded.cache_read_per_m, cache_read_per_m),
            cache_write_per_m = COALESCE(excluded.cache_write_per_m, cache_write_per_m),
            free = excluded.free,
            requests_per_day = COALESCE(excluded.requests_per_day, requests_per_day),
            requests_per_5h = COALESCE(excluded.requests_per_5h, requests_per_5h),
            requests_per_minute = COALESCE(excluded.requests_per_minute, requests_per_minute),
            tokens_per_day = COALESCE(excluded.tokens_per_day, tokens_per_day),
            quota_scope = COALESCE(excluded.quota_scope, quota_scope),
            quota_window_hours = COALESCE(excluded.quota_window_hours, quota_window_hours),
            subscription_usd = COALESCE(excluded.subscription_usd, subscription_usd),
            credits_included = COALESCE(excluded.credits_included, credits_included),
            usage_multiplier = COALESCE(excluded.usage_multiplier, usage_multiplier),
            capacity_multiplier = COALESCE(excluded.capacity_multiplier, capacity_multiplier),
            context_tokens = COALESCE(excluded.context_tokens, context_tokens),
            max_output_tokens = COALESCE(excluded.max_output_tokens, max_output_tokens),
            region = COALESCE(excluded.region, region),
            automation_allowed = COALESCE(excluded.automation_allowed, automation_allowed),
            requires_card = COALESCE(excluded.requires_card, requires_card),
            requires_phone = COALESCE(excluded.requires_phone, requires_phone),
            requires_kyc = COALESCE(excluded.requires_kyc, requires_kyc),
            starts_at = COALESCE(excluded.starts_at, starts_at),
            expires_at = COALESCE(excluded.expires_at, expires_at),
            expiry_precision = COALESCE(excluded.expiry_precision, expiry_precision),
            deal_type = COALESCE(excluded.deal_type, deal_type),
            deal_status = excluded.deal_status,
            source_url = COALESCE(excluded.source_url, source_url),
            metadata_json = excluded.metadata_json,
            updated_at = excluded.updated_at
    """, (offer_id, provider_id, model_id, offer_type,
          input_per_m, output_per_m, cache_read_per_m, cache_write_per_m,
          int(free), requests_per_day, requests_per_5h, requests_per_minute,
          tokens_per_day, quota_scope, quota_window_hours,
          subscription_usd, credits_included, usage_multiplier, capacity_multiplier,
          context_tokens, max_output_tokens,
          region, automation_allowed, requires_card, requires_phone, requires_kyc,
          starts_at, expires_at, expiry_precision,
          deal_type, deal_status,
          source_url, metadata_json, now, now))


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
