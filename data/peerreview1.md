## Verdict

**As an exploratory prototype: 7/10. As the “rock-hard canonical LLM inference data layer” you want other agents to depend on: about 3.5/10 right now.**

The problem is not lack of features. The repo has **too many features before the truth layer is trustworthy**. It already has 38 adapters, five APIs, routing, scoring, MCP, expiry, Hermes orchestration and thousands of records, but several core mechanisms can silently manufacture or misclassify data. The repo's own peer-review brief recognizes some symptoms—zero-result adapters, broken expiry, unlinked multipliers—but substantially understates the architectural problems.

The highest-value move now is **stop adding providers and features for a bit and harden the observation → claim → canonical-state pipeline**.

## Critical findings

| Severity | Problem                                      | Consequence                              |
| -------- | -------------------------------------------- | ---------------------------------------- |
| **P0**   | Five APIs + multiple schemas                 | No canonical contract                    |
| **P0**   | Discovery does not write canonical SQLite DB | “Canonical DB” isn't actually canonical  |
| **P0**   | Adapters fabricate fallback facts            | Dataset can confidently lie              |
| **P0**   | Unknown prices become `$0`                   | False free/cheap results                 |
| **P0**   | Change detector is structurally broken       | Promotions won't reliably start/end      |
| **P0**   | MCP has code-injection surface               | Agent input can become Python source     |
| **P0**   | Raw evidence isn't durably preserved         | Historical claims cannot be reproduced   |
| **P1**   | Poll schedule/health only lives in RAM       | Cron scheduling doesn't work as designed |
| **P1**   | Expiry invents temporal precision            | False countdowns                         |
| **P1**   | Verification is heuristic theatre            | “Verified” does not mean verified        |
| **P1**   | Provider/T&C/setup info is static Python     | Will rot silently                        |
| **P1**   | Heuristic scores presented like measurements | Misleading workhorse/value rankings      |
| **P1**   | Tests are mainly smoke tests                 | Broken semantics still pass              |
| **P2**   | Git stores generated snapshots/events        | Noise, duplication, repo bloat           |
| **P2**   | Router work dominates core data work         | Scope drift                              |

---

# 1. You do not currently have one system

This is the biggest architectural defect.

The tree contains:

`api.py`
`api_v2.py`
`api_v3.py`
`api_hot.py`
`api_canonical.py`

plus two MCP implementations and old/new routing/data code.

Worse, `models_v2.py` literally says:

> `Model → ProviderOffering → CommercialOffer → DealEvent` is “THE schema”.

Yet `schema.sql` implements something else: it collapses the offering/commercial layers into `offers`, then has separate `offer_snapshots` and `promotion_events`.

Then `normalize.py` introduces **another canonical representation**: `canonical-models.json`.

That means there are effectively three truths:

```text
models_v2.py truth
SQLite truth
canonical-models.json / snapshots truth
```

This is fatal for a data-infrastructure product.

### Change

Make one domain package:

```text
llmdeals/
  domain/
    model.py
    provider.py
    offering.py
    plan.py
    deal.py
    claim.py
    evidence.py
    source.py
    activation.py
    terms.py
```

And make the database schema derive from that contract, or vice versa.

Then:

```text
one DB
   ↓
one query/service layer
   ↓
REST
MCP
website
exports
```

MCP should **call the same service methods** as REST.

No implementation is allowed to reread random JSON files and invent its own semantics.

---

# 2. `discovery.py` bypasses your supposedly canonical database

`db.py` says:

> “All writes go through this module.”

But the actual discovery pipeline imports `db` and then essentially doesn't use it. Instead it writes:

```text
snapshots/<source>.json
events/<source>_<timestamp>.json
```

directly to disk.

So the SQLite kernel is architectural decoration at the moment.

### Worse: raw observations disappear

The adapter's `Observation` actually contains the raw `text`.

But the database observation record stores essentially:

```text
URL
status
hash
etag
last-modified
```

