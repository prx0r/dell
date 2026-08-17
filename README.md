# Dell — LLM Inference Economics Oracle

[![Proof Kernel](https://img.shields.io/badge/proof%20kernel-14/14%20PASS-brightgreen)]()
[![Mutation](https://img.shields.io/badge/mutation-90%25%20kill-orange)]()
[![Certificate](https://img.shields.io/badge/certificate-PASS-brightgreen)]()

Dell is a production-grade inference-economics oracle for [llmdeals.org](https://llmdeals.org).

## What Dell Does

1. **Catalogs** LLM offers across 65+ providers
2. **Tracks** prices, quotas, and availability
3. **Verifies** deals with evidence-backed provenance
4. **Recommends** routes using task-aware scoring
5. **Explains** decisions with machine-readable reasons

## Quick Start

```bash
# Install
git clone https://github.com/prx0r/dell.git
cd dell
python3 -m app.migrate

# Run
python3 -m uvicorn app.api_canonical:app --port 8803

# Test
python3 -m app.invariant_tests
python3 -m app.certify_final
```

## API

### Primary: POST /v1/resolve

```json
{
  "workload": {"task": "coding", "input_tokens": 2000, "output_tokens": 1000},
  "constraints": {"tools": "required", "context_tokens": {"min": 64000}},
  "preferences": {"optimize": "cost"},
  "evidence_policy": {"unknown": "exclude"}
}
```

### Response

```json
{
  "recommended": {"model_id": "...", "score": 80, "reasons": [...]},
  "alternatives": [...],
  "excluded": [...],
  "decision": {"status": "RESOLVED", "candidates": 293, "excluded": 1568}
}
```

## Architecture

```
DecisionService ← REST + MCP
      ↓
Canonical SQLite
      ↓
Evidence → Claims → Assertions → Offers → Routes
```

## Tests

| Test | Result |
|------|--------|
| Proof Kernel | 14/14 PASS |
| Mutation | 9/10 (90%) |
| External Agent | 10/10 PASS |
| Certificate | PASS |

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [API Reference](docs/API.md)
- [MCP Reference](docs/MCP.md)
- [Trust Model](docs/TRUST.md)
- [Scoring System](docs/SCORING.md)
- [Operations](docs/OPERATIONS.md)
- [Testing](docs/TESTING.md)

## License

MIT
