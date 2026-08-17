# Dell External Oracle Utility Audit

**Date:** 2026-08-18
**Git SHA:** cf061cd
**Auditor:** Autonomous Agent

---

## Executive Verdict

Dell has made substantial progress from schema theatre to actual utility. The system now:
- Has 60.7% assertion coverage
- Has 33.2% evidence coverage
- Has 33.3% verification coverage
- Passes 90% of mutation tests
- Passes 10/10 external agent tests
- Passes 12/12 REST contract tests

**However**, the system still has significant gaps:
- Only 33% of offers have full provenance
- No real performance measurements
- No live probe data
- Limited activation recipes
- No external agent baseline comparison

---

## Test Results

### REST Contract Tests (12/12 PASS)
All endpoints return valid JSON with correct status codes.

### External Agent Tests (10/10 PASS)
An external agent can use Dell to:
- Find cheapest coding models
- Plan free workloads
- Verify promoted deals
- Find all routes for a model
- Find no-card/no-KYC offers
- Find under $0.20/M routes
- Get price proofs
- Check model identity
- Identify stale claims
- Find fallback routes

### Mutation Tests (9/10 PASS, 90% kill rate)
The system catches:
- Stale filtering bypass
- Quota window confusion
- Source authority inversion
- Identity merging
- Unknown coercion
- Region ignoring
- Expired promo resurrection
- Negative prices
- Economic misclassification

---

## Coverage Honesty

| Metric | Count | Percentage |
|--------|-------|------------|
| Total offers | 1861 | 100% |
| Economic classified | 1861 | 100% |
| With assertions | 1130 | 60.7% |
| With claims | 617 | 33.2% |
| With evidence | 617 | 33.2% |
| With verification | 619 | 33.3% |
| With freshness | 617 | 33.2% |

**Key insight:** We have breadth but lack depth. Only 33% of offers have full provenance.

---

## What Dell Can Do Today

1. **Catalog 1861 offers** across 65 providers
2. **Classify economic access** for all offers
3. **Track 3019 price observations**
4. **Model 79 serving endpoints**
5. **Provide freshness checking** for provenanced offers
6. **Answer 10/10 user questions** correctly
7. **Catch 90% of mutations** in critical logic

---

## What Dell Cannot Do Today

1. **Deep provenance for 67% of offers** — only 33% have full evidence chain
2. **Real performance measurements** — no live probe data
3. **Comprehensive activation recipes** — only 10 recipes
4. **Real-time conflict resolution** — reconciliation table exists but unused
5. **External agent baseline comparison** — not yet implemented
6. **MCP black-box tests** — not yet implemented

---

## Recommendation

**Dell is ready for limited production use** as a data layer for llmdeals.org, but should NOT be marketed as a "verified oracle" until:

1. Provenance coverage reaches 80%+
2. Live probe data exists
3. External agent baseline comparison shows clear value
4. MCP parity is verified

---

## Machine-Readable Artifacts

```
data/tests/utility/utility-20260817-201901/run.json
data/tests/utility/utility-20260817-202110/run.json
data/certificates/dell-production-30a7a672.json
```
