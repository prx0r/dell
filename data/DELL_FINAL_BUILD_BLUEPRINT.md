# LLM Deals / `prx0r/dell`
## Final Build Blueprint — canonical deal intelligence layer

**Review target:** current `master` head `2350ea2d4e80dccefc1a48fe063c82a0c78c7b53`

## 0. Final product decision

LLM Deals should **not** be a router in V1.

It should be the highest-trust live data layer for:

- models
- providers
- provider offerings
- commercial plans
- prices
- free capacity
- quotas
- promotions
- credits
- subscription allowances
- rate limits
- regional eligibility
- setup friction
- terms/restrictions
- expiry/reset semantics
- verification
- historical changes
- measured model capability data
- derived “opportunity” metrics

Routers, agents, IDEs, dashboards, newsletters and researchers should be able to build on this data.

**North-star sentence**

> LLM Deals provides live, verifiable, machine-readable data about LLM inference opportunities, with every important claim traceable to evidence and every uncertainty represented honestly.

The site is a human view over the same service.
The MCP server is an agent view over the same service.
Neither owns independent business logic.

---

# 1. Current-state verdict

The repo has improved substantially. The latest architecture is directionally correct:

- canonical SQLite read path exists
- rich quota fields have been added
- `region=NULL` is better than default-global
- explicit provider multiplier vs derived capacity ratio is being separated
- endpoint reachability is no longer called proof that a deal works
- Hermes user testing is surfacing real usability failures
- model/provider cross-reference is being attempted

But it is **not ready to become a trusted public API**.

The central problem is now **convergence and epistemology**, not source count.

There are still multiple truth systems, multiple APIs, multiple histories, multiple schedulers and multiple ranking mechanisms. Several fields that look “verified” are still inferred, defaulted or inherited without sufficient identity proof.

The correct next move is to freeze source expansion and finish the truth kernel.

---

# 2. P0 findings from the latest push

## P0.1 — Latest enrichment is not reproducible

The newest two commits claim:

- same-model enrichment across providers
- 708 inherited fields
- smart context enrichment
- 506 model names in a context lookup
- MiMo V2.5 context inherited to other offerings

But those commits modify only `data/llmdeals.sqlite3`.

There is no committed enrichment module implementing the described mechanism.

That means:

1. the database contains state that cannot be regenerated from source code;
2. a fresh rebuild can lose the enrichment;
3. nobody can audit which identity rule copied which field;
4. a bad one-off match can silently contaminate many offerings.

**Required fix**

Never mutate canonical facts with an interactive/one-off enrichment script.

Create a committed deterministic subsystem:

```text
identity/
  resolver.py
  aliases.py
  assertions.py
  transfer_rules.py

enrichment/
  project_model_facts.py
```

Every inherited field must produce an auditable record:

```json
{
  "target": "offering:opencode-go/mimo-v2.5",
  "field": "context_tokens",
  "value": 1000000,
  "derivation": "exact_model_identity_projection",
  "source_claim_id": "...",
  "identity_assertion_id": "...",
  "resolver_version": "identity.v1"
}
```

If it cannot be regenerated, it cannot enter canonical state.

---

## P0.2 — Model identity is still unsafe

Do not use “normalized model name” as identity.

`MiMo V2.5` and `MiMo V2.5 Pro` are separate provider/model identifiers. They may share some family-level properties, but they are not automatically the same model.

Never transfer:

- benchmark scores
- agentic scores
- tool behavior
- latency
- pricing
- quota
- context
- modalities
- output cap

from a sibling variant simply because the names are similar.

Use identity relationships:

```text
EXACT_SAME_MODEL
EXPLICIT_PROVIDER_ALIAS
SAME_WEIGHTS_DIFFERENT_ROUTE
SAME_MODEL_DIFFERENT_PROVIDER
SIBLING_VARIANT
MODEL_FAMILY
UNKNOWN_RELATION
```

Only `EXACT_SAME_MODEL`, `EXPLICIT_PROVIDER_ALIAS`, and carefully defined `SAME_MODEL_DIFFERENT_PROVIDER` relationships can propagate selected model-native fields.

Even then, provider-offering fields cannot propagate.

### Field-locality matrix

| Field | Canonical owner | Cross-provider transfer? |
|---|---|---|
| published model family | model | yes if exact identity |
| model release date | model/version | yes if exact identity |
| benchmark result | exact model/version | **no sibling inheritance** |
| native modality | exact model/version | yes if exact identity |
| native max context | exact model/version | maybe, with evidence |
| provider accepted context | provider offering | **never** |
| tool calling supported | provider offering | **never blindly** |
| OpenAI compatibility | provider endpoint | never model-wide |
| latency / TPS | provider route | never |
| free quota | commercial offer | never |
| subscription allowance | commercial offer | never |
| promotion multiplier | deal | never |
| region/KYC/card | commercial offer/eligibility | never |

A fact should live at the narrowest entity to which it is actually true.

---

## P0.3 — “Canonical DB” still is not the only service surface

Current REST reads SQLite, which is progress.

But MCP still loads `snapshots/*.json` directly.
The web layer still reads an old absolute `canonical-models.json` path.
Legacy APIs remain.
Old history reads JSON snapshot files.

This means:

```text
REST truth != MCP truth != website truth != legacy API truth
```

**Required fix**

Create one application service:

```text
llmdeals/service.py
```

with methods such as:

```python
list_deals(...)
get_deal(...)
list_offers(...)
get_model(...)
compare_model(...)
get_changes(...)
get_activation_recipe(...)
get_terms(...)
get_evidence(...)
```

All surfaces call this.

```text
SQLite/Postgres
      ↓
Repository
      ↓
DealService
  ┌───┼────┐
 REST MCP  site/export
```

Delete direct snapshot reading from MCP and web.

---

## P0.4 — Claim/Evidence tables exist but are not the ingestion path

The schema now contains:

- `claims`
- `evidence`
- `verification_checks`
- `activation_recipes`

This is good.

But discovery still writes adapter output directly into `offers`.

The core pipeline must become:

```text
Source
  ↓
Artifact
  ↓
Observation
  ↓
CandidateClaim
  ↓
Identity resolution
  ↓
Evidence
  ↓
Adjudication
  ↓
Domain event
  ↓
Current projection
```

The `offers` table should be a **projection**, not the first durable interpretation of a page.

---

## P0.5 — Raw evidence is still not retained

`source_observations` stores hashes, URLs and timestamps but not the exact source artifact.

A hash without the bytes is not reproducible provenance.

Store raw source artifacts content-addressably:

```text
artifact_sha256
artifact_uri
content_type
encoding
response_headers_json
fetched_at
```

For local development:

