"""app/duckdb_test.py — Quick DuckDB performance test.

Tests DuckDB vs SQLite for analytical queries on a subset of data.
"""
from __future__ import annotations

import time
import sqlite3
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
SQLITE_DB = ROOT / "data" / "llmdeals.sqlite3"
DUCKDB_DB = ROOT / "data" / "llmdeals_test.duckdb"


def test_performance():
    """Test DuckDB vs SQLite performance for analytical queries."""
    print("=== DuckDB vs SQLite Performance Test ===\n")
    
    # Connect to SQLite
    sqlite_conn = sqlite3.connect(str(SQLITE_DB))
    offers_count = sqlite_conn.execute("SELECT COUNT(*) FROM offers").fetchone()[0]
    print(f"SQLite database: {offers_count} offers")
    
    # Create DuckDB with sample data
    duckdb_conn = duckdb.connect(str(DUCKDB_DB))
    
    # Create table
    duckdb_conn.execute("DROP TABLE IF EXISTS offers")
    duckdb_conn.execute("""
        CREATE TABLE offers (
            offer_id VARCHAR PRIMARY KEY,
            provider_id VARCHAR,
            model_id VARCHAR,
            offer_type VARCHAR,
            input_per_m DOUBLE,
            output_per_m DOUBLE,
            free BOOLEAN,
            context_tokens INTEGER,
            lifecycle_state VARCHAR
        )
    """)
    
    # Migrate sample data (first 1000 offers)
    print("Migrating sample data (1000 offers)...")
    start = time.time()
    rows = sqlite_conn.execute("""
        SELECT offer_id, provider_id, model_id, offer_type, 
               input_per_m, output_per_m, free, context_tokens, lifecycle_state
        FROM offers LIMIT 1000
    """).fetchall()
    duckdb_conn.executemany("INSERT INTO offers VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", rows)
    migrate_time = time.time() - start
    print(f"Migration time: {migrate_time*1000:.2f}ms\n")
    
    # Test queries
    queries = [
        ("Provider aggregation", """
            SELECT provider_id, 
                   COUNT(*) as model_count,
                   AVG(input_per_m) as avg_price,
                   MIN(input_per_m) as cheapest
            FROM offers 
            GROUP BY provider_id
            HAVING model_count > 5
            ORDER BY cheapest
        """),
        ("Free models by context", """
            SELECT provider_id, model_id, context_tokens
            FROM offers 
            WHERE free = true AND context_tokens IS NOT NULL
            ORDER BY context_tokens DESC
            LIMIT 10
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
        ("Complex JOIN simulation", """
            SELECT 
                p.provider_id,
                p.model_count,
                p.avg_price,
                f.free_count
            FROM (
                SELECT provider_id, 
                       COUNT(*) as model_count,
                       AVG(input_per_m) as avg_price
                FROM offers 
                GROUP BY provider_id
            ) p
            LEFT JOIN (
                SELECT provider_id, 
                       COUNT(*) as free_count
                FROM offers 
                WHERE free = true
                GROUP BY provider_id
            ) f ON p.provider_id = f.provider_id
            ORDER BY p.avg_price
        """),
    ]
    
    # Test DuckDB
    print("DuckDB Performance:")
    for name, query in queries:
        start = time.time()
        result = duckdb_conn.execute(query).fetchall()
        elapsed = time.time() - start
        print(f"  {name}: {len(result)} rows in {elapsed*1000:.2f}ms")
    
    # Test SQLite
    print("\nSQLite Performance:")
    for name, query in queries:
        start = time.time()
        result = sqlite_conn.execute(query).fetchall()
        elapsed = time.time() - start
        print(f"  {name}: {len(result)} rows in {elapsed*1000:.2f}ms")
    
    # Cleanup
    duckdb_conn.close()
    sqlite_conn.close()
    
    # Remove test database
    DUCKDB_DB.unlink(missing_ok=True)
    print("\nTest complete! DuckDB test database removed.")


if __name__ == "__main__":
    test_performance()