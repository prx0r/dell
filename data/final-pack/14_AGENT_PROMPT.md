# FINAL AGENT PROMPT — COPY THIS INTO HERMES/CODING AGENT

You are finishing `prx0r/dell`.

Your objective is NOT to add features. Your objective is to make the existing product semantically correct, internally converged, externally useful, reproducible and release-ready.

Read every file in this final pack before editing.

Repository baseline reviewed: `e9ca0fe11052aa6422999fd848c936ef7d9a838a`.

## Governing rules

1. Preserve Dell's permanent truth architecture: stable identities, observations/artifacts, claims/assertions, evidence, temporal semantics and projections.
2. MODEL != ENDPOINT != OFFER.
3. Unknown is never a convenient default.
4. Hard requirements are applied before ranking.
5. Context window is per request, never quota.
6. Quota windows remain dimensionally distinct.
7. Source collection health != inference endpoint reliability.
8. REST and MCP are adapters over the exact same services.
9. Every public decision label has a machine-auditable definition and basis.
10. Every claim of PASS must be falsifiable.
11. Do not alter tests merely to make failing behavior pass unless the test contract is demonstrably wrong and the report explains why.
12. No hard-coded certification successes.

## First action

Run and record the current baseline. Inspect:
- `app/resolve.py`
- `app/scoring_v2.py`
- `app/mcp_canonical.py`
- `app/api_canonical.py`
- free workload planner
- freshness/verification
- proof kernel
- mutation suite
- current MCP entrypoint(s)
- README / AGENTS / MANIFEST

Confirm or refute each issue in `01_EXECUTIVE_PEER_REVIEW.md` with code evidence.

## Build sequence

Follow `13_IMPLEMENTATION_ORDER.md` exactly.

## Required output

Create:
- `data/reports/DELL-FINAL-HARDENING.md`
- `data/tests/final/<run-id>/...`
- `app/certify_final.py`
- final generated `MANIFEST.json`
- updated canonical README/AGENTS docs

Final report must state:

1. Git SHA before
2. Git SHA after
3. exact commands
4. each peer-review issue: CONFIRMED / REFUTED / FIXED
5. decision test results
6. badge test results
7. REST tests
8. MCP tests
9. parity tests
10. mutation results
11. external-agent results
12. field-level coverage
13. endpoint measurement coverage
14. documentation clean-room test
15. operational/live test status
16. all remaining limitations
17. whether Dell can honestly call itself:
   - production-ready data layer
   - production-ready decision API
   - verified live oracle
18. final GO / NO-GO

If anything critical fails, final status is NO-GO.

Goal: truth, not PASS.