```text
data/artifacts/sha256/ab/abcdef....gz
```

Production can move those bytes to object storage.

Evidence then points to:

```text
artifact_id
selector_type
selector
byte_start
byte_end
excerpt
extractor_version
```

---

## P0.6 — Discovery records only the first observation

Some adapters fetch multiple URLs/pages.

Discovery currently records only `observations[0]` in canonical observations.

This destroys provenance for:

- pagination
- fallback URLs
- multiple official pages
- partial fetches
- pricing page + plan page combinations

Record every observation.

Also distinguish run completeness:

```text
COMPLETE
PARTIAL
FAILED
RATE_LIMITED
AUTH_REQUIRED
BLOCKED
```

Do not treat “one page succeeded” as a complete source refresh.

---

## P0.7 — Current dedupe can discard richer evidence

Discovery deduplicates by `offer_id` and keeps the first record.

If page A knows price and page B knows quota for the same offer, one can be discarded.

Candidate extraction should merge **claims**, not choose a winning snapshot.

Example:

```text
page A → price claim
page B → quota claim
page C → expiry claim
```

All three belong to the same offer.

---

## P0.8 — Upsert + COALESCE creates immortal stale data

`upsert_offer()` preserves old values when a new extraction is NULL.

This is dangerous.

If a provider removes a quota, ends a promotion, removes context metadata, or changes terms, old values can survive indefinitely.

Canonical state should be derived from current valid claims, not sticky SQL columns.

Use append-only observations/claims/events and a reducer:

```text
current_projection = reduce(valid_claims, events, time)
```

Never rely on `COALESCE(new, old)` to decide truth.

---

## P0.9 — `free=False` still means two different things

The source dataclass defaults:

```text
free = False
```

and DB defaults:

```text
free = 0
```

But:

```text
CONFIRMED_PAID
```

and:

```text
UNKNOWN_FREE_STATUS
```

are different.

Use tri-state semantics:

```text
price_state:
  FREE
  PAID
  UNKNOWN
```

Optionally keep nullable `is_free`.

Absence of evidence must never become a negative fact.

The same principle applies to:

- automation allowed
- commercial use
- region
- tool support
- card required
- KYC
- production use

---

## P0.10 — Stable offer IDs still encode fake “global”

Discovery generates the offer ID using `"global"` even though it stores region as NULL.

Therefore identity can encode a claim the data explicitly says is unknown.

Do not put eligibility into the core offering identity.

Use:

```text
provider_offering_id =
provider + provider_model_slug + endpoint/product

commercial_offer_id =
provider_offering + plan/price-meter

deal_id =
commercial_offer + deal/event identity
```

Eligibility is a rule attached to the commercial offer/deal.

---

## P0.11 — Rich fields are still not all round-tripping

The adapter dataclass and discovery field names differ.

Examples include variants of:

```text
requests_day
requests_per_day
requests_minute
requests_per_minute
tokens_day
tokens_per_day
```

Several canonical fields are not passed through discovery at all.

Create one typed canonical candidate object and stop manually plumbing dictionaries.

Use validation:

```python
class CandidateOffer(BaseModel):
    ...
```

Every adapter must return the same typed shape.

Then test:

```text
adapter object
→ canonical candidate
→ DB
→ service
→ API
```

with exact round-trip equality for every field.

---

## P0.12 — Lifecycle/history still is not canonical

`source_diff` is improved but discovery does not use it to create canonical `deal_events`.

`promo_extract` finds candidate events, but they are not committed as the event history.

The API also contains overlapping history mechanisms.

One event log only:

```text
OFFER_DISCOVERED
OFFER_CHANGED
OFFER_WITHDRAWN
DEAL_ACTIVATED
DEAL_MODIFIED
DEAL_EXPIRED
DEAL_EXTENDED
PRICE_CHANGED
QUOTA_CHANGED
TERMS_CHANGED
ELIGIBILITY_CHANGED
MODEL_ADDED
MODEL_REMOVED
```

Then expose:

```text
GET /v1/events?since=<cursor>
```

Everything historical comes from this event stream.

---

## P0.13 — Scheduler is still split between RAM and SQLite

The DB has durable scheduling state, but discovery still asks the in-memory registry which sources are due.

A new process resets RAM timestamps.

Delete scheduling state from the Python registry.

Registry describes immutable configuration.
DB owns mutable scheduler state.

```text
SourceDefinition
  id
  adapter
  default cadence
  priority

SourceRuntime
  last_attempt
  last_success
  last_change
  next_check
  failures
  etag
  last_modified
```

The scheduler queries `next_check_at`.

---

## P0.14 — Do not auto-disable a source after three transient failures

Transient blocks, rate limits and site outages are normal.

Use exponential backoff:

```text
15m
30m
1h
3h
6h
12h
```

Keep state:

```text
ACTIVE
BACKOFF
BLOCKED
AUTH_REQUIRED
MANUAL_REVIEW
RETIRED
```

Permanent disablement should be an explicit state transition.

---

## P0.15 — Freshness is still fabricated

The API currently emits `is_stale=False` even though the code itself says it does not know.

Never emit optimistic defaults.

Expose:

```json
{
  "freshness": {
    "last_observed_at": "...",
    "last_verified_at": null,
    "max_age_seconds": 1800,
    "state": "UNKNOWN"
  }
}
```

Possible states:

```text
FRESH
STALE
UNKNOWN
SOURCE_ERROR
```

---

## P0.16 — Verification still conflates source authority with claim verification

“Official-looking domain” is not the same thing as “this claim was verified.”

Verification must be claim-level.

Use this ladder:

```text
LEAD
SOURCE_FETCHED
CLAIM_EXTRACTED
PRIMARY_EVIDENCE
PRIMARY_CORROBORATED
ENDPOINT_REACHABLE
MODEL_LISTED
INFERENCE_SUCCEEDED
DEAL_CONDITION_CONFIRMED
```

Examples:

- HTTP 401 → `ENDPOINT_REACHABLE`, not deal verified.
- model appears in `/models` → `MODEL_LISTED`
- minimum completion succeeds → `INFERENCE_SUCCEEDED`
- free request succeeds without charge or quota endpoint confirms allowance → `DEAL_CONDITION_CONFIRMED`

Store every verification check independently.

---

## P0.17 — `/deals/live` is not a real “live deals” endpoint

The API currently treats ordinary offers as deals.

Split catalog from opportunity radar.

### Catalog

```text
/models
/providers
/offerings
/prices
/free
```

### Deals

Only unusual opportunities:

```text
/deals
/deals/hot
/deals/expiring
/deals/new
/deals/changed
```

A normal market-rate metered model should not appear in `/deals`.

---

## P0.18 — Several API filters are accepted but not enforced