without the complete fetched body.

This destroys one of the most important properties of your project:

> **Can I prove what OpenCode's page said on August 17, 2026?**

A SHA-256 digest proves integrity **only if you retained the bytes it hashed**.

### Change

Every fetch should create:

```text
SourceObservation
    observation_id
    source_id
    fetched_at
    http_status
    response_headers
    artifact_sha256
    artifact_uri
    normalized_sha256
```

Then raw artifacts go into content-addressed storage:

```text
artifacts/
  sha256/
    ab/
      abcd1234....html.gz
```

Later use R2/S3 if desired.

The database stores the pointer.

Now ten years later you can reconstruct:

```text
Provider page
↓
exact bytes
↓
extractor version
↓
claim
↓
deal state
```

That is **actual provenance**.

---

# 3. The adapters currently fabricate facts

This is the most serious data-quality issue.

`opencode.py` has a fallback where, if it doesn't successfully extract offers, it inserts a hardcoded list of “known models”.

It also sees a generic `2x usage` signal and, when it cannot identify the model, creates:

```text
opencode-go/2x-usage-promo
```

as though it were a model.

That's precisely backwards.

An unknown model association should produce:

```text
Claim:
  provider = OpenCode Go
  predicate = usage_multiplier
  value = 2
  model_scope = UNKNOWN
```

not a fake model identity.

SenseNova is worse in a subtler way. Its parser says, effectively:

```python
if couldn't extract call count:
    calls = 1500
```

and then hardcodes:

```text
automation_allowed = True
global_access = True
```

while converting a five-hour allowance into an estimated daily number.

Your database cannot distinguish those hardcoded assumptions from observed facts.

### Rule I would enforce

**Adapters are forbidden from providing fallback commercial facts.**

An adapter may return:

```text
OBSERVED
PARSED
UNKNOWN
```

It may never return:

```text
probably 1500
I remember this model exists
likely global
probably automation allowed
```

Those can become **candidate claims** with low confidence, but not canonical observations.

This should be a test invariant.

---

# 4. Unknown is being treated as zero

This bug exists repeatedly.

For example `/v1/deals` does effectively:

```python
in_m = o.get("input_per_m") or 0
```

when applying `max_price`.

So:

```text
price = UNKNOWN
```

becomes:

```text
price = $0
```

This is catastrophic for a cheapest-inference API.

The old `normalize.py` does the same pattern repeatedly, and models.dev records can become marked free when pricing is missing/zero-like.

### Enforce three-valued semantics

```text
0       = confirmed free
12.50   = known price
NULL    = unknown
```

Never:

```text
NULL → 0
```

Then APIs need:

```text
price_known: true
```

and:

```http
?max_price=1
```

automatically excludes unknown prices unless:

```http
?include_unknown_price=true
```

This single invariant should get dozens of regression tests.

---

# 5. Your change detector is literally broken

This one is concrete.

`source_diff.diff_snapshots()` explicitly accepts dictionaries.

But `discovery.py` sends it:

```python
prev["offers"]        # list
source_offers         # list
```

so the change detector rejects its input and returns nothing.

Even after fixing that, its vocabulary doesn't match your actual schema.

It looks for:

```text
free_tier
multiplier
promo_expiry
context_window
```

while the OfferSnapshot representation uses:

```text
free
usage_multiplier
expires_at
context_tokens
```

And there is a spectacular inversion in the free-tier transition logic:

```text
true → false = free_started
false → true = free_ended
```

which should obviously be the reverse.

### Replace it entirely

Don't diff anonymous lists.

Give every object stable identity:

```text
offering_id
commercial_offer_id
```

Then:

```text
previous[offer_id]
current[offer_id]
```

and compare normalized semantic state.

Example:

```text
OfferState V17
input = 0.20
output = 0.60
multiplier = 1

OfferState V18
input = 0.20
output = 0.60
multiplier = 2
```

generates:

