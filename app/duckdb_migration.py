"""app/duckdb_migration.py — Migrate SQLite to DuckDB for analytical queries.

This module provides:
1. Schema migration from SQLite to DuckDB
2. Data migration with batch inserts
3. Performance comparison tests
4. Hybrid query engine (SQLite for writes, DuckDB for reads)
"""
from __future__ import annotations

import json
import time
import sqlite3
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
SQLITE_DB = ROOT / "data" / "llmdeals.sqlite3"
DUCKDB_DB = ROOT / "data" / "llmdeals.duckdb"


def connect_duckdb(db_path: Path | None = None) -> duckdb.DuckDBPyConnection:
    """Connect to DuckDB database."""
    path = str(db_path or DUCKDB_DB)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = duckdb.connect(path)
    return conn


def migrate_schema(duckdb_conn: duckdb.DuckDBPyConnection):
    """Create DuckDB schema from SQLite schema."""
    
    # Create offers table (main analytical table)
    duckdb_conn.execute("""
        CREATE TABLE IF NOT EXISTS offers (
            offer_id VARCHAR PRIMARY KEY,
            provider_id VARCHAR,
            model_id VARCHAR,
            offer_type VARCHAR,
            input_per_m DOUBLE,
            output_per_m DOUBLE,
            cache_read_per_m DOUBLE,
            cache_write_per_m DOUBLE,
            free BOOLEAN,
            requests_per_day INTEGER,
            requests_per_5h INTEGER,
            requests_per_minute INTEGER,
            tokens_per_day INTEGER,
            quota_scope VARCHAR,
            quota_window_hours DOUBLE,
            subscription_usd DOUBLE,
            credits_included DOUBLE,
            usage_multiplier DOUBLE,
            capacity_multiplier DOUBLE,
            context_tokens INTEGER,
            max_output_tokens INTEGER,
            region VARCHAR,
            automation_allowed BOOLEAN,
            requires_card BOOLEAN,
            requires_phone BOOLEAN,
            requires_kyc BOOLEAN,
            starts_at TIMESTAMP,
            expires_at TIMESTAMP,
            expiry_precision VARCHAR,
            deal_type VARCHAR,
            deal_status VARCHAR,
            source_url VARCHAR,
            metadata_json VARCHAR,
            created_at TIMESTAMP,
            updated_at TIMESTAMP,
            -- Oracle columns
            first_seen_at TIMESTAMP,
            last_verified_at TIMESTAMP,
            next_check_at TIMESTAMP,
            discovered_by VARCHAR,
            value_state VARCHAR,
            lifecycle_state VARCHAR,
            last_source_success_at TIMESTAMP,
            stale_reason VARCHAR,
            valid_from TIMESTAMP,
            valid_until TIMESTAMP,
            superseded_at TIMESTAMP
        )
    """)
    
    # Create sources table
    duckdb_conn.execute("""
        CREATE TABLE IF NOT EXISTS sources (
            source_id VARCHAR PRIMARY KEY,
            adapter_module VARCHAR,
            cadence_minutes INTEGER,
            priority INTEGER,
            enabled BOOLEAN,
            last_fetch_at DOUBLE,
            consecutive_failures INTEGER,
            created_at TIMESTAMP
        )
    """)
    
    # Create source_observations table
    duckdb_conn.execute("""
        CREATE TABLE IF NOT EXISTS source_observations (
            id INTEGER PRIMARY KEY,
            source_id VARCHAR,
            url VARCHAR,
            status INTEGER,
            sha256 VARCHAR,
            model_count INTEGER,
            fetched_at TIMESTAMP
        )
    """)
    
    # Create claims table
    duckdb_conn.execute("""
        CREATE TABLE IF NOT EXISTS claims (
            id INTEGER PRIMARY KEY,
            offer_id VARCHAR,
            claim_type VARCHAR,
            claim_value VARCHAR,
            confidence DOUBLE,
            source_url VARCHAR,
            observation_id INTEGER,
            created_at TIMESTAMP
        )
    """)
    
    # Create evidence table
    duckdb_conn.execute("""
        CREATE TABLE IF NOT EXISTS evidence (
            id INTEGER PRIMARY KEY,
            claim_id INTEGER,
            source_url VARCHAR,
            excerpt TEXT,
            content_hash VARCHAR,
            created_at TIMESTAMP
        )
    """)
    
    # Create verification_checks table
    duckdb_conn.execute("""
        CREATE TABLE IF NOT EXISTS verification_checks (
            id INTEGER PRIMARY KEY,
            offer_id VARCHAR,
            check_type VARCHAR,
            status VARCHAR,
            confidence DOUBLE,
            created_at TIMESTAMP
        )
    """)
    
    # Create indexes for analytical queries
    duckdb_conn.execute("CREATE INDEX IF NOT EXISTS idx_offers_provider ON offers(provider_id)")
    duckdb_conn.execute("CREATE INDEX IF NOT EXISTS idx_offers_model ON offers(model_id)")
    duckdb_conn.execute("CREATE INDEX IF NOT EXISTS idx_offers_free ON offers(free)")
    duckdb_conn.execute("CREATE INDEX IF NOT EXISTS idx_offers_price ON offers(input_per_m)")
    duckdb_conn.execute("CREATE INDEX IF NOT EXISTS idx_offers_lifecycle ON offers(lifecycle_state)")
    duckdb_conn.execute("CREATE INDEX IF NOT EXISTS idx_claims_offer ON claims(offer_id)")
    duckdb_conn.execute("CREATE INDEX IF NOT EXISTS idx_claims_type ON claims(claim_type)")


