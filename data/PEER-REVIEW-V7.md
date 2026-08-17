# Peer Review V7 — External Reality Test

**Date:** 2026-08-18
**Verdict:** Architecture good, certification is theatre, need external proof of value

## Core Issue

> "The current production certificate is not sufficient. Evidence that the product is useful and correct under realistic external use."

## Test Families

### A. UX-01..UX-20 — Realistic user decisions
### B. AG-01..AG-15 — Blind external agent tasks
### C. BASELINE — agent-only vs web-search vs Dell
### D. LIE-01..LIE-25 — Synthetic scenarios to make Dell lie
### E. MUT-* — Genuine source-code mutation testing
### F. REST-* — Actual HTTP/OpenAPI contract tests
### G. MCP-* — MCP black-box + REST parity tests
### H. COVERAGE-* — Honest evidence/verification/performance coverage
### I. CUSTOMER-* — Top 25 real customer questions

## Critical No-Tolerance Invariants

- stale claim served as current = 0
- hard constraint violations = 0
- unsupported factual claims = 0
- quota-window conflations = 0
- known identity false merges = 0
- expired deals resurrected = 0
- evidence hash mismatches = 0
- REST/MCP semantic disagreements = 0

## What's Currently Fake

| Test | Problem |
|------|---------|
| mutation detection | Hardcoded PASS |
| backup/restore | Hardcoded PASS |
| load/soak | Hardcoded PASS |
| unit tests | One OfferId construction |
| fixture adapters | Counts files, doesn't run |
| API contracts | Counts routes, not semantics |
| RT-02 | Unconditional PASS |
| RT-16 | triggers >= 0 (always true) |
| RT-27 | Reports stale, passes anyway |

## What to Build

```
D13 — EXTERNAL ORACLE UTILITY / NO-HIDING CERTIFICATION

app/certify_utility.py
tests/utility/
tests/blackbox/
tests/mutations/
tests/external_agent/
tests/customer_questions/

data/reports/DELL-EXTERNAL-UTILITY-AUDIT.md
```

## Expected Output

```
DELL EXTERNAL ORACLE UTILITY CERTIFICATION

BLACK-BOX REST: 41/41 PASS
BLACK-BOX MCP: 9/9 PASS, 30/30 parity
USER QUESTIONS: 21/25 supported
EXTERNAL AGENT: 93.3% completion
BASELINE: agent=54.2%, web=78.6%, Dell=93.3%
MUTATION: 93.6% kill rate
```

## The Real Question

> Would an external coding agent benefit from installing this MCP/API today?

Answer with measured results, not hope.

## What Dell Can Do Today (honest)

- 1,714 models cataloged
- 3,019 price observations
- 79 serving endpoints
- 30 fully provenanced claims
- Real-time freshness checking
- Multi-dimensional verification

## What Dell Cannot Do Today (honest)

- Deep provenance for most offers
- Real performance measurements
- Comprehensive activation recipes
- Real-time conflict resolution
- External-agent validated usefulness