```text
ClaimChanged
  field: usage_multiplier
  old: 1
  new: 2
```

Then a domain reducer determines whether that implies:

```text
DealActivated
DealModified
DealExpired
```

Don't have the low-level differ make business-level conclusions directly.

---

# 6. There is another subtle event corruption bug

`discovery.py` accumulates one global `all_events` list.

Then after processing a source it does essentially:

```python
_save_events(source_id, all_events[-len(source_offers):])
```

The number of offers has nothing to do with the number of extracted events.

That can associate events from earlier sources with the current source.

And if:

```python
len(source_offers) == 0
```

then Python:

```python
all_events[-0:]
```

means:

```python
all_events[0:]
```

which is **every event**.

So a source producing zero offers can potentially get a file containing unrelated events from the whole run.

This needs deletion, not patching.

Keep event generation scoped:

```text
observation
→ claims
→ source-local candidate changes
→ commit
```

No global mutable accumulation.

---

# 7. Your scheduler isn't actually persistent

The registry contains:

```python
last_fetch_at: float = 0
consecutive_failures: int = 0
```

inside an in-memory Python dataclass.

Every cron invocation starts a new process.

Therefore:

```text
process starts
last_fetch_at = 0
EVERY source appears due
```

Your nice 120/240/1440-minute cadences aren't durable.

The source health module has exactly the same problem: health history lives in a module-level dictionary.

You already have a `source_health` DB table that isn't actually being used for this.

### Replace source registry state with persistent records

```text
sources
source_schedule_state
source_fetch_runs
source_health_rollups
```

with:

```text
last_attempt_at
last_success_at
last_changed_at
next_check_at
etag
last_modified
consecutive_failures
parse_success_rate
expected_offer_count
last_offer_count
```

Then the scheduler just asks:

```sql
SELECT *
FROM sources
WHERE enabled = TRUE
AND next_check_at <= now()
ORDER BY priority DESC, next_check_at;
```

No in-memory scheduling state.

---

# 8. Don't poll every source every six hours

The current validation describes one six-hour cron.

But the internal registry simultaneously claims different frequencies.

Neither is the optimal architecture.

You want:

```text
scheduler tick: every 1–5 minutes
```

but it does **not poll all sources**.

It only executes sources whose persisted `next_check_at` has arrived.

Then dynamically compute next poll:

```text
hot promotion:          15 min
pricing API:            30 min
active changelog:       1 h
ordinary docs:          6 h
stable grant page:      24 h
unchanged 90 days:      3–7 days
known expiry nearby:    temporarily accelerate
```

That gives high freshness without hammering providers.

---

# 9. Source identity needs to be richer

Right now `SourceEntry` is basically:

```text
name
module
cadence
priority
enabled
```

That's nowhere near enough for your eventual global radar.

A source should know:

```text
authority_class
provider_id
language
country
region
URL(s)
fetch_method
content_type
robots_policy
expected_schema
adapter_version
parser_version
expected_frequency
known_time_zone
credential_requirement
community_or_primary
terms_relevance
price_relevance
promotion_relevance
```

Then your Scout can autonomously propose a `SourceCandidate`, but only the source registry can promote it to a monitored canonical source.

---

# 10. The expiry system has false precision

`expiry.py` calls itself “precise” and “hour-level”.

But when it sees:

```text
Ends December 31, 2026
```

it assigns midnight UTC.

The provider never said UTC.

It also treats “ends today” as approximately:

```text
now + 23h59m
```

which is simply wrong if parsed at noon.

This is exactly the mistake we discussed earlier.

### Your timestamp object needs:

```text
value
precision
timezone
boundary
source_expression
anchor
```

Examples:

```json
{
  "date": "2026-12-31",
  "precision": "day",
  "timezone": null,
  "boundary": "unknown"
}
```

versus:

```json
{
  "instant": "2026-12-31T23:59:00-08:00",
  "precision": "minute",
  "timezone": "America/Los_Angeles",
  "boundary": "inclusive"
}
```

