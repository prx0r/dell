"""app/generate_website_data.py — Generate website data from database.

Creates JSON files for the website frontend from the canonical database.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

import canonical_db
SNAPSHOTS_DIR = ROOT / "snapshots"


def generate_website_data():
    """Generate website data from database."""
    conn = canonical_db.connect()
    canonical_db.migrate(conn)
    
    # Create snapshots directory
    SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Get all offers
    offers = conn.execute("""
        SELECT * FROM offers 
        WHERE lifecycle_state != 'SUPERSEDED'
        ORDER BY created_at DESC
    """).fetchall()
    
    print(f"Generating website data for {len(offers)} offers...")
    
    # Group by provider
    provider_offers = {}
    for offer in offers:
        provider_id = offer['provider_id']
        if provider_id not in provider_offers:
            provider_offers[provider_id] = []
        provider_offers[provider_id].append(dict(offer))
    
    # Export by provider
    for provider_id, offers_list in provider_offers.items():
        snapshot = {
            "offers": offers_list,
            "exported_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "count": len(offers_list)
        }
        path = SNAPSHOTS_DIR / f"{provider_id}.json"
        with open(path, "w") as f:
            json.dump(snapshot, f, indent=2, default=str)
    
    # Generate summary statistics
    stats = {
        "total_offers": len(offers),
        "free_offers": len([o for o in offers if o['free']]),
        "providers": len(provider_offers),
        "mega_deals": len([o for o in offers if (o['usage_multiplier'] or 0) >= 2]),
        "exported_at": time.strftime("%Y-%m-%dT%H:%M:%SZ")
    }
    
    # Save stats
    stats_path = ROOT / "MANIFEST.json"
    manifest = {
        "version": "2.0.0",
        "stats": stats,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ")
    }
    with open(stats_path, "w") as f:
        json.dump(manifest, f, indent=2)
    
    print(f"Generated {len(provider_offers)} provider snapshots")
    print(f"Stats: {stats}")
    
    conn.close()
    return stats


if __name__ == "__main__":
    generate_website_data()