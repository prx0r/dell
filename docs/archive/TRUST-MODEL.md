# Trust Model — What "Verified" Means

## What This System Proves

LLM Deals is a **data layer** for LLM inference economics. It provides:
- Canonical, append-only records of deals and offers
- Cryptographic proof of data provenance
- Verification levels based on actual checks

## What "Verified" Means

### Verification Levels (from actual checks)

| Level | Meaning | What's Required |
|-------|---------|-----------------|
| LEAD | Unverified lead | Nothing required |
| SOURCE_FETCHED | Source page fetched | Observation stored |
| CLAIM_EXTRACTED | At least 1 claim extracted | Claim + observation |
| PRIMARY_EVIDENCE | 1 primary evidence source | Evidence record |
| PRIMARY_CORROBORATED | Primary + corroboration | 2+ evidence records |
| ENDPOINT_REACHABLE | API endpoint reachable | Reachability check |
| MODEL_LISTED | Model confirmed listed | Model listing check |
| INFERENCE_SUCCEEDED | Inference canary passed | Inference check |
| DEAL_CONDITION_CONFIRMED | Deal condition tested | Deal test |

### What Each Level Does NOT Prove

- **SOURCE_FETCHED** does not mean the deal is real
- **PRIMARY_EVIDENCE** does not mean the deal is active
- **ENDPOINT_REACHABLE** does not mean the deal is live
- **DEAL_CONDITION_CONFIRMED** does not mean the deal will last

### What Requires Human Verification

- Deals with no expiry date
- Deals with "limited time" terms
- Deals from new/unknown providers
- Deals that seem too good to be true

## Cryptographic Proof

### What We Store

1. **Content-addressed artifacts**: Raw source data stored by SHA-256 hash
2. **Append-only events**: Every change recorded with timestamps
3. **Hash chains**: Tool events linked cryptographically
4. **Merkle roots**: Run roots binding all evidence

### What We Sign

- Verification runs are sealed with cryptographic proof
- Run roots include: events, artifacts, claims, evidence
- After sealing, no child artifacts can be modified

### What We Don't Sign

- Individual offers (no per-offer signing)
- Source observations (no per-observation signing)
- Real-time data (no streaming signatures)

## Release Gates

### For Internal Use
- Proof Kernel Gates: 14/14 must pass
- Every claim must link to a valid offer
- Every verification level must come from actual checks

### For External Advertising
- Must have at least 1 DEAL_CONDITION_CONFIRMED
- Must have cryptographically sealed verification run
- Must have evidence records with artifacts

## Known Limitations

1. **Partial expiry tracking**: Expiry dates not yet populated for most offers
2. **Partial verification**: 33% of offers have full provenance
3. **No live verification**: Most deals are not actively checked
4. **No human verification**: All checks are automated
5. **No streaming**: Data is batch-updated, not real-time

## What We Don't Claim

- We don't claim deals are "guaranteed"
- We don't claim prices are "locked in"
- We don't claim availability is "certain"
- We don't claim we've "verified everything"

We provide **evidence-based confidence levels**, not guarantees.