Only the second one gets a seconds-level countdown.

Never convert uncertain dates into fake instants.

---

# 11. “Verification” currently does not mean verification

`verify_deal_is_live()` searches source text for the provider/model string and counts that as a confirmation. Two mentions can become `verified`.

That does not prove:

> “2× usage is currently active.”

It proves:

> “Two texts mentioned OpenCode.”

Similarly, the canonical API assigns verification confidence based partly on whether the URL contains strings like `openrouter.ai`, `models.dev`, or Alibaba's docs domain.

That is source-authority scoring, **not claim verification**.

### Introduce the missing object: `Claim`

```text
Claim:
  subject
  predicate
  object/value
  valid_time
  asserted_by
  extracted_from
```

For example:

```text
subject:
  commercial_offer: opencode-go/luna

predicate:
  usage_multiplier

value:
  2

evidence:
  observation: obs_7821
  selector: ...
  excerpt: ...
```

Then verification operates on **the claim**.

```text
primary official exact claim     = strong
second independent primary claim = corroboration
community report                 = lead/corroboration only
inference                         = explicitly marked inferred
```

Now “verified” means something.

---

# 12. Preserve evidence selectors, not merely excerpts

Your `promo_extract.py` returns things like:

```text
matched_text: "2x usage"
```

Better:

```text
observation_id
artifact_hash
DOM/CSS selector
JSON Pointer / XPath
byte_start
byte_end
raw excerpt
normalization version
extractor version
```

For APIs:

```text
Source:
https://...

Evidence:
pricing.cards[3].badge

Observed:
2026-08-17T...
```

That's the difference between “trust our parser” and a scientific audit trail.

---

# 13. Your model identity layer is dangerous

`normalize.py` still does:

```python
merged.update(data)
```

for each source.

So if provider A and provider B both describe the same model, later records can overwrite earlier records.

But **multiple providers for the same model are your entire product**.

Worse, models.dev enrichment uses substring-ish fuzzy matching between base names.

That is dangerous with families like:

```text
qwen-3
qwen-3.5
qwen-3-coder
qwen-3-coder-next
```

Do not resolve canonical identity with loose substring matching automatically.

### You need a proper identity graph

```text
CanonicalModel
ModelAlias
ProviderModelIdentifier
ModelVersion
ModelFamily
```

Resolver outputs:

```text
EXACT
EXPLICIT_ALIAS
HIGH_CONFIDENCE
AMBIGUOUS
UNRESOLVED
```

Only the first two should automatically merge without review.

---

# 14. Delete `canonical-models.json` as a source of truth

It can remain an **export**.

That distinction matters:

```text
DB truth
  ↓
canonical-models.json export
```

not:

```text
random ingestion modules
  ↓
canonical-models.json
  ↓
some APIs

other ingestion modules
  ↓
snapshots/
  ↓
other APIs

SQLite
  ↓
almost nothing
```

Right now you basically have the second architecture.

---

# 15. The provider metadata file is guaranteed to rot

`providers.py` contains pricing/free-tier prose, T&C highlights, rate limits, setup instructions, capabilities and subjective commentary directly in Python.

There are even contradictions inside individual records. For example OpenRouter has one free-request count in a field and a different number in explanatory notes.

It also contains statements like:

```text
"FASTEST"
"Best hub"
"unbeatable"
```

Those are editorial opinions inside canonical infrastructure.

### Replace it with evidence-backed records

```text
Provider
ProviderCapabilityClaim
ActivationRecipe
TermsSnapshot
QuotaRule
EligibilityRule
```

And version them.

The setup guide should be a projection:

```text
Provider
↓
current ActivationRecipe
↓
human-readable instructions
```

not handwritten Python strings that silently become stale.

---

# 16. Activation Recipes are still missing from the real architecture

This should become one of your most distinctive pieces of data.

Not merely:

```text
setup_difficulty = 2
```

but:

