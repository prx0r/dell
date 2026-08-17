# Testing

## Test Suites

| Suite | Command | Result |
|-------|---------|--------|
| Proof Kernel | python3 -m app.invariant_tests | 14/14 PASS |
| Mutation | python3 -m app.mutation_tests | 10/10 (100%) |
| External Agent | python3 -m app.external_agent_tests | 10/10 PASS |
| Final Certificate | python3 -m app.certify_final | PASS |

## Test Categories

- Structural (DB, schema, imports)
- Truth (proof kernel, integrity)
- Decision (constraints, cost)
- Scoring (no priors, coverage)
- Mutation (kill rate)
