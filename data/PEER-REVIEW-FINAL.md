# Final Release Defects Review

**Date:** 2026-08-18
**Verdict:** Almost done, but not frozen yet

## Critical Defects

### 1. Certifier: 90% mutation kill = PASS (should be 100%)
The certifier accepts 9/10 = 90% as PASS when requirement is 100%.

### 2. Schema gate imports checker without executing
Import check is structural, not functional.

### 3. DecisionService issues
- max_total_cost_usd checked before calculating workload cost
- Unknown output price coerced to zero
- endpoints not used in candidate building
- confidence = evidence_coverage
- unknown reliability/throughput get neutral 50
- context length treated as quality

### 4. scoring_v3.py confidence = coverage
Both count populated dimensions.

## Required Fixes

1. Fix mutation kill to 100%
2. Fix schema gate to actually execute
3. Fix DecisionService:
   - Calculate cost BEFORE checking budget
   - Never coerce unknown to zero
   - Build endpoint-level candidates
   - Separate confidence from coverage
   - Remove neutral 50 for unknown
   - Don't treat context as quality
4. Fix scoring_v3.py confidence calculation