```text
steps:
  - OPEN_URL          HUMAN
  - CREATE_ACCOUNT    HUMAN
  - ACCEPT_TERMS      HUMAN
  - CREATE_API_KEY    HUMAN
  - STORE_SECRET      USER/AGENT
  - CONFIGURE_CLIENT  AGENT
  - TEST_ENDPOINT     AGENT
```

Plus:

```text
requires_card
requires_phone
requires_KYC
requires_local_billing
requires_subscription
legal_consent_required
automatable_fraction
```

That is hugely more useful downstream.

A Hermes agent can then query:

> “Give me free deals with at most one manual setup step.”

That is a real differentiator.

---

# 17. T&C need snapshots, not bullet points

Likewise:

```text
TermsSnapshot
TermsClaim
```

with evidence.

Important predicates:

```text
automation_allowed
commercial_use_allowed
production_use_allowed
resale_allowed
account_sharing_allowed
API_use_allowed
scraping_allowed
geographic_restriction
rate_limit_policy
credit_expiry
```

And every one should allow:

```text
TRUE
FALSE
UNKNOWN
CONDITIONAL
```

**Never default legal/commercial fields to true.**

Unfortunately `ProviderOffering` currently defaults:

```python
automation_allowed = True
production_allowed = True
regions = ["global"]
openai_compatible = True
```

Those defaults should become unknown.

This is an important schema principle:

> **Absence of evidence must never increase eligibility.**

---

# 18. The scoring engine should be demoted immediately

This is one of the weakest parts.

`scoring.py` currently gives unknown intelligence a baseline of 50, then raises intelligence because a **provider** supports reasoning or tools.

Reliability begins at 70 and gets points because:

* setup is easy,
* batch API exists,
* source URL begins with HTTPS.

None of those measurements establish runtime reliability.

Tool-calling quality becomes 70 largely because tool calling is supported.

Agentic capability gets synthetic boosts for structured output.

Writer/creative are effectively placeholder intelligence thresholds.

Then `free = 100 value`, regardless of whether the free tier permits five calls a day.

The `$ / successful task` calculation is even more misleading: every model is assigned the **same hardcoded task success probability** for a given workload.

So it is not actually:

> cost per successful task for Model X.

It's:

> token cost divided by a generic guessed success rate.

### Keep these as experimental projections

Expose:

```text
score_id: workhorse.v0.experimental
method: heuristic
evidence_coverage: 0.31
```

Never put them in the canonical facts table.

Eventually:

```text
Evidence
↓
MetricObservation
↓
ScoreVersion
↓
DerivedScore
```

Then you can rederive every score when the formula improves.

---

# 19. The API currently lies about its own filters

`/v1/deals` accepts:

```text
task
openai_compatible
automation_allowed
country
```

but doesn't actually apply them.

`/v1/deals/live` is essentially just another call to the generic deal listing.

Freshness says:

```python
"is_stale": False
```

unconditionally.

This is worse than not having the field.

An agent sees:

```json
"is_stale": false
```

and trusts it.

### API invariant

If you cannot compute a field:

```json
"is_stale": null
```

or omit it.

Never fill an unknown with an optimistic default.

---

# 20. The MCP implementation needs to be replaced

The Node MCP bridge directly embeds MCP arguments into Python source strings and then calls `python -c`.

For example, model/provider/task values are interpolated into generated Python.

That means untrusted tool input can potentially escape the string and execute Python.

This is a **P0 security flaw**.

It also reimplements filtering/ranking itself by opening snapshot JSON files.

So you have:

```text
REST semantics
≠
MCP semantics
```

### Make MCP tiny

```text
MCP
  ↓
llmdeals.service
```

or:

```text
MCP
  ↓
localhost REST API
```

No spawned `python -c`.

No embedded source strings.

No duplicate business logic.

If using Python anyway, I would probably retain **only the Python MCP server** and delete the Node bridge unless there is a compelling runtime reason for Node.

---