If a parameter is in the contract, it must work.

Do not accept:

- task
- automation allowed
- country

until the service can answer them honestly.

Either implement or remove.

Contract correctness is more important than endpoint count.

---

## P0.19 — Unknown price is still unsafe in parts of the stack

REST improved this.
MCP still contains the classic pattern:

```python
(input_per_m or 0)
```

This turns unknown into zero for filtering.

Delete all such patterns.

Create one money type:

```text
KNOWN(value)
FREE
UNKNOWN
NOT_APPLICABLE
```

Derived calculations only run on known values.

If output price is unknown, do not calculate a fake blended cost using zero output price.

---

## P0.20 — Scoring still contains dimension errors

The current “legitimate scoring” is not yet legitimate enough for public ranking.

Examples:

- reliability is a hardcoded 70
- unknown tool-calling is inserted into workhorse as 50
- request capacity per 5h is used as a proxy for speed
- free with no intelligence data can receive a made-up value score
- provider endpoint capacity is not tokens/sec
- benchmark coverage differs wildly by model

Keep raw metrics and derived rankings separate.

Public labels should say:

```text
EXPERIMENTAL
score_version
coverage
confidence
```

Do not publish a single authoritative “workhorse score” yet.

---

## P0.21 — Free qualification collapses incompatible quota units

`1500 / 5h` is not `1500 / day`.

Keep quota vectors intact:

```json
{
  "amount": 1500,
  "unit": "requests",
  "window": "PT5H",
  "scope": "per_model",
  "reset_mode": "rolling_or_fixed",
  "reset_anchor": null
}
```

A normalized “estimated requests/day” can be a derived metric, clearly labeled.

Never use the normalized estimate as the source fact.

---

## P0.22 — `always_free` must never be the default

Unknown duration is:

```text
UNKNOWN
```

not permanent.

Deal duration:

```text
PERMANENT
TEMPORARY
PUBLIC_BETA
ROLLING_TRIAL
NEW_USER
UNTIL_CREDITS_EXHAUSTED
UNKNOWN
```

---

## P0.23 — Current cross-reference result happens to prove the wrong mechanism

For MiMo V2.5, an independent source may confirm a 1M context window.

That does **not** mean copying context/benchmarks/tool data from a “Pro” sibling was valid.

Correct process:

```text
MiMo V2.5 exact identity
↓
find direct/equivalent exact-model evidence
↓
attach claim to MiMo V2.5
```

Incorrect:

```text
MiMo V2.5 Pro has field X
↓
normalized name looks close
↓
copy X to MiMo V2.5
```

The result may be right by accident while the mechanism is unsafe.

---

## P0.24 — The website still points at an obsolete absolute file

The current web helper reads an absolute local path to an old `canonical-models.json`.

That is neither portable nor canonical.

The site should call `DealService` at build time or consume a versioned export produced from it:

```text
data/exports/public-v1.json
```

Generated by:

```text
python -m llmdeals.export public-v1
```

No hard-coded `/root/...` paths.

---

## P0.25 — The docs describe the wrong product

README/VISION still frame this as Garglecum, a Pāṭala translation recommender/router.

That is now scope debt.

Rewrite around:

> live inference-market intelligence + verified deal aggregation

Keep Pāṭala as an example consumer, not the mission.

---

## P0.26 — Generated runtime state is still committed

Current Git history includes:

- SQLite database
- probe logs
- cron logs
- poll reports
- autonomous test outputs
- snapshots/events from prior commits

Do not use Git as the live market database.

Git should contain:

```text
code
migrations
schemas
gold fixtures
tests
docs
small curated examples
```

Runtime state belongs in DB/object storage.

Add:

```gitignore
data/*.sqlite3
data/*.sqlite3-*
data/cron.log
data/poll-report.json
data/probe-log.json
data/history/
snapshots/
events/
```

---

## P0.27 — There is no visible CI status on current head

A commit message saying tests pass is not a release gate.

Add GitHub Actions:

```text
lint
typecheck
unit
fixtures
migration-test
invariant
MCP/REST parity
gold-source replay
security scan
```

Protect main so red CI cannot merge.

---

## P0.28 — Previous secret exposure must be treated as compromised

A previous commit message contained an apparent API credential.

If that credential was real:

1. rotate it;
2. remove it from active use;
3. scrub history if appropriate;
4. add secret scanning;
5. prevent secrets in commit messages/logs.

Never assume “not in current files” means a committed credential is safe.

---

# 3. Final V1 scope

## In scope

### Exhaustive catalog

- models
- exact model variants
- providers
- provider endpoints
- provider offerings
- prices
- context
- modality
- compatibility
- limits
- regional availability

### Deal radar

- temporary free
- temporary price discounts
- explicit usage multipliers
- launch/beta subsidies
- free quota changes
- subscription allowances
- signup credits
- startup/research credits
- batch discounts
- off-peak pricing
- regional bargains
- unusually underpriced routes
- expiring opportunities

### Trust layer

- evidence
- freshness
- verification
- lifecycle history
- uncertainty
- terms/restrictions
- activation steps

### Distribution

- REST
- MCP
- static site
- RSS/Atom or JSON feed
- event cursor API

## Explicitly out of V1

- inference proxy
- hot router
- user billing
- API-key vault
- inference resale
- autonomous account creation
- model hosting
- user prompt logging
- Pāṭala-specific routing
- complex bandit router

---

# 4. Canonical entity model

## Identity plane

```text
ModelFamily
ModelVersion
ModelAlias
IdentityAssertion
Provider
ProviderEndpoint
ProviderOffering
```

## Commercial plane

```text
CommercialPlan
CommercialOffer
QuotaRule
EligibilityRule
Deal
DealEvent
```

## Evidence plane

```text
Source
Artifact
Observation
Claim
Evidence
Adjudication
VerificationCheck
```

## Access plane

```text
ActivationRecipe
ActivationStep
TermsSnapshot
TermsClaim
```

## Measurement plane

```text
MetricObservation
DerivedMetric
ScoreDefinition
ScoreValue
```

### Key rule

Permanent truth is:

```text
stable identity
+ source artifacts
+ observations
+ claims/evidence
+ append-only events
```

Current API objects are projections.

---

# 5. Suggested relational schema

This can still run on SQLite initially.

## `models`

```text
model_id PK
family_id
canonical_name
variant_name
developer
release_date
status
```

## `model_aliases`

```text
alias
model_id
namespace
source_claim_id
confidence
```

## `identity_assertions`

```text
left_ref
right_ref
relationship
confidence
evidence_id
resolver_version
```

## `providers`

```text
provider_id
name
homepage
country
```

## `provider_endpoints`

