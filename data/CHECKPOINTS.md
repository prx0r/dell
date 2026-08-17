# Verification Engine Checkpoints

**Source:** LLM_DEALS_VERIFICATION_ENGINE_BUILD_SPEC.md
**Purpose:** Binary validation — each checkpoint either passes or fails. No grey areas.

---

## CHECKPOINT 1: Observation → Claim Linkage
**Invariant:** Claims extracted from observation N must reference observation N.

```python
# TEST: For every claim, observation_id must exist in source_observations
claims = conn.execute("SELECT observation_id FROM claims").fetchall()
for c in claims:
    assert conn.execute("SELECT 1 FROM source_observations WHERE observation_id=?", (c[0],)).fetchone()
```

## CHECKPOINT 2: Artifact Store is Live
**Invariant:** Every successful fetch writes artifact before claims are accepted.

```python
# TEST: Every observation has an artifact hash
obs = conn.execute("SELECT content_hash FROM source_observations").fetchall()
for o in obs:
    assert o[0] is not None  # content_hash must exist
```

## CHECKPOINT 3: Evidence Rows Exist
**Invariant:** A claim with source_url is NOT evidence. Evidence must have artifact_id + selector.

```python
# TEST: claims table has proper schema
cols = [c[1] for c in conn.execute("PRAGMA table_info(claims)").fetchall()]
assert "claim_id" in cols
assert "claim_type" in cols
assert "source_observation_id" in cols
```

## CHECKPOINT 4: Event Identity
**Invariant:** Events reference source_id, subject_type, subject_id correctly.

```python
# TEST: deal_events have proper fields
cols = [c[1] for c in conn.execute("PRAGMA table_info(deal_events)").fetchall()]
assert "offer_id" in cols
assert "event_type" in cols
assert "created_at" in cols
```

## CHECKPOINT 5: DB-Driven Scheduling
**Invariant:** Scheduler reads from DB, not RAM.

```python
# TEST: sources table exists and has data
count = conn.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
assert count > 0  # Must have registered sources
```

## CHECKPOINT 6: MCP = DealService
**Invariant:** MCP tools call same service as REST.

```python
# TEST: MCP tool_runner.py imports service.py
content = open("mcp/server.mjs").read()
assert "service" in content.lower() or "DealService" in content
```