# 21. Hermes should not run your truth layer

The current Hermes skill is still framed around:

> recommending models, routing, checking prices, canaries, etc.

I would change Hermes' role.

### Hermes should produce proposals

```text
Scout
  → SourceCandidate

Investigator
  → CandidateClaim

Verifier
  → VerificationBundle

Terms agent
  → CandidateTermsClaims

Activation agent
  → CandidateActivationRecipe
```

Then deterministic application code commits only when invariants pass.

Hermes should **never** execute:

```sql
UPDATE deals SET ...
```

directly.

Use:

```text
Hermes
↓
POST /internal/candidates
↓
validator
↓
adjudication
↓
commit
```

That gives you agentic discovery without agentic corruption.

---

# 22. `agent/run.py` is mostly orchestration around the legacy system

It still invokes:

```text
normalize
refresh
canary
routing
quality
```

and the validation step only calls `app/test.py`.

That means Hermes' “official gate” doesn't validate much of the new source/event/canonical architecture.

The skill even says:

> “Never fabricate a result”

while the OpenCode and SenseNova adapters demonstrably contain fallback fabrication mechanisms.

The philosophy is right. The gate simply doesn't enforce it.

---

# 23. Your 52/54 “red team” result is not a red team

The artifact calls endpoints and marks them PASS because they responded.

For example:

```text
Canonical /v1/deals?limit=2 → PASS
```

That test wouldn't detect that several filters in the endpoint do nothing.

It didn't detect unknown price → `$0`.

It didn't detect the broken source differ.

It didn't detect fabricated fallback models.

It didn't detect fake expiry precision.

So call these:

> **API smoke tests**

because that's what they are.

The actual `app/test.py` itself has only seven broad gates, mostly around old normalization, quality and routing.

---

# 24. Build invariant tests instead

This is where I would invest hard.

Examples:

```text
UNKNOWN_PRICE_NEVER_EQUALS_FREE
UNKNOWN_ELIGIBILITY_NEVER_EQUALS_GLOBAL
UNKNOWN_TERMS_NEVER_EQUALS_ALLOWED

ONE_MODEL_CAN_HAVE_N_PROVIDER_OFFERINGS

RAW_OBSERVATION_CAN_BE_REPLAYED

EVERY_CANONICAL_CLAIM_HAS_EVIDENCE

EVERY_EVIDENCE_POINTS_TO_IMMUTABLE_ARTIFACT

EXTRACTOR_FAILURE_PRODUCES_NO_FACTS

FALLBACK_DATA_CANNOT_ENTER_CANONICAL_STATE

DATE_ONLY_EXPIRY_NEVER_BECOMES_EXACT_TIMESTAMP

FALSE→TRUE FREE = FREE_STARTED
TRUE→FALSE FREE = FREE_ENDED

MCP_AND_REST_RETURN_IDENTICAL_DOMAIN_RESULT

REPLAY(SAME_OBSERVATIONS) = SAME_CANONICAL_STATE

NEW_EXTRACTOR_VERSION_DOES_NOT_MUTATE_OLD_INTERPRETATION

FAILED_FETCH_DOES_NOT_EXPIRE_DEAL

PROVIDER_PAGE_DISAPPEARANCE != DEAL_EXPIRED

COMMUNITY_LEAD_CANNOT_BECOME_VERIFIED_WITHOUT_EVIDENCE
```

These matter vastly more than whether `/health` returns 200.

---

# 25. The migration system isn't a migration system

`SCHEMA_VERSION = 2`, but `migrate()` only loads `schema.sql` if the `schema_version` table doesn't exist.

So once you've initialized V2:

```text
schema V3 arrives
schema_version table exists
→ migrate() does nothing
```

You need:

```text
migrations/
  0001_initial.sql
  0002_claims.sql
  0003_activation.sql
```

with applied migration history.

If staying SQLite initially, this can be very simple.

---

# 26. “Strict typing” is currently false advertising

