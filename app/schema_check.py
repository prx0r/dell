#!/usr/bin/env python3
"""app/schema_check.py — Verify database schema matches migrations.

Usage:
    DELL_DB=/tmp/dell.sqlite3 python3 -m app.schema_check
"""
import sys
import os
import hashlib
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS_DIR = ROOT / "app" / "migrations"
DB_PATH = os.environ.get("DELL_DB", str(ROOT / "data" / "llmdeals.sqlite3"))

# Expected tables from migrations
EXPECTED_TABLES = {
    'sources', 'source_observations', 'offers', 'deal_events', 'source_health',
    'claims', 'evidence', 'evidence_v2', 'verification_checks',
    'models', 'model_prices', 'model_providers', 'model_events',
    'serving_endpoints', 'quota_policies', 'performance_observations',
    'activation_recipes', 'verification_runs', 'tool_events', 'query_recipes',
    'offer_assertions', 'verification_dimensions',
    'freshness_policies', 'negative_observations', 'claim_reconciliation',
    'source_authority', 'economic_access', 'schema_migrations'
}


def get_db():
    """Connect to database."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    return conn


def check_schema():
    """Run all schema checks."""
    conn = get_db()
    
    print("DELL SCHEMA CHECK")
    print("=" * 60)
    print("database=%s" % DB_PATH)
    
    errors = []
    warnings = []
    
    # 1. Check migrations applied
    migrations = conn.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0]
    print("migrations_applied=%d" % migrations)
    
    # 2. Check tables
    actual_tables = set(r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall())
    
    missing_tables = EXPECTED_TABLES - actual_tables
    unexpected_tables = actual_tables - EXPECTED_TABLES - {'sqlite_sequence'}
    
    if missing_tables:
        errors.append("missing_tables=%d: %s" % (len(missing_tables), missing_tables))
    if unexpected_tables:
        warnings.append("unexpected_tables=%d: %s" % (len(unexpected_tables), unexpected_tables))
    
    print("tables_expected=%d" % len(EXPECTED_TABLES))
    print("tables_actual=%d" % len(actual_tables))
    print("missing_tables=%d" % len(missing_tables))
    print("unexpected_tables=%d" % len(unexpected_tables))
    
    # 3. Check indexes
    indexes = conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='index'").fetchone()[0]
    print("indexes=%d" % indexes)
    
    # 4. Check foreign keys
    fk_errors = conn.execute("PRAGMA foreign_key_check").fetchall()
    if fk_errors:
        errors.append("foreign_key_errors=%d" % len(fk_errors))
    print("foreign_key_errors=%d" % len(fk_errors))
    
    # 5. Check triggers
    triggers = conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='trigger'").fetchone()[0]
    print("triggers=%d" % triggers)
    
    # 6. Verify migration checksums
    migration_files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    checksum_errors = 0
    for m in migration_files:
        version = int(m.stem.split("_")[0])
        expected_sha = hashlib.sha256(m.read_bytes()).hexdigest()
        
        row = conn.execute(
            "SELECT sha256 FROM schema_migrations WHERE version = ?", (version,)
        ).fetchone()
        
        if row and row[0] != expected_sha:
            checksum_errors += 1
            errors.append("checksum mismatch for %s" % m.name)
    
    print("migration_checksum_errors=%d" % checksum_errors)
    
    # 7. Check freshness policies
    freshness_count = conn.execute("SELECT COUNT(*) FROM freshness_policies").fetchone()[0]
    print("freshness_policies=%d" % freshness_count)
    
    # 8. Check source authority
    authority_count = conn.execute("SELECT COUNT(*) FROM source_authority").fetchone()[0]
    print("source_authority_rules=%d" % authority_count)
    
    conn.close()
    
    # Summary
    print()
    print("=" * 60)
    if errors:
        print("RESULT: FAIL")
        print("ERRORS:")
        for e in errors:
            print("  - %s" % e)
        return 1
    else:
        print("RESULT: PASS")
        if warnings:
            print("WARNINGS:")
            for w in warnings:
                print("  - %s" % w)
        return 0


if __name__ == "__main__":
    sys.exit(check_schema())