```text
endpoint_id
provider_id
base_url
protocol
compatibility
```

## `provider_offerings`

```text
offering_id
provider_id
endpoint_id
model_id
provider_model_slug
status
```

## `commercial_offers`

```text
commercial_offer_id
offering_id
plan_id
pricing_state
currency
input_price
output_price
cache_read_price
cache_write_price
status
```

## `quota_rules`

```text
quota_rule_id
commercial_offer_id
amount
unit
window_iso8601
scope
reset_mode
reset_anchor
effective_from
effective_until
```

## `eligibility_rules`

```text
eligibility_rule_id
commercial_offer_id/deal_id
rule_type
operator
value_json
```

## `deals`

Current identity/projection for unusual opportunity.

```text
deal_id
commercial_offer_id
deal_type
current_status
```

## `deal_events`

Append-only:

```text
event_id
deal_id
event_type
effective_at
observed_at
claim_id
previous_json
current_json
```

## `sources`

```text
source_id
provider_id nullable
url
authority
language
country
source_type
adapter
priority
enabled
```

## `source_runtime`

```text
source_id
last_attempt
last_success
last_change
next_check_at
failures
etag
last_modified
state
```

## `artifacts`

```text
artifact_id
sha256
uri
content_type
encoding
byte_length
```

## `observations`

```text
observation_id
source_id
artifact_id
fetched_at
http_status
completeness
request_metadata_json
response_headers_json
```

## `claims`

```text
claim_id
subject_type
subject_id
predicate
value_json
valid_from
valid_until
confidence
extractor_version
observation_id
```

## `evidence`

```text
evidence_id
claim_id
artifact_id
selector_type
selector
byte_start
byte_end
excerpt
```

## `verification_checks`

```text
check_id
claim_id/deal_id/offering_id
check_type
status
checked_at
details_json
```

## `activation_recipes`

```text
recipe_id
commercial_offer_id
version
status
```

## `activation_steps`

```text
step_id
recipe_id
position
actor
step_type
instructions
url_claim_id
requires_human
```

## `terms_snapshots`

```text
terms_snapshot_id
provider_id
artifact_id
effective_at
observed_at
```

## `terms_claims`

```text
terms_snapshot_id
predicate
value
evidence_id
confidence
```

## `metrics`

Raw observations.

## `derived_metrics`

Versioned calculations only.

---

# 6. Deal definition

A deal is **not** every cheap/free model.

A deal is an unusually favorable inference opportunity relative to an appropriate baseline.

## Deal types

```text
PROMO_PRICE
TEMPORARY_FREE
USAGE_MULTIPLIER
QUOTA_BOOST
NEW_USER_CREDIT
TRIAL_CREDIT
STARTUP_CREDIT
RESEARCH_CREDIT
SUBSCRIPTION_ALLOWANCE
BATCH_DISCOUNT
OFF_PEAK_DISCOUNT
BETA_FREE
REFERRAL_CREDIT
REGIONAL_DISCOUNT
PRICE_ANOMALY
PROVIDER_ARBITRAGE
```

## Non-deal examples

- ordinary market-rate API
- permanent free model with tiny quota and no unusual advantage
- generic provider listing
- model existing in a catalog

These remain in `/catalog` or `/free`.

---

# 7. Separate the ranking dimensions

Never create one mystical score.

Expose these separately:

## `opportunity_score`

How attractive the economics/capacity are.

## `confidence_score`

How certain the underlying claims are.

## `urgency_score`

How likely the user is to miss the opportunity.

## `access_score`

How easy the deal is to activate/use.

## `utility_vector`

Task-relevant model usefulness.

## `deal_score`

A display ranking derived from the above and versioned.

Example conceptual formula:

```text
deal_score =
  opportunity × 0.45
+ urgency     × 0.20
+ access      × 0.15
+ confidence  × 0.20
```

Do not hide the components.

---

# 8. Free capacity qualification

Do not rank “free” using one scalar before basic truth is known.

## Hard metadata

```text
working_state
exact_model
context
output_limit
quota
quota_window
quota_scope
rate_limit
tool support
compatibility
region
card
phone
KYC
terms
duration
```

Unknown remains unknown.

## Then publish views

```text
Best useful free
Highest free capacity
Best free coding
Best free agentic
Best free long-context
Lowest setup friction
Most verified free
```

A free deal can have:

```text
utility_score = 92
confidence = 38
```

That tells the user “potentially amazing, insufficiently verified.”

---

# 9. Temporal model

Never invent second-level precision.

## Expiry modes

```text
EXACT_INSTANT
DATE_ONLY
ROLLING_FROM_SIGNUP
ROLLING_FROM_ACTIVATION
QUOTA_WINDOW
CALENDAR_RESET
UNTIL_CREDITS_EXHAUSTED
UNTIL_PUBLIC_BETA_ENDS
UNKNOWN
```

Store:

```text
source_expression
instant
date
timezone
precision
boundary
anchor
duration
```

Only render a second-by-second countdown when `EXACT_INSTANT` is known.

Otherwise:

```text
Ends Aug 31 — exact cutoff not published
```

## Reverification schedule around exact expiry

```text
T-24h
T-1h
T-10m
T+2m
T+1h
T+24h
```

Passing the stored timestamp does not alone prove the provider ended the deal.
It triggers reverification.

---

# 10. Activation recipes

This should be a signature feature.

## Actor types

```text
HUMAN_REQUIRED
AGENT_SAFE
AGENT_OPTIONAL
SYSTEM
```

## Step types

```text
OPEN_URL
CREATE_ACCOUNT
VERIFY_EMAIL
VERIFY_PHONE
ACCEPT_TERMS
ADD_PAYMENT_METHOD
COMPLETE_KYC
ACTIVATE_PLAN
CREATE_API_KEY
STORE_SECRET
CONFIGURE_CLIENT
RUN_HEALTHCHECK
RUN_CANARY
```

Legal consent, payment and identity checks remain human-required.

Agents can do:

- open exact docs/setup page
- generate config
- validate key format locally
- write LiteLLM/OpenCode config
- run health checks
- test model listing
- test a minimal completion
- record local quota observations

Never ask the agent to bypass provider restrictions.

---

# 11. Terms model

Do not store prose like:

```text
"automation allowed"
```

without evidence.

Use claims:

```text
api_use
automation_allowed
commercial_use
production_use
resale
account_sharing
training_on_inputs
logging_policy
regional_restriction
rate_limit_policy
```

Each is:

```text
TRUE
FALSE
CONDITIONAL
UNKNOWN
```

and references exact terms evidence.

---

# 12. Optional usage tracking

Do **not** make usage tracking part of core V1.

Core LLM Deals should remain stateless and useful without API keys.

