# Final Validation Matrix

## A. Decision semantics

RES-001 max_total_cost rejects over-budget route
RES-002 output price included in cost
RES-003 missing output price => cost UNKNOWN
RES-004 tools UNKNOWN excluded when required
RES-005 context unknown excluded under hard policy
RES-006 per-request context does not become daily quota
RES-007 quota windows never conflated
RES-008 expired promo excluded
RES-009 stale price excluded under stale=exclude
RES-010 conflicted price excluded under conflicted=exclude
RES-011 region constraint enforced
RES-012 automation constraint enforced
RES-013 no-card/no-phone/no-KYC enforced
RES-014 endpoint unavailable excludes route
RES-015 alternatives all satisfy every hard constraint
RES-016 no cheaper eligible route omitted for cost objective
RES-017 decision evidence coverage is actual evidence coverage
RES-018 exclusion reason codes deterministic
RES-019 task profile changes ranking
RES-020 unknown never silently becomes default fact

## B. Badge semantics

BADGE-001 free only from explicit economic state
BADGE-002 promo only while active
BADGE-003 throughput uses TPS only
BADGE-004 low latency uses TTFT only
BADGE-005 reliable endpoint uses endpoint measurements
BADGE-006 tool capable from capability fact
BADGE-007 tool proven requires measured success
BADGE-008 long context != long-context proven
BADGE-009 frontier is cohort-relative/versioned
BADGE-010 workhorse route-level
BADGE-011 high-value workload-specific
BADGE-012 every badge returns basis/evidence

## C. REST/MCP parity

PAR-001 resolve same route
PAR-002 search same candidates
PAR-003 unknown price handling identical
PAR-004 stale handling identical
PAR-005 evidence IDs identical
PAR-006 provider setup identical
PAR-007 error codes semantically identical
PAR-008 pagination/deterministic order parity

## D. External agent tasks

Use an agent with no DB/repo access.

1. cheapest sufficient coding route, tools required, 64k context
2. exact free plan for 500 requests
3. no-card route
4. no-KYC route
5. all provider routes for specific model
6. explain why chosen
7. retrieve price proof
8. identify stale facts affecting a decision
9. identify conflicted price
10. find fallback after endpoint outage
11. current promo with expiry
12. route under exact dollar ceiling
13. high-throughput route
14. low-latency route
15. tool-proven route
16. compare free-quota vs zero-marginal-price
17. calculate cost for asymmetric input/output workload
18. detect unknown quota rather than inventing capacity
19. ask "what changed today?"
20. produce a complete machine-readable inference plan

Zero tolerance:
- hard constraint violation
- unsupported factual claim
- stale-as-current
- unknown-as-known
- quota-window conflation
- identity false merge
- expired deal resurrection
- evidence mismatch
- REST/MCP semantic mismatch

## E. Mutation tests

Mutations that must be killed:

1. unknown price -> zero
2. swap input/output prices
3. tools UNKNOWN -> TRUE
4. ignore output cost
5. remove stale filtering
6. merge quota windows
7. region ignored
8. requires_card ignored
9. endpoint outage ignored
10. source health substituted for endpoint reliability
11. context window treated as quota
12. evidence-policy bypass
13. expired promo active
14. model and endpoint IDs merged
15. MCP uses independent scorer
16. REST uses independent scorer
17. badge input structure mismatch
18. capability receives free-price bonus
19. conflict state coerced to known
20. negative price accepted

Target:
critical mutation kill = 100%
overall mutation kill >= 95%