`db.py` says strict typing.

The SQLite schema doesn't declare `STRICT` tables.

Also prices are stored as `REAL`.

For financial/economic data, avoid binary floating point as canonical monetary representation.

Use either:

```text
integer nano/micro-dollars
```

or decimal strings / Decimal-compatible DB numeric representation.

Example:

```text
$0.14/M
```

could be normalized internally to:

```text
USD per token = 0.00000014 Decimal
```

or a fixed integer unit.

You do not want floating-point weirdness appearing in price histories.

---

# 27. `insert_snapshot_if_changed()` is broken

The new state is hashed as the complete `snapshot_data`.

The old state is reconstructed using a totally different tiny dictionary:

```text
i
o
c
f
r
```

covering only a subset of fields.

Those hashes aren't over the same canonical serialization.

So deduplication is unreliable.

### Use one function

```python
canonical_economic_state(snapshot)
```

for both previous and new values.

Then hash the resulting canonical object.

Better yet, use explicit equality over versioned fields rather than treating arbitrary JSON hashes as semantics.

---

# 28. `INSERT OR IGNORE` is wrong for event observation

`insert_event()` ignores an existing event ID.

Yet the event has:

```text
last_seen_at
status
confidence
corroboration_count
```

which therefore cannot naturally evolve through repeat observations if the ID remains stable.

Separate:

```text
DealEvent            immutable event
DealEventObservation repeat sightings/evidence
```

Then:

```text
DealActivated
```

happens once.

Additional confirmations do not mutate it; they attach evidence.

Much cleaner.

---

# 29. Don't store generated crawl state in Git

The repository contains a huge number of:

```text
snapshots/*.json
events/*.json
```

and many different event filenames point to identical blobs.

This will become unbearable once polling runs continuously.

Git should contain:

```text
source adapters
schemas
migrations
fixtures
goldens
tests
docs
```

Not your live database.

Keep only curated regression fixtures like:

```text
fixtures/opencode/2026-08-17.html
fixtures/opencode/expected_claims.json
```

Everything else goes to runtime storage.

---

# 30. Stop building Hot Router right now

This is the easiest scope cut.

The repo contains both `router.py` and `routing.py`, a `api_hot.py`, routing research, recommendation layers and feedback state.

None of that improves the thing you're uniquely positioned to own.

I'd move it to:

```text
experiments/router/
```

or another repository.

Same with Pāṭala-specific layer recommendations.

Your public core should not know what `L2`, `ARGMAP`, etc. are.

Those are **consumers** of LLM Deals.

That separation is important.

---

# The architecture I'd replace this with

```text
                     EXTERNAL WORLD
                          │
             ┌────────────┴────────────┐
             │                         │
      KNOWN SOURCES                 SCOUTING
 API/docs/RSS/changelog       web/HN/Reddit/regional
             │                         │
             ▼                         ▼
          FETCHER                    LEADS
             │                         │
             ▼                         ▼
      RAW OBSERVATION             Hermes Scout
             │                         │
             └────────────┬────────────┘
                          ▼
                     CANDIDATES
                          │
                Hermes investigators
                          │
                          ▼
                       CLAIMS
                          │
                  claim validation
                          │
             ┌────────────┴────────────┐
             ▼                         ▼
          EVIDENCE                 REJECTED
             │
             ▼
                    ADJUDICATION
                          │
                          ▼
              APPEND-ONLY DOMAIN EVENTS
                          │
                          ▼
                    PROJECTIONS
              ┌───────────┼───────────┐
              ▼           ▼           ▼
           Models       Offers       Deals
              │           │           │
              └───────────┼───────────┘
                          ▼
                     QUERY LAYER
                          │
         ┌────────────────┼────────────────┐
         ▼                ▼                ▼
       REST              MCP             SITE
```

And importantly:

```text
observations ≠ claims
claims ≠ events
events ≠ current state
current state ≠ scores
scores ≠ truth
```