Design an optional later component:

```text
llmdeals-meter
```

It can track locally:

```text
provider
model
deal
requests
input tokens
output tokens
cache tokens
latency
errors
estimated cost
quota consumed
```

Rules:

- prompts/completions OFF by default
- API keys never sent to LLM Deals
- local ledger is authoritative for local observations
- provider-reported quota preferred when available
- estimated quota clearly marked estimated

This later enables routing without polluting the core data product.

---

# 13. Source registry and polling

## Deterministic scheduler owns routine work

Hermes should not reread every page on a timer.

Scheduler tick:

```text
every few minutes
↓
SELECT sources WHERE next_check_at <= now
↓
fetch only due sources
```

## Starting cadence classes

```text
active promo               10–15m
hot pricing page           30m
provider changelog         30–60m
catalog API                1h
normal pricing/docs        3–6h
startup/research program   12–24h
terms                      24h
very stable source         2–7d
```

Adapt based on:

```text
change frequency
active-deal count
expiry proximity
source authority
historical volatility
failure state
fetch cost
```

Use HTTP validators when available.

---

# 14. Lead discovery

Known-source monitoring does not discover new providers.

Create a separate `leads` subsystem.

Sources:

```text
provider blogs
release notes
pricing pages
RSS
GitHub
HN
Reddit
regional developer media
multilingual web searches
community submissions
provider submissions
```

Lead state:

```text
DISCOVERED
INVESTIGATING
PRIMARY_SOURCE_FOUND
VERIFIED
REJECTED
DUPLICATE
STALE
```

A community post can create a lead.
It cannot directly create a verified deal.

---

# 15. Hermes architecture

Hermes should be the autonomous research staff, not the database.

## `deal-scout`

Find new leads.

Output only `CandidateLead`.

## `change-investigator`

Given changed source artifacts/diffs:

- identify meaningful commercial changes
- ignore nav/layout noise
- generate candidate claims

## `claim-verifier`

Seek primary official evidence.
Return a `VerificationBundle`.

## `identity-resolver`

Resolve model/provider identity conservatively.
Can propose an assertion.
Cannot merge on its own.

## `terms-auditor`

Extract current terms claims and exact evidence.

## `activation-author`

Build/update activation recipe from official setup docs.

## `stale-deal-reviewer`

Investigate deals whose source changed/disappeared.

## `regional-scout`

Run multilingual discovery vocabularies and propose new sources.

## `audit-agent`

Sample canonical claims and independently verify them.

### Agent permissions

Scout:

```text
web/browser/search
read DB
NO canonical write
NO provider keys
```

Verifier:

```text
web/browser
read artifacts
write candidate bundle only
```

Commit worker:

```text
NO freeform web
accepts typed candidate bundle
deterministic validation
transactional DB write
```

---

# 16. Canonical ingestion loop

```text
01 scheduler selects due source

02 fetch
   save raw artifact

03 create observation
   preserve every request/page

04 deterministic parser
   emits CandidateClaims

05 if parser confidence insufficient:
   enqueue Hermes investigation

06 identity resolution
   attach exact subject IDs

07 claim validation
   type/schema/units/time semantics

08 evidence validation
   every canonical claim must have evidence

09 adjudication
   choose current supported claim(s)

10 compare with prior current projection

11 emit append-only domain events

12 rebuild current projections

13 update source runtime / next_check

14 publish API/event feed

15 optional live verification
   adds VerificationCheck, never mutates history
```

---

# 17. Service/API contract

## Catalog

```text
GET /v1/models
GET /v1/models/{id}
GET /v1/providers
GET /v1/providers/{id}
GET /v1/offerings
GET /v1/offerings/{id}
GET /v1/prices
GET /v1/free
```

## Deals

```text
GET /v1/deals
GET /v1/deals/{id}
GET /v1/deals/hot
GET /v1/deals/expiring
GET /v1/deals/new
```

## Trust

```text
GET /v1/deals/{id}/evidence
GET /v1/deals/{id}/verification
GET /v1/deals/{id}/activation
GET /v1/deals/{id}/terms
GET /v1/deals/{id}/history
```

## Changes

```text
GET /v1/events?since=<cursor>
```

## Compare

```text
GET /v1/compare?model=<canonical_model_id>
```

## Experimental derived views

```text
GET /v1/rankings/workhorse
GET /v1/rankings/coding
GET /v1/rankings/free
```

Responses must include:

```text
score_version
coverage
confidence
```

Never pretend derived ranking is truth.

---

# 18. Minimal MCP

Do not expose 20 overlapping tools.

Six excellent tools are enough:

```text
search_deals
get_deal
compare_model_offers
get_recent_changes
get_activation_recipe
get_evidence
```

Optional:

```text
search_catalog
```

MCP calls `DealService` directly.

No snapshot reading.
No duplicated filters.
No subprocess-generated Python.
No separate scoring implementation.

---

# 19. Website

Homepage:

```text
HOT NOW
ENDING SOON
NEWLY FREE
BIGGEST PRICE DROPS
BEST CURRENT WORKHORSE OPPORTUNITIES
BEST VERIFIED FREE CAPACITY
RECENT CHANGES
```

Navigation:

```text
Deals
Free
Models
Providers
Prices
Credits
History
API
```

Deal card:

```text
provider/model
what changed
why it matters
normal vs current economics
quota
context
setup friction
eligibility
verification status
last checked
expiry semantics
source/evidence
```

Make trust visible.

Example:

```text
VERIFIED CLAIM
Official source
Observed 11m ago
Endpoint listed
Inference not yet tested
Exact expiry unknown
```

That is better than a generic green check.

---

# 20. Scoring rules

## Do not mix dimensions

Do not use requests/5h as speed.
Do not use fetch success as model reliability.
Do not use tool support as tool-call accuracy.

Raw metrics:

```text
throughput_tps
TTFT
quota
context
price
benchmark
tool_supported
tool_benchmark
provider_uptime
```

Derived metrics calculate only from relevant dimensions.

## Workhorse

Eventually:

```text
task_quality
effective task cost
runtime reliability
latency
context
tool quality
capacity
```

But if data is missing, publish coverage and uncertainty.

## Dealness

Separate from model quality.

A mediocre model can be a spectacular deal.
A frontier model can be a terrible deal.

---

# 21. Testing and release gates

## Unit

- parsers
- unit conversion
- temporal parser
- identity resolver
- price state
- eligibility semantics

## Fixture replay

Captured real source artifact:

```text
fixture artifact
→ parser
→ exact expected claims
```

OpenCode Go and OpenCode Zen should become gold fixtures.

## Round-trip

```text
adapter candidate
→ DB
→ service
→ REST
→ MCP
```