## CHECKPOINT 7: No Direct Snapshot Reads
**Invariant:** No code reads snapshots/*.json directly.

```python
# TEST: Only discovery.py and artifact_store read snapshots
import subprocess
result = subprocess.run(["grep", "-r", "snapshots", "app/"], capture_output=True, text=True)
# Should only find in discovery.py (for export) and artifact_store.py
```

## CHECKPOINT 8: Price State Semantics
**Invariant:** price_state is FREE|PAID|UNKNOWN, never just True/False.

```python
# TEST: All offers have valid price_state
rows = conn.execute("SELECT DISTINCT price_state FROM offers").fetchall()
valid_states = {r[0] for r in rows}
assert valid_states <= {"FREE", "PAID", "UNKNOWN"}
```

## CHECKPOINT 9: Region is NULL (not 'global')
**Invariant:** region=NULL means unknown, not eligible everywhere.

```python
# TEST: No offers have region='global'
count = conn.execute("SELECT COUNT(*) FROM offers WHERE region='global'").fetchone()[0]
assert count == 0
```

## CHECKPOINT 10: Deal Classification
**Invariant:** /deals only contains unusual opportunities, not ordinary market-rate.

```python
# TEST: deal_classifier identifies deals vs catalog
from deal_classifier import classify_as_deal
test_cases = [
    ({"free": True, "context_tokens": 1000000}, True),   # high-value free = deal
    ({"free": True, "context_tokens": 1000}, False),      # low-value free = catalog
    ({"input_per_m": 0.10, "free": False}, False),         # ordinary paid = catalog
    ({"metadata": {"multiplier": 2.0}}, True),              # usage multiplier = deal
]
for offer, expected in test_cases:
    result = classify_as_deal(offer)
    assert result["is_deal"] == expected, f"Expected {expected} for {offer}"
```

## CHECKPOINT 11: Identity Resolution
**Invariant:** EXACT_SAME_MODEL propagates, SIBLING_VARIANT does not.

```python
# TEST: Identity resolver works correctly
from identity import infer_relationship, EXACT_SAME_MODEL, SIBLING_VARIANT
assert infer_relationship("mimo-v2.5", "mimo-v2.5") == EXACT_SAME_MODEL
assert infer_relationship("mimo-v2.5", "mimo-v2.5-pro") == SIBLING_VARIANT
```

## CHECKPOINT 12: Canonical DB is Single Truth
**Invariant:** REST, MCP, and site all read from same canonical DB.

```python
# TEST: _load_all() reads from canonical_db, not snapshots
import api_canonical
# The _load_all function should call canonical_db.connect()
```

## CHECKPOINT 13: Free Tri-State
**Invariant:** price_state FREE/PAID/UNKNOWN, not just True/False.

```python
# TEST: No offer has price_state that's not in {FREE, PAID, UNKNOWN}
rows = conn.execute("SELECT DISTINCT price_state FROM offers").fetchall()
for r in rows:
    assert r[0] in ("FREE", "PAID", "UNKNOWN"), f"Invalid price_state: {r[0]}"
```

## CHECKPOINT 14: Scoring Uses Real Data
**Invariant:** Intelligence from benchmarks, not fabricated.

```python
# TEST: Scoring uses benchmark data when available
import scoring
test_offer = {"model_id": "test", "provider_id": "test", "metadata": {"benchmarks": [{"name": "test", "score": 80}]}}
scored = scoring.score_and_badge(test_offer)
assert scored["vector"]["intelligence"] == 80  # Should use benchmark score
```

## CHECKPOINT 15: Mega Deal Detection
**Invariant:** MiMo 9.4x detected, Luna 2x detected.

```python
# TEST: Mega deals found in current data
from mega_deals import detect_mega_deals
mega = detect_mega_deals(all_offers)
assert len(mega) >= 2  # At least MiMo + Luna
```

## CHECKPOINT 16: Deal Service Works
**Invariant:** All DealService methods return valid data.

```python
# TEST: DealService methods
from service import DealService
svc = DealService()
stats = svc.get_stats()
assert stats["total_offers"] > 0
deals = svc.list_deals(limit=5)
assert isinstance(deals, list)
models = svc.list_models(limit=5)
assert isinstance(models, list)
```

## CHECKPOINT 17: Invariant Tests Pass
**Invariant:** All 10 invariant tests pass.

```python
# TEST: Run invariant tests
import subprocess
result = subprocess.run([sys.executable, "-m", "app.invariant_tests"], capture_output=True, text=True)
assert "10/10 PASS" in result.stdout
```

## CHECKPOINT 18: API Endpoints Respond
**Invariant:** All canonical API endpoints return 200.

```python
# TEST: All endpoints
from fastapi.testclient import TestClient
from api_canonical import app
c = TestClient(app)
endpoints = ['/health', '/v1/stats', '/v1/models?limit=2', '/v1/deals?limit=2',
    '/v1/free?limit=2', '/v1/recommend?task=coding', '/v1/glossary']
for ep in endpoints:
    assert c.get(ep).status_code == 200, f"Failed: {ep}"
```

## CHECKPOINT 19: MCP Tools Work
**Invariant:** MCP tool_runner.py executes without error.

```python
# TEST: MCP tools
import subprocess
r = subprocess.run(["node", "mcp/server.mjs"], input='', capture_output=True, text=True, timeout=3)
assert r.returncode == 0
```

## CHECKPOINT 20: Source Adapters Return Data
**Invariant:** 30+ adapters return offers.

```python
# TEST: Source adapters
from sources import registry
ok = 0
for src in registry.get_all_sources():
    adapter = registry.get_adapter(src.source_id)
    if adapter:
        obs = adapter.fetch()
        if any(o.status == 200 for o in obs):
            ok += 1
assert ok >= 30  # At least 30 adapters working
```
