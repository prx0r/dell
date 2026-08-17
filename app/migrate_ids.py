#!/usr/bin/env python3
"""app/migrate_ids.py — Migrate old-format offer_ids to new format.

This fixes the ID bug where claims/events had old-format offer_ids.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

import canonical_db
from offer_id import OfferId


def migrate_claim_ids(conn):
    """Migrate claims with old-format offer_ids to new format."""
    claims = conn.execute("SELECT claim_id, offer_id FROM claims").fetchall()
    
    migrated = 0
    for claim in claims:
        old_id = claim["offer_id"]
        
        # Check if already valid
        if OfferId.validate(old_id):
            continue
        
        # Try to parse old format: provider:model_id:offer_kind (3 parts)
        parts = old_id.split(":")
        if len(parts) == 3:
            provider_id = parts[0]
            model_id = parts[1]
            offer_type = parts[2]
            
            # Create new ID with default region
            new_id = OfferId.create(provider_id, model_id, offer_type, "global")
            
            # Update claim
            conn.execute("UPDATE claims SET offer_id = ? WHERE claim_id = ?",
                        (new_id, claim["claim_id"]))
            migrated += 1
        elif len(parts) == 2:
            # Just model_id (e.g., "qwen/qwen3.8-27b") - can't reconstruct
            # These are orphan claims, remove them
            conn.execute("DELETE FROM claims WHERE claim_id = ?", (claim["claim_id"],))
            migrated += 1
    
    conn.commit()
    return migrated


def main():
    print("Migrating old-format offer_ids...")
    
    conn = canonical_db.connect()
    canonical_db.migrate(conn)
    
    claims_migrated = migrate_claim_ids(conn)
    
    conn.close()
    
    print("Migrated %d claims" % claims_migrated)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