assert exact semantics.

## Mutation tests

Deliberately mutate:

```text
free true→false
multiplier 2→1
quota 1500→500
expiry date
model alias
region
```

and assert the expected event.

## Negative invariants

```text
UNKNOWN_PRICE != FREE
UNKNOWN_REGION != GLOBAL
UNKNOWN_TERMS != ALLOWED
DATE_ONLY != EXACT_INSTANT
SIBLING_VARIANT != SAME_MODEL
401 != DEAL_CONFIRMED
FETCH_FAILURE != DEAL_EXPIRED
NO_EVIDENCE != VERIFIED
```

## Source completeness

A partial pagination failure cannot publish removals.

## MCP/REST parity

Compare full semantic objects, not just counts.

## Random audit

Sample 100 canonical claims:

```text
claim
→ evidence
→ artifact
→ parser replay
```

100/100 reproducible.

## Live audit

Randomly sample 20 currently promoted deals and compare to current primary source.

---

# 22. Git/CI hygiene

Keep in Git:

```text
app code
migrations
schemas
tests
fixtures
docs
small gold evidence
```

Remove from Git:

```text
live sqlite DB
snapshots
events
cron logs
probe logs
poll reports
Hermes raw transcripts
generated history
secrets
```

Add CI and branch protection.

Use a versioned migration system:

```text
migrations/
  0001_initial.sql
  0002_claims_evidence.sql
  0003_quota_rules.sql
```

`CREATE TABLE IF NOT EXISTS` is not a migration system.

---

# 23. Target repository structure

```text
llmdeals/
  domain/
    identity.py
    commercial.py
    temporal.py
    evidence.py
    verification.py
    activation.py

  storage/
    db.py
    migrations/
    artifacts.py
    repositories.py

  sources/
    registry.py
    base.py
    adapters/
      opencode_go.py
      opencode_zen.py
      openrouter.py
      ...

  ingest/
    fetch.py
    parse.py
    claims.py
    adjudicate.py
    events.py
    project.py

  identity/
    resolver.py
    aliases.py
    transfer_rules.py

  verification/
    endpoint.py
    inference.py
    deal_condition.py

  scoring/
    deal_score.py
    free_score.py
    task_metrics.py

  service/
    deals.py
    catalog.py
    events.py

  api/
    app.py
    schemas.py

  mcp/
    server.py

  agents/
    skills/
      scout/
      verifier/
      terms/
      activation/
      audit/

  tests/
    unit/
    fixtures/
    replay/
    integration/
    mutation/
```

Legacy:

```text
experiments/legacy/
```

Move old router/Pāṭala-specific code there or delete it.

---

# 24. Files to retire from the production path

Do not keep five public APIs.

Retire/archive:

```text
app/api.py
app/api_v2.py
app/api_v3.py
app/api_hot.py
legacy router.py
legacy routing.py
layer_recommend.py
old normalize.py canonical path
old db.py
JSON history pipeline
snapshot-driven MCP
```

Keep only one V1 API.

Rewrite:

```text
README.md
VISION.md
GOALS.md
AGENTS.md
```

around LLM Deals rather than Garglecum/Pāṭala.

Pāṭala can consume LLM Deals later.

---

# 25. Build checkpoints

## CP0 — Repository truth reset

Gate:

```text
one API
one MCP
one DB layer
one scheduler
one event log
no live DB in Git
CI green
```

## CP1 — Evidence kernel

Gate:

```text
100% canonical claims link to retained artifacts + evidence
```

## CP2 — Exact identity

Gate:

```text
no sibling-variant inheritance
cross-provider same-model projection reproducible
```

## CP3 — Deal lifecycle

Gate:

```text
fixture transitions generate correct append-only events
```

## CP4 — Flagship sources

Gold sources:

```text
OpenCode Go
OpenCode Zen
OpenRouter
models.dev
Artificial Analysis
SenseNova
one Chinese provider
one regional provider
```

Gate:

```text
manual/live spot-check exact match
```

## CP5 — Trust API

Gate:

```text
REST and MCP return same objects
freshness honest
verification claim-level
activation/terms exposed
```

## CP6 — Deal radar

Gate:

```text
/deals excludes ordinary catalog entries
hot/expiring/new classifications correct
```

## CP7 — Autonomous curation

Gate:

```text
Hermes discovers a new lead
finds primary source
produces candidate bundle
deterministic validator commits it
no direct agent DB write
```

---

# 26. Master implementation prompt for the coding agent

