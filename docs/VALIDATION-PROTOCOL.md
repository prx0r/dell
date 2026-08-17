# Hermes Validation Protocol

**How to validate LLM Deals data quality using invariant tests.**

## Purpose

Instead of trusting that "endpoints return 200", run invariant tests that verify the
data actually means what it claims. These tests catch the bugs the peer review found.

## Running Tests

```bash
cd /root/ass-rape-spunk-porn
python3 -m app.invariant_tests
```

## The Invariants

### INV-01: UNKNOWN_PRICE_NEVER_EQUALS_FREE
```python
# Free offers must have price_known=True (free IS a known price $0)
# Non-free offers with null price must have price_known=False
for offer in all_offers:
    if offer["free"] and not offer.get("price_known"):
        FAIL("Free offer without price_known=True")
    if not offer["free"] and offer.get("input_per_m") is None and offer.get("price_known"):
        FAIL("Non-free offer with null price marked as price_known")
```

### INV-02: FALLBACK_DATA_CANNOT_ENTER_CANONICAL_STATE
```python
# Adapters must not contain hardcoded model lists or fallback values
for source_file in glob("app/sources/*.py"):
    content = source_file.read()
    if "known_models" in content or "hardcoded" in content:
        FAIL(f"Adapter {source_file.name} contains fabrication")
```

### INV-03: MCP_AND_REST_RETURN_IDENTICAL_DOMAIN_RESULT
```python
# MCP tool_runner.py reads from same snapshots as REST API
# Both must produce identical results for the same query
mcp_result = run_mcp_tool("get_free_models", {"limit": 5})
rest_result = call_api("/v1/deals/free?limit=5")
assert set(m["model_id"] for m in mcp_result["free_models"]) == \
       set(d["model_id"] for d in rest_result["deals"])
```

### INV-04: EXTRACTOR_FAILURE_PRODUCES_NO_FACTS
```python
# If fetch fails, adapter must return empty list
for source_id, adapter in all_adapters():
    obs = Observation(status=None, text="FETCH_ERROR: test")
    result = adapter.extract(obs)
    assert result == [], f"{source_id} produced facts from failed fetch"
```

### INV-05: FAILED_FETCH_DOES_NOT_EXPIRE_DEAL
```python
# Parser errors should not mark deals as expired
# source_health tracks failures separately from deal status
health = source_health.get_health()
for source_id, info in health.items():
    if info["consecutive_failures"] > 0:
        # Source is degraded, but deals should still be in their last known state
        assert info["status"] != "expired"  # degraded != expired
```

### INV-06: DATE_ONLY_EXPIRY_NEVER_BECOMES_EXACT_TIMESTAMP
```python
# If expiry is a date without time, precision must be "day", not "minute"
for offer in all_offers:
    expiry = offer.get("expiry", {})
    if expiry.get("date") and not expiry.get("instant"):
        assert expiry.get("precision") == "day"
```

### INV-07: FREE_FALSE_FREE_TRUE_IS_FREE_STARTED
```python
# If an offer was not free and becomes free, that's free_started
# If it was free and becomes not free, that's free_ended
# Never invert the logic
assert free_to_not_free == "free_ended"
assert not_free_to_free == "free_started"
```

### INV-08: REPLAY_SAME_OBSERVATIONS_SAME_STATE
```python
# Running discovery twice with same data should produce same canonical state
state1 = run_discovery(fixtures="test_data/")
state2 = run_discovery(fixtures="test_data/")
assert state1 == state2
```

### INV-09: EVERY_CLAIM_HAS_EVIDENCE
```python
# Every deal in the API must have a source URL
for deal in api_response["deals"]:
    assert deal.get("metadata", {}).get("source_url"), \
        f"Deal {deal['model_id']} has no source URL"
```

### INV-10: PROVIDER_PAGE_DISAPPEARANCE != DEAL_EXPIRED
```python
# If a source returns 404 or empty, existing deals should NOT be marked expired
# They should be marked as "stale_suspected" until re-verified
```

## How Hermes Uses These

1. **Before any commit**: Run invariant tests
2. **During cron job**: Run invariant tests after each poll
3. **On kanban card completion**: Run invariant tests for affected sources
4. **In skill verification**: Goal-mode cards include invariant test as acceptance criteria

### Example Kanban Card
```
Title: POLL: OpenCode Go
Body: Poll OpenCode Go and verify INV-01, INV-02, INV-03 pass
Skill: deal-scout
Goal: All invariants pass for OpenCode Go data
```

### Example Goal-Mode Card
```
hermes kanban create "VALIDATE: Full invariant test suite" \
  --body "Run all 10 invariants. If any FAIL, create a fix card." \
  --goal --goal-max-turns 10
```