That is the separation the current repo is missing.

---

# The canonical domain I would freeze

```text
Model
ModelAlias

Provider
ProviderEndpoint
ProviderOffering

CommercialPlan
CommercialOffer
QuotaRule

Source
SourceObservation
Artifact

Claim
ClaimEvidence
ClaimAdjudication

Deal
DealEvent

EligibilityRule
ActivationRecipe
ActivationStep

TermsSnapshot
TermsClaim

MetricObservation
DerivedMetric
ScoreVersion
```

That's enough.

You don't need 70 abstractions beyond those.

---

# The next build order

1. **Freeze feature development.** Move routing/hot APIs and Pāṭala-specific recommendation code out of the canonical core.

2. **Choose one schema.** Implement real `Model → ProviderOffering → CommercialOffer`, with Claim/Evidence/Observation as a perpendicular provenance layer.

3. **Make the DB actually canonical.** Everything writes through transactions. JSON becomes exports/fixtures only.

4. **Add immutable raw artifact storage.** Every observation retains retrievable bytes.

5. **Delete fallback commercial facts from every adapter.** Unknown must remain unknown.

6. **Rebuild OpenCode as the gold adapter.** It should perfectly detect Luna 2×, exact source evidence, plan association, confidence, and lifecycle. If OpenCode isn't perfect, don't pretend 38 adapters are useful.

7. **Rebuild source scheduling as persistent state.** `next_check_at`, adaptive cadence, ETag/Last-Modified, failures and health live in DB.

8. **Replace source diffing.** Stable offer identity + normalized semantic-state diff + append-only events.

9. **Implement Claim/Evidence verification.** Remove URL-domain confidence hacks.

10. **Implement honest temporal semantics.** Date precision/timezone/boundary/rolling quota/reset types.

11. **Implement ActivationRecipe + TermsSnapshot.** These are genuinely differentiated features.

12. **Collapse to one `/v1` API and one MCP adapter.** Generate OpenAPI; MCP delegates to service functions.

13. **Replace smoke-test bragging with invariants and replay fixtures.** The quality metric should become “X canonical invariants pass,” not “52 endpoints returned responses.”

14. **Only then expand back to the 38 sources.** Each adapter must earn `production` status via fixtures, evidence completeness and replay tests.

---

## A source adapter should have to earn production status

I'd create explicit stages:

```text
REGISTERED
    ↓
FETCHING
    ↓
FIXTURE_CAPTURED
    ↓
EXTRACTION_TESTED
    ↓
IDENTITY_TESTED
    ↓
EVIDENCE_COMPLETE
    ↓
LIFECYCLE_TESTED
    ↓
PRODUCTION
```

So “38 adapters” stops being a vanity metric.

You may end up with:

```text
38 registered
11 production
9 experimental
8 fetch-only
10 broken
```

That is **far more trustworthy**.

And your public API defaults:

```http
?source_maturity=production
```

---

# What the repo actually does well

There is real good material worth preserving.

The instinct to separate `Model → ProviderOffering → CommercialOffer → DealEvent` is correct.

The source-adapter architecture is correct in spirit.

Community leads are already quarantined separately in the SQLite schema, which is the right direction.

The desire for append-only offer snapshots and temporal events is correct.

The source-registry idea is correct.

The Hermes skill + kanban approach can work well **once agents generate proposals instead of truth**.

The regional adapter coverage is exactly where this project can become unusually useful.

The problem is that the implementation raced several phases ahead of its epistemic foundations.

## The single most important correction

The current repo optimizes for:

> **How much useful LLM data can we expose?**

Change the engineering objective to:

> **For every value we expose, can we answer exactly where it came from, what was actually observed, how it was interpreted, how certain we are, when it was valid, and reproduce that interpretation later?**

Once that invariant holds, **2,000 excellent records beat 200,000 vaguely plausible records**.

That is how `dell` becomes infrastructure other agents can safely build routers on rather than another clever model-price scraper.