```text
You are the lead infrastructure engineer for prx0r/dell, which is becoming LLM Deals.

Read the repository before editing. The product is no longer primarily a router or a Pāṭala-specific model recommender. The V1 mission is:

“LLM Deals provides live, verifiable, machine-readable data about LLM inference opportunities, with every important claim traceable to evidence and every uncertainty represented honestly.”

Your job is to harden the repository into a canonical inference-market data layer. Do NOT add new providers or flashy features until the truth kernel is complete.

NON-NEGOTIABLE PRINCIPLES

1. Observations are not claims.
2. Claims are not current state.
3. Current state is not history.
4. Derived scores are not truth.
5. Unknown is never converted into zero, false, global, allowed, permanent, or verified.
6. Every canonical claim must reference retained evidence.
7. Every source artifact required for replay must be retained content-addressably.
8. Model identity must be explicit. Never merge or inherit facts across similar model names without a typed identity assertion.
9. Benchmarks never transfer between sibling variants.
10. Provider-offering fields never transfer across providers.
11. Legal consent/payment/KYC steps are human-required.
12. Hermes/LLMs may propose candidates; deterministic code commits canonical state.
13. No live runtime DB/logs/snapshots in Git.
14. One application service powers REST, MCP and site/export.
15. No router/proxy work in V1.

FIRST, AUDIT CURRENT MASTER

Explicitly verify and document these known problems before changing code:
- latest enrichment commits changed only data/llmdeals.sqlite3 and are not reproducible from committed code;
- REST reads SQLite while MCP reads snapshots;
- web reads an obsolete absolute canonical-models.json path;
- claims/evidence/verification tables are not the main ingest path;
- raw source artifacts are not retained;
- only the first observation of multi-observation sources is persisted;
- discovery still uses RAM registry scheduling instead of durable next_check_at;
- source_diff/deal_events are not one canonical lifecycle path;
- free and other boolean states conflate unknown with false;
- offer ID generation still encodes “global” despite unknown region;
- rich adapter field names do not round-trip consistently;
- COALESCE upserts can preserve stale old facts;
- freshness is currently fabricated as non-stale;
- URL/source authority is being confused with claim verification;
- /deals/live is not a real deal lifecycle query;
- several declared filters are not applied;
- MCP still contains unknown-price-as-zero logic;
- scoring mixes incompatible dimensions and inserts heuristics as measurements;
- free qualification collapses quota windows and defaults duration incorrectly;
- README/VISION still describe the old Garglecum/Pāṭala scope;
- generated DB/logs are committed;
- there is no visible CI gate on master.

Then implement the target architecture in checkpoint order.

CP0 REPOSITORY RESET
- Create a clean llmdeals package structure.
- Introduce versioned SQL migrations.
- Remove the live SQLite DB and generated snapshots/logs/history from tracking.
- Keep small gold fixtures only.
- Add CI.
- Archive old API/router/Pāṭala-specific production paths under experiments/legacy.
- Rewrite README/VISION/GOALS to the new mission.
- Expose exactly one FastAPI app.

CP1 EVIDENCE KERNEL
Implement:
Source
Artifact
Observation
Claim
Evidence
Adjudication
VerificationCheck

Artifacts must be content-addressed. Observation must preserve every fetch/page, HTTP status, headers and completeness. Parser output must be CandidateClaim objects. Canonical claims cannot exist without evidence.

Build replay tests proving:
artifact → parser → exact claim.

CP2 IDENTITY
Implement:
ModelFamily
ModelVersion
ModelAlias
ProviderOffering
IdentityAssertion

Relationship enum:
EXACT_SAME_MODEL
EXPLICIT_PROVIDER_ALIAS
SAME_MODEL_DIFFERENT_PROVIDER
SIBLING_VARIANT
MODEL_FAMILY
UNKNOWN

Build a field transfer policy. Never transfer benchmarks or provider-specific capabilities from sibling variants. Delete any one-off DB enrichment that cannot be recreated.

CP3 COMMERCIAL + TEMPORAL
Implement:
CommercialPlan
CommercialOffer
QuotaRule
EligibilityRule
Deal
DealEvent

Represent quota windows exactly.
Represent free/paid/unknown explicitly.
Represent expiry as exact/date-only/rolling/reset/unknown.
No fake timestamp precision.

CP4 INGESTION
Pipeline:
scheduler → fetch → artifact → observation → candidate claims → identity → evidence validation → adjudication → events → projection.

Persist all observations.
Do not use first-wins offer dedupe.
Do not use COALESCE upserts as truth semantics.
A partial fetch may not remove existing deals.
A failed fetch may not expire anything.

CP5 SERVICE CONVERGENCE
Create DealService and CatalogService.
REST, MCP and site/export call them.
Delete direct snapshot readers.
Implement stable response schemas and cursor-based events.

CP6 VERIFICATION
Status ladder:
LEAD
SOURCE_FETCHED
CLAIM_EXTRACTED
PRIMARY_EVIDENCE
PRIMARY_CORROBORATED
ENDPOINT_REACHABLE
MODEL_LISTED
INFERENCE_SUCCEEDED
DEAL_CONDITION_CONFIRMED

Never call 401/403 “deal verified”.
Verification checks append evidence; they do not rewrite history.

CP7 ACTIVATION + TERMS
Implement versioned ActivationRecipe/ActivationStep and TermsSnapshot/TermsClaim.
Actor enum:
HUMAN_REQUIRED
AGENT_SAFE
AGENT_OPTIONAL
SYSTEM

Terms claims are tri-state/conditional with evidence.

CP8 DEAL RADAR
Catalog and deals are separate.
Only unusual opportunities enter /deals.
Implement deal types and versioned Opportunity/Confidence/Urgency/Access scores.
Do not publish speculative “workhorse” rankings as facts.

CP9 HERMES
Use Hermes as event-driven research staff:
scout
change investigator
claim verifier
identity resolver
terms auditor
activation author
regional scout
audit agent

No Hermes agent may directly mutate canonical tables.
Hermes outputs typed candidate bundles to a deterministic commit API.

TESTING
Implement real tests, not count/smoke theatre:
- fixture replay
- mutation tests
- round-trip DB/service/API/MCP
- partial fetch
- identity false-positive tests
- temporal precision
- lifecycle transitions
- random claim evidence audit
- MCP/REST full semantic parity

Create flagship gold fixtures for OpenCode Go and OpenCode Zen.

RELEASE GATE
Do not label the system V1 until:
- 100 randomly sampled canonical claims replay from retained evidence;
- no unsupported global eligibility exists;
- no unknown price is interpreted as free;
- quota semantics round-trip unchanged;
- no sibling variant benchmark inheritance exists;
- REST/MCP objects are identical;
- 20 current flagship deals manually spot-check against primary sources;
- CI is required and green.

Work autonomously. Commit checkpoint-sized changes. After each checkpoint, run the relevant tests and write a short evidence report describing exactly what is now proven and what remains unproven. Do not claim completion from file existence or endpoint 200 responses.
```

---

# 27. Prompt — identity + enrichment specialist

```text
Act as the identity/provenance specialist for LLM Deals.

The current repo recently enriched fields across provider records by normalized model names and committed the resulting SQLite DB. That mechanism is unsafe and irreproducible.

Build a conservative identity graph.

Required entities:
ModelFamily
ModelVersion
ModelAlias
ProviderModelRef
IdentityAssertion

Required relations:
EXACT_SAME_MODEL
EXPLICIT_PROVIDER_ALIAS
SAME_MODEL_DIFFERENT_PROVIDER
SIBLING_VARIANT
MODEL_FAMILY
UNKNOWN

Build resolver output:
relationship
confidence
supporting claims/evidence
resolver version

Rules:
- Similar strings never automatically prove exact identity.
- “Pro”, “Flash”, “Turbo”, dated snapshots, preview, instruct, thinking, vision, coder, omni and quantized variants are distinct unless primary evidence proves aliasing.
- Never transfer benchmarks from sibling variants.
- Never transfer provider-specific context caps, endpoint compatibility, tool support, latency, quota or price.
- Exact same model across providers may share model-native properties only when the source property is model-native and no offering override exists.
- Every projected field must retain provenance to the source claim and identity assertion.
- Derived enrichment must be rebuildable from scratch.

Create adversarial tests:
MiMo V2.5 vs MiMo V2.5 Pro
DeepSeek Flash vs Pro
Qwen snapshot vs latest alias
preview vs release
provider-prefixed aliases
same model name from different developers

The test suite must deliberately contain near-match traps and prove the resolver refuses unsafe merges.

Finally, rebuild the current enrichment from committed logic and compare the result to the existing DB. Emit a report of every field whose old inherited value cannot be justified.
```

---

# 28. Prompt — evidence/lifecycle specialist

