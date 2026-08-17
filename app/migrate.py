#!/usr/bin/env python3
"""app/migrate.py — Run migrations from app/migrations/

Usage:
    DELL_DB=/tmp/dell.sqlite3 python3 -m app.migrate
"""
import sys
import os
import hashlib
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS_DIR = ROOT / "app" / "migrations"
DB_PATH = os.environ.get("DELL_DB", str(ROOT / "data" / "llmdeals.sqlite3"))


def get_db():
    """Connect to database."""
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    return conn


def ensure_migration_table(conn):
    """Create schema_migrations table if not exists."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            filename TEXT NOT NULL,
            sha256 TEXT NOT NULL,
            applied_at TEXT NOT NULL
        )
    """)
    conn.commit()


def get_applied(conn):
    """Get set of applied migration versions."""
    rows = conn.execute("SELECT version FROM schema_migrations").fetchall()
    return set(r[0] for r in rows)


def compute_sha256(filepath):
    """Compute SHA256 of a file."""
    return hashlib.sha256(filepath.read_bytes()).hexdigest()


def run_migrations():
    """Run all pending migrations."""
    conn = get_db()
    ensure_migration_table(conn)
    
    applied = get_applied(conn)
    
    # Get all migration files
    migrations = sorted(MIGRATIONS_DIR.glob("*.sql"))
    
    print("DELL MIGRATION RUNNER")
    print("=" * 60)
    print("database=%s" % DB_PATH)
    print("migrations_found=%d" % len(migrations))
    print("migrations_applied=%d" % len(applied))
    print()
    
    run = 0
    for m in migrations:
        # Extract version from filename (e.g., 0001_core.sql -> 1)
        version = int(m.stem.split("_")[0])
        
        if version in applied:
            print("SKIP %s (already applied)" % m.name)
            continue
        
        sha256 = compute_sha256(m)
        
        print("RUN  %s (sha256=%s...)" % (m.name, sha256[:16]))
        
        try:
            sql = m.read_text()
            conn.executescript(sql)
            
            # Record migration
            from datetime import datetime
            conn.execute("""
                INSERT INTO schema_migrations (version, filename, sha256, applied_at)
                VALUES (?, ?, ?, ?)
            """, (version, m.name, sha256, datetime.utcnow().isoformat()))
            conn.commit()
            
            run += 1
            print("     OK")
        except Exception as e:
            print("     FAILED: %s" % e)
            conn.close()
            return 1
    
    conn.close()
    
    print()
    print("migrations_run=%d" % run)
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(run_migrations())