def migrate_data():
    """Migrate data from SQLite to DuckDB."""
    sqlite_conn = sqlite3.connect(str(SQLITE_DB))
    duckdb_conn = connect_duckdb()
    
    # Migrate offers
    print("Migrating offers...")
    offers = sqlite_conn.execute("SELECT * FROM offers").fetchall()
    # PRAGMA table_info returns (cid, name, type, notnull, dflt_value, pk)
    columns = [desc[1] for desc in sqlite_conn.execute("PRAGMA table_info(offers)").fetchall()]
    
    if offers:
        # Convert to list of dicts for easier insertion
        offer_dicts = []
        for row in offers:
            offer_dict = dict(zip(columns, row))
            # Convert None values to appropriate defaults
            for k, v in offer_dict.items():
                if v is None:
                    offer_dict[k] = None
            offer_dicts.append(offer_dict)
        
        # Batch insert
        duckdb_conn.executemany("""
            INSERT OR REPLACE INTO offers (
                offer_id, provider_id, model_id, offer_type,
                input_per_m, output_per_m, cache_read_per_m, cache_write_per_m,
                free, requests_per_day, requests_per_5h, requests_per_minute,
                tokens_per_day, quota_scope, quota_window_hours,
                subscription_usd, credits_included, usage_multiplier, capacity_multiplier,
                context_tokens, max_output_tokens,
                region, automation_allowed, requires_card, requires_phone, requires_kyc,
                starts_at, expires_at, expiry_precision,
                deal_type, deal_status,
                source_url, metadata_json, created_at, updated_at,
                first_seen_at, last_verified_at, next_check_at,
                discovered_by, value_state, lifecycle_state,
                last_source_success_at, stale_reason,
                valid_from, valid_until, superseded_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [(
            o['offer_id'], o['provider_id'], o['model_id'], o['offer_type'],
            o['input_per_m'], o['output_per_m'], o['cache_read_per_m'], o['cache_write_per_m'],
            o['free'], o['requests_per_day'], o['requests_per_5h'], o['requests_per_minute'],
            o['tokens_per_day'], o['quota_scope'], o['quota_window_hours'],
            o['subscription_usd'], o['credits_included'], o['usage_multiplier'], o['capacity_multiplier'],
            o['context_tokens'], o['max_output_tokens'],
            o['region'], o['automation_allowed'], o['requires_card'], o['requires_phone'], o['requires_kyc'],
            o['starts_at'], o['expires_at'], o['expiry_precision'],
            o['deal_type'], o['deal_status'],
            o['source_url'], o['metadata_json'], o['created_at'], o['updated_at'],
            o.get('first_seen_at'), o.get('last_verified_at'), o.get('next_check_at'),
            o.get('discovered_by'), o.get('value_state'), o.get('lifecycle_state'),
            o.get('last_source_success_at'), o.get('stale_reason'),
            o.get('valid_from'), o.get('valid_until'), o.get('superseded_at')
        ) for o in offer_dicts])
        print(f"Migrated {len(offer_dicts)} offers")
    
    # Migrate sources
    print("Migrating sources...")
    sources = sqlite_conn.execute("SELECT * FROM sources").fetchall()
    source_columns = [desc[1] for desc in sqlite_conn.execute("PRAGMA table_info(sources)").fetchall()]
    if sources:
        source_dicts = [dict(zip(source_columns, row)) for row in sources]
        duckdb_conn.executemany("""
            INSERT OR REPLACE INTO sources (
                source_id, adapter_module, cadence_minutes, priority, enabled,
                last_fetch_at, consecutive_failures, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, [(
            s['source_id'], s['adapter_module'], s['cadence_minutes'], s['priority'], s['enabled'],
            s['last_fetch_at'], s['consecutive_failures'], s['created_at']
        ) for s in source_dicts])
        print(f"Migrated {len(source_dicts)} sources")
    
    # Migrate claims
    print("Migrating claims...")
    claims = sqlite_conn.execute("SELECT * FROM claims").fetchall()
    claim_columns = [desc[1] for desc in sqlite_conn.execute("PRAGMA table_info(claims)").fetchall()]
    if claims:
        claim_dicts = [dict(zip(claim_columns, row)) for row in claims]
        duckdb_conn.executemany("""
            INSERT OR REPLACE INTO claims (
                id, offer_id, claim_type, claim_value, confidence,
                source_url, observation_id, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, [(
            c['id'], c['offer_id'], c['claim_type'], c['claim_value'], c['confidence'],
            c['source_url'], c['observation_id'], c['created_at']
        ) for c in claim_dicts])
        print(f"Migrated {len(claim_dicts)} claims")
    
    sqlite_conn.close()
    duckdb_conn.close()
    print("Migration complete!")


def test_performance():
    """Test DuckDB vs SQLite performance for analytical queries."""
    print("\n=== Performance Test ===")
    
    # Test analytical queries
    queries = [
        ("Provider aggregation", """
            SELECT provider_id, 
                   COUNT(*) as model_count,
                   AVG(input_per_m) as avg_price,
                   MIN(input_per_m) as cheapest
            FROM offers 
            WHERE lifecycle_state = 'ACTIVE_UNVERIFIED'
            GROUP BY provider_id
            HAVING model_count > 10
            ORDER BY cheapest
        """),
        ("Free models by context", """
            SELECT provider_id, model_id, context_tokens
            FROM offers 
            WHERE free = true AND context_tokens IS NOT NULL
            ORDER BY context_tokens DESC
            LIMIT 20
        """),
        ("Price distribution", """
            SELECT 
                CASE 
                    WHEN input_per_m = 0 THEN 'Free'
                    WHEN input_per_m < 1 THEN 'Under $1/M'
                    WHEN input_per_m < 10 THEN '$1-10/M'
                    WHEN input_per_m < 100 THEN '$10-100/M'
                    ELSE 'Over $100/M'
                END as price_bucket,
                COUNT(*) as count
            FROM offers
            GROUP BY price_bucket
            ORDER BY MIN(input_per_m)
        """),
    ]
    
    # Test DuckDB
    print("\nDuckDB Performance:")
    duckdb_conn = connect_duckdb()
    for name, query in queries:
        start = time.time()
        result = duckdb_conn.execute(query).fetchall()
        elapsed = time.time() - start
        print(f"  {name}: {len(result)} rows in {elapsed*1000:.2f}ms")
    
    # Test SQLite
    print("\nSQLite Performance:")
    sqlite_conn = sqlite3.connect(str(SQLITE_DB))
    for name, query in queries:
        start = time.time()
        result = sqlite_conn.execute(query).fetchall()
        elapsed = time.time() - start
        print(f"  {name}: {len(result)} rows in {elapsed*1000:.2f}ms")
    
    duckdb_conn.close()
    sqlite_conn.close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="DuckDB Migration Tool")
    parser.add_argument("--migrate", action="store_true", help="Migrate data from SQLite to DuckDB")
    parser.add_argument("--test", action="store_true", help="Run performance tests")
    args = parser.parse_args()
    
    if args.migrate:
        migrate_schema(connect_duckdb())
        migrate_data()
    
    if args.test:
        test_performance()
    
    if not args.migrate and not args.test:
        print("Usage: python3 -m app.duckdb_migration --migrate --test")