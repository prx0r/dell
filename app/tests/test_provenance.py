#!/usr/bin/env python3
"""Test provenance chain."""
import sys
sys.path.insert(0, 'app')

import canonical_db
from provenance import get_provenance_chain, verify_provenance_exists

conn = canonical_db.connect()
canonical_db.migrate(conn)

print("PROVENANCE CHAIN TEST")
print("=" * 60)

# Test with an offer that has claims
offer = conn.execute("""
    SELECT offer_id FROM claims LIMIT 1
""").fetchone()

if offer:
    offer_id = offer["offer_id"]
    print("\nTesting offer: %s" % offer_id)
    
    # Get provenance for a field
    chain = get_provenance_chain(conn, offer_id, "price_state")
    print("\nProvenance chain:")
    for k, v in chain.items():
        if isinstance(v, dict):
            print("  %s:" % k)
            for kk, vv in v.items():
                print("    %s: %s" % (kk, vv))
        else:
            print("  %s: %s" % (k, v))
else:
    print("No offers with claims found")

conn.close()