```text
Act as the evidence and temporal-integrity engineer for LLM Deals.

Replace snapshot-first ingestion with:
Source → Artifact → Observation → Claim → Evidence → Adjudication → DealEvent → Projection.

Requirements:

ARTIFACT
- immutable
- SHA-256 content addressed
- compressed optional
- stores URI, content type, encoding, byte size

OBSERVATION
- one row per HTTP/API response/page
- source ID
- artifact ID
- fetched time
- status
- request metadata
- response headers
- completeness state

CLAIM
- typed subject/predicate/value
- valid time
- observation ID
- extractor version
- extraction confidence

EVIDENCE
- artifact ID
- selector type
- selector/JSON pointer/XPath/byte range
- excerpt

ADJUDICATION
- selects currently supported claim without deleting alternatives
- records why

EVENT
- append-only lifecycle event
- must reference supporting claim/evidence

PROJECTION
- reconstruct current deal/offering state from claims/events
- must be rebuildable

Temporal types:
EXACT_INSTANT
DATE_ONLY
ROLLING_FROM_SIGNUP
ROLLING_FROM_ACTIVATION
QUOTA_WINDOW
CALENDAR_RESET
UNTIL_CREDITS_EXHAUSTED
UNTIL_PUBLIC_BETA_ENDS
UNKNOWN

Build mutation fixtures proving:
free false→true = DEAL/FREE_STARTED
free true→false = FREE_ENDED
2x→1x = PROMO_CHANGED/ENDED
quota changes preserve window units
date-only does not become midnight UTC
failed fetch creates no expiry
partial pagination creates no removals
temporary missing DOM element creates STALE_SUSPECTED, not EXPIRED

No canonical fact may exist without retrievable evidence.
```

---

# 29. Prompt — API/MCP/site convergence specialist

```text
Act as the public-contract engineer for LLM Deals.

The current repository has multiple APIs and independent snapshot-reading MCP/site logic. Replace this with one domain service.

Create:
CatalogService
DealService
EvidenceService
EventService

All storage queries live behind repositories.
REST, MCP and static export call service methods.
No UI/MCP code opens SQLite or snapshots directly.

Public REST:

/v1/models
/v1/models/{id}
/v1/providers
/v1/providers/{id}
/v1/offerings
/v1/offerings/{id}
/v1/prices
/v1/free

/v1/deals
/v1/deals/{id}
/v1/deals/hot
/v1/deals/expiring
/v1/deals/new

/v1/deals/{id}/evidence
/v1/deals/{id}/verification
/v1/deals/{id}/activation
/v1/deals/{id}/terms
/v1/deals/{id}/history

/v1/events?since=cursor
/v1/compare?model=id

MCP:
search_deals
get_deal
compare_model_offers
get_recent_changes
get_activation_recipe
get_evidence

Rules:
- no unused query parameters
- unknown price cannot pass max-price filtering
- output cost is not treated as zero when unknown
- “live” requires active lifecycle state, not merely an existing offer
- freshness state is derived from source runtime
- verification state comes from verification checks
- no source-domain heuristic creates “verified”
- CORS/read API is separate from authenticated internal commit/admin API

Generate OpenAPI.
Create shared contract tests where the same service query is invoked via REST and MCP and the semantic payloads must deep-equal.

Delete or archive api.py/api_v2.py/api_v3.py/api_hot.py and all snapshot-driven MCP logic.
```

---

# 30. Prompt — Hermes autonomous curator

```text
You are Hermes operating as LLM Deals’ autonomous research workforce.

You are NOT a database editor.

Your outputs are typed candidate bundles.

When a source changes:

1. Read the deterministic diff.
2. Inspect the new and previous artifacts.
3. Decide whether the change is commercially relevant.
4. Ignore navigation/layout/cosmetic changes.
5. Identify exact candidate claims:
   subject
   predicate
   value
   units
   temporal semantics
   eligibility
6. Find primary official corroboration where possible.
7. Preserve exact evidence selectors/excerpts.
8. Resolve model/provider identity conservatively.
9. If identity is uncertain, mark it unresolved.
10. Never invent region, rate limit, context, price, expiry, automation allowance or permanence.
11. Never treat a community post as primary verification.
12. Never accept terms, make payments, perform KYC, or create accounts on a user’s behalf.
13. Build/update activation recipe only from current official setup documentation.
14. Return confidence and unresolved questions.

Candidate output schema:

{
  lead_id,
  source_ids,
  candidate_subjects,
  candidate_claims: [
    {
      subject_ref,
      predicate,
      value,
      units,
      temporal,
      evidence,
      confidence
    }
  ],
  identity_assertions,
  verification_recommendations,
  activation_recipe_candidate,
  terms_claim_candidates,
  unresolved,
  recommendation: COMMIT_CANDIDATE | NEEDS_REVIEW | REJECT
}

If a primary source cannot be found, keep the object as community-reported/unverified.

Your objective is not to maximize deal count.
Your objective is to maximize useful discoveries while preserving epistemic integrity.
```

---

# 31. Prompt — final adversarial release auditor

```text
Act as a hostile external auditor.

Assume LLM Deals is about to be consumed by autonomous routers that may spend real money based on its API.

Try to prove the dataset cannot be trusted.

Randomly sample:
- 25 free claims
- 25 prices
- 15 quota claims
- 10 promotions
- 10 expiry claims
- 5 eligibility/terms claims
- 10 identity/enrichment claims

For each:
1. locate canonical claim;
2. retrieve evidence;
3. retrieve immutable artifact;
4. replay extractor;
5. verify identity;
6. compare projection;
7. independently inspect the current primary source where appropriate;
8. classify:
   EXACT
   STALE
   UNSUPPORTED
   WRONG_IDENTITY
   WRONG_UNIT
   WRONG_TIME
   WRONG_ELIGIBILITY
   UNREPRODUCIBLE

Also attack:
- unknown→zero
- unknown→global
- unknown→allowed
- 401→verified
- partial fetch→removal
- source failure→expiry
- sibling variant inheritance
- quota-window normalization
- date-only timestamp fabrication
- MCP/REST divergence
- stale runtime state committed to Git

Fail release on any unsupported canonical claim in the sampled set.

Produce:
audit.json
audit.md
counterexamples/
reproduction commands

Do not praise the system. Your job is to break it.
```

---

# 32. Final stop condition

The project is finished enough for public V1 when it is boring.

A downstream agent asks:

```text
“What unusually good coding inference deals are live, verified, usable in my region, with at least 128K context?”
```

LLM Deals returns a small set where every field can answer:

```text
What exactly does this mean?
Who asserted it?
Where is the evidence?
When was it observed?
Is it current?
How certain are we?
What are the setup steps?
What restrictions apply?
What changed historically?
```

At that point you have the valuable product.

Do not build the router until this layer is trusted.
