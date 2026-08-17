# Hermes Skills and Autonomous Maintenance

Split consumer and maintainer authority.

## Consumer skills

### `dell-query`
Read-only search/list/details.
No DB access.

### `dell-resolve`
Transforms a workload into a typed `/resolve` call.
Must not invent missing constraints.

### `dell-explain`
Follows decision → route → fields → assertions → claims → evidence.

### `dell-plan-free`
Calls exact quota-aware planner.
Returns UNKNOWN when quota cannot be established.

## Maintainer skills

### `dell-discover`
Finds candidate sources/offers.
May create candidates, not canonical truth.

### `dell-investigate`
Fetches source artifacts and emits observations.

### `dell-reconcile`
Applies authority/identity rules to conflicting claims.

### `dell-verify`
Runs claim/endpoint verification.

### `dell-gap`
Ranks UNKNOWN/STALE critical fields by expected user value.

### `dell-source-repair`
Diagnoses source/parser degradation. Must never convert ingestion failure into market absence.

### `dell-certify`
Read-only grader. Executes clean-room, invariant, mutation, REST, MCP, parity, utility and operational gates.

## Required SKILL contract

Each skill must declare:

- mission
- accepted inputs
- outputs/schema
- filesystem permissions
- network permissions
- database read/write permissions
- allowed canonical mutations
- termination condition
- failure states
- evidence produced
- exact verification command

## Autonomous loop

```text
gap analysis
  ↓
highest-value stale/unknown fact
  ↓
investigation task
  ↓
observation
  ↓
reconciliation
  ↓
verification
  ↓
projection update
  ↓
certification sample
```

Do not optimize the autonomous loop for number of rows changed.

Optimize:
`verified critical-field coverage gained / unit cost`.
