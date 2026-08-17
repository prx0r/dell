I inspected `prx0r/garglecum` properly. The important finding is that the existing build is already a solid **model/routing plane**: canonical normalization, measured quality, quota-aware routing, API, MCP and Astro are present, with the dev plan reporting 65 passing tests.

The architectural problem is that `normalize.py` still collapses sources into a model-keyed latest state using source overwrites. That cannot represent **MiMo@OpenCode vs MiMo@Nous vs MiMo@OpenRouter simultaneously**, much less preserve a temporary 2× promotion historically.  Also, current `/deals` is essentially a free-model projection rather than a temporal promotion engine.

I tried to commit the spec directly and then as a GitHub issue, but the connected GitHub integration is currently returning **403 on writes** despite read access. So this is the exact agent build I would put into the repo as `DEAL-RADAR-V2-PROMO-INTELLIGENCE-BUILD.md`."

# DEAL RADAR V2 — Promotion Intelligence + Inference Arbitrage Build

**Implementation contract for the coding agent**

## Mission

Turn the existing deal-radar from:

**“What models exist, what do they cost now, and which looks good?”**

into:

**“What exact inference offers exist right now, what changed, what is temporarily mispriced, how long will it last, and which offer gives the most useful intelligence for this workload?”**

Do **not** rebuild the existing application.

Preserve:

* `app/normalize.py`
* `app/benchmark_quality.py`
* `app/quality.py`
* `app/routing.py`
* `app/tensions.py`
* `app/task_ranking.py`
* `app/rate_limits.py`
* `app/free_limits.py`
* `app/api.py`
* `mcp/server.py`
* `web/`
* existing tests
* `canonical-models.json`

V2 adds a **temporal offer/promotion plane beside V1**.

The core distinction becomes:

```text
MODEL IDENTITY
    !=
PROVIDER OFFER
    !=
OFFER SNAPSHOT
    !=
PROMOTION EVENT
    !=
SUBSCRIPTION PLAN
    !=
ROUTING DECISION
```

This is mandatory.

A model such as:

```text
xiaomi/mimo-v2.5
```

may simultaneously have:

```text
OpenCode Go / MiMo V2.5
Nous Portal / MiMo V2.5
OpenRouter / MiMo V2.5
Xiaomi direct / MiMo V2.5
DeepInfra / MiMo V2.5
```

These are not duplicates.

They are separate economic offers for the same underlying model.

---

# 1. Questions the finished system must answer

```text
What are the hottest LLM deals right now?

What changed in the last 24 hours?

What became free today?

Which promotion ends soon?

What is 50%+ cheaper than normal?

Which providers have 2x/3x/etc usage multipliers?

Does anything beat MiMo V2.5 on OpenCode Go
for cache-heavy coding-agent work?

Which provider currently has the cheapest MiMo?

Which offer is best for bulk Sanskrit translation?

Which free model actually has enough quota for 5,000 jobs/day?

Is Nous giving a genuine discount or is this normal market price?

What was the cheapest route for model X last month?

Did this promotion actually disappear,
or did our parser break?

Where did this deal come from?

Is it an official price, a derived price drop,
or just something someone mentioned on Reddit?

What effective price do I pay if I only use 20%
of a subscription allowance?
```

---

# 2. V2 invariants

### Observation is permanent

Do not overwrite historical source observations.

### Model != offer

Model identity is permanent-ish.

Offer identity describes how someone can buy access to it.

### Promotion != price

A provider can announce:

```text
2x usage
```

without modifying its visible token rates.

That still materially changes economics.

Therefore store the multiplier independently.

### Unknown != free

Missing input/output prices are `NULL`.

Never:

```text
missing price -> 0 -> free model
```

### Every deal has evidence

Every deal must eventually trace to:

```text
source
URL
fetch time
bounded evidence text
content hash
parser/extraction result
```

### Observed != inferred

Store:

```text
fact_basis:
    observed
    derived
    community_lead
```

Example:

```text
Observed:
"GPT 5.6 Luna (2x usage)"

Derived:
Yesterday multiplier=2.
Today clean official page has multiplier=1.
Therefore promotion probably ended.
```

### Source failure != promotion ending

If OpenCode suddenly returns an error page:

```text
DO NOT MARK EVERY OPENCODE PROMOTION ENDED.
```

Mark:

```text
source degraded
last state stale
```

### Subscription economics require utilization

A nominal:

```text
$10 subscription
$60 included usage
```

is not universally equivalent to paying one-sixth of API pricing.

It approaches that only if the allowance is actually consumed.

Expose the assumption.

---

# 3. Add a temporal SQLite kernel

Keep JSON as the lightweight V1 projection.

Add:

```text
app/db.py
app/schema.sql
app/migrations/
    001_v2.sql

data/deal-radar.sqlite3
```

Use stdlib:

```python
sqlite3
```

Configure:

```sql
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;
PRAGMA synchronous=NORMAL;
```

No Postgres.

No Redis.

No Kafka.

This workload absolutely does not require them.

---

# 4. Canonical V2 schema

## models

Stable underlying model identity.

```sql
CREATE TABLE models (
    model_id TEXT PRIMARY KEY,
    canonical_name TEXT NOT NULL,
    author TEXT,
    family TEXT,

    context_tokens INTEGER,
    max_output_tokens INTEGER,

    reasoning INTEGER,
    tool_call INTEGER,
    structured_output INTEGER,
    open_weights INTEGER,

    metadata_json TEXT NOT NULL DEFAULT '{}',

    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

Example:

```text
model_id:
xiaomi/mimo-v2.5
```

There should be ONE underlying MiMo V2.5 identity.

---

## model_aliases

Provider naming is chaotic.

```sql
CREATE TABLE model_aliases (
    source TEXT NOT NULL,
    alias TEXT NOT NULL,

    model_id TEXT NOT NULL
        REFERENCES models(model_id),

    confidence REAL NOT NULL,
    method TEXT NOT NULL,

    PRIMARY KEY(source, alias)
);
```

Supported methods:

```text
exact
canonical_slug
manual
normalized_exact
fuzzy_reviewed
```

Resolver must understand:

```text
MiMo V2.5
MiMo-V2.5
Xiaomi: MiMo-V2.5
xiaomi/mimo-v2.5
```

but NEVER merge:

```text
MiMo V2.5
MiMo V2.5 Pro
```

or:

```text
GPT 5.6 Luna
GPT 5.6 Luna Pro
```

or:

```text
Qwen3.7 Plus
Qwen3.7 Max
```

Fuzzy matches are candidates.

They do not automatically join economic records.

---

# 5. Providers are separate from model authors

Add:

```sql
CREATE TABLE providers (
    provider_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    kind TEXT NOT NULL,

    homepage TEXT,
    api_base TEXT,

    metadata_json TEXT NOT NULL DEFAULT '{}'
);
```

Example provider IDs:

```text
openrouter
opencode-go
opencode-zen
nous-portal
xiaomi-mimo
minimax-token-plan
zai-coding-plan
deepseek-direct
vercel-ai-gateway
upstage
siliconflow
cloudflare-workers-ai
deepinfra
fireworks
together
groq
cerebras
```

Critical fix:

```text
model author != inference provider
```

Current model records often blur these.

V2 must not.

---

# 6. Offer identity

Add:

```sql
CREATE TABLE offers (
    offer_id TEXT PRIMARY KEY,

    provider_id TEXT NOT NULL
        REFERENCES providers(provider_id),

    model_id TEXT
        REFERENCES models(model_id),

    provider_model_slug TEXT,

    plan_id TEXT,
    offer_kind TEXT NOT NULL,
    region TEXT,

    currency TEXT NOT NULL DEFAULT 'USD',
    active INTEGER NOT NULL DEFAULT 1,

    metadata_json TEXT NOT NULL DEFAULT '{}',

    created_at TEXT NOT NULL
);
```

Offer kinds:

```text
metered_api
provider_route
subscription_allowance
credit_pack
free_tier
temporary_free
off_peak
batch
```

Examples:

```text
opencode-go:mimo-v2.5:go
nous-portal:mimo-v2.5:metered
openrouter:mimo-v2.5:default
xiaomi:mimo-v2.5:token-plan-lite
```

---

# 7. Source observations

Add:

```sql
CREATE TABLE source_observations (
    observation_id INTEGER PRIMARY KEY AUTOINCREMENT,

    source_id TEXT NOT NULL,
    source_type TEXT NOT NULL,
    url TEXT NOT NULL,

    fetched_at TEXT NOT NULL,
    http_status INTEGER,

    etag TEXT,
    last_modified TEXT,

    content_sha256 TEXT,
    normalized_text_sha256 TEXT,

    extraction_status TEXT NOT NULL,

    evidence_text TEXT,

    metadata_json TEXT NOT NULL DEFAULT '{}'
);
```

Do not archive megabytes of duplicate HTML forever.

Normally retain:

```text
URL
timestamp
HTTP metadata
content hash
normalized hash
relevant evidence region
parsed result
```

For especially valuable official pages, optionally keep compressed changed bodies.

---

# 8. Append-only offer snapshots

```sql
CREATE TABLE offer_snapshots (
    snapshot_id INTEGER PRIMARY KEY AUTOINCREMENT,

    offer_id TEXT NOT NULL
        REFERENCES offers(offer_id),

    observed_at TEXT NOT NULL,

    input_per_m REAL,
    output_per_m REAL,
    cache_read_per_m REAL,
    cache_write_per_m REAL,

    subscription_usd REAL,
    included_nominal_usd REAL,

    credits_included REAL,
    usage_multiplier REAL,

    requests_5h INTEGER,
    requests_day INTEGER,
    requests_week INTEGER,
    requests_month INTEGER,

    tokens_day INTEGER,

    context_tokens INTEGER,
    max_output_tokens INTEGER,

    free INTEGER NOT NULL DEFAULT 0,

    starts_at TEXT,
    expires_at TEXT,

    source_observation_id INTEGER NOT NULL,

    parsed_json TEXT NOT NULL DEFAULT '{}'
);
```

Important:

```text
usage_multiplier = 2
```

must remain explicit.

Do NOT transform it during ingestion into some fake token price.

---

# 9. Promotion events

Add:

```sql
CREATE TABLE promotion_events (
    event_id TEXT PRIMARY KEY,

    offer_id TEXT,
    model_id TEXT,

    provider_id TEXT NOT NULL,

    event_type TEXT NOT NULL,
    status TEXT NOT NULL,
    fact_basis TEXT NOT NULL,

    discount_fraction REAL,
    usage_multiplier REAL,

    previous_value REAL,
    current_value REAL,

    title TEXT NOT NULL,
    summary TEXT,

    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,

    starts_at TEXT,
    expires_at TEXT,

    confidence REAL NOT NULL,

    source_observation_id INTEGER NOT NULL,

    corroboration_count INTEGER
        NOT NULL DEFAULT 0,

    metadata_json TEXT NOT NULL DEFAULT '{}'
);
```

Event types:

```text
price_drop
price_increase

usage_multiplier

free_started
free_ended

promo_started
promo_extended
promo_ended

quota_increase
quota_decrease

subscription_subsidy
launch_price
off_peak_discount

context_increase

model_added
model_removed
```

---

# 10. Community leads remain quarantined

Add:

```sql
CREATE TABLE community_leads (
    lead_id TEXT PRIMARY KEY,

    source TEXT NOT NULL,
    external_id TEXT NOT NULL,

    url TEXT,
    title TEXT,
    body_excerpt TEXT,
    author TEXT,

    score REAL,

    published_at TEXT,
    discovered_at TEXT NOT NULL,

    matched_provider TEXT,
    matched_model TEXT,

    promo_signal REAL,

    verification_status TEXT
        NOT NULL DEFAULT 'unverified',

    metadata_json TEXT NOT NULL DEFAULT '{}'
);
```

Examples:

```text
HN:
"DeepSeek is 90% off on Nous"

Reddit:
"OpenCode Flash back to 2x"

blog:
"New model free for one week"
```

These trigger verification.

They do not establish price truth.

---

# 11. Preserve `canonical-models.json`

Do NOT make SQLite replace everything immediately.

Add:

```text
app/materialize.py
```

Pipeline:

```text
normalize.py
    |
    v
current model metadata
    |
    v
models table

offers/events
    |
    v
V2 projections

    |
    +--> existing canonical-models.json
    |
    +--> current-deals.json
    |
    +--> current-workhorses.json
    |
    +--> recent-changes.json
```

V1 continues functioning throughout development.

---

# 12. Source adapter architecture

Create:

```text
app/sources/
    __init__.py
    base.py
    registry.py

    rss.py

    models_dev.py
    artificial_analysis.py
    openrouter.py

    opencode.py
    nous.py
    provider_pages.py

    hackernews.py
    reddit.py
```

Interface:

```python
@dataclass
class Observation:
    source_id: str
    source_type: str
    url: str
    fetched_at: str

    status: int | None

    text: str
    sha256: str

    etag: str | None = None
    last_modified: str | None = None

    metadata: dict = field(default_factory=dict)


class SourceAdapter(Protocol):
    source_id: str
    cadence_minutes: int

    def fetch(self) -> list[Observation]:
        ...

    def extract(
        self,
        observation: Observation
    ) -> list[dict]:
        ...
```

Fetch and extraction MUST remain separate.

Why:

```text
network test != parser test
```

All parsing tests should work entirely from saved fixtures.

---

# 13. Source registry

Create one declarative registry.

Do not scatter URLs and cadence constants across fifteen files.

Conceptually:

```python
SOURCES = {
    "models-dev": {...},
    "artificial-analysis": {...},
    "openrouter-models": {...},

    "opencode-go": {...},
    "opencode-go-docs": {...},
    "opencode-data": {...},

    "nous-portal": {...},
    "nous-blog": {...},

    "vercel-changelog": {...},

    "xiaomi-mimo": {...},
    "minimax": {...},
    "zai": {...},
    "deepseek": {...},

    ...
}
```

---

# 14. Structured baseline sources

## models.dev

Use as:

```text
model identity
context
capabilities
modalities
ordinary provider metadata
```

Do NOT rely on it for transient promotion discovery.

## Artificial Analysis

Use as:

```text
quality oracle
coding/agent capability
intelligence
throughput/latency where available
market pricing reference
```

Refresh once per day.

Persist last successful result.

Never make `/recommend` hit AA over the network synchronously.

## OpenRouter

Use model API for:

```text
current catalog
prices
free variants
context
expiration metadata
```

Detect:

```text
new model
removed model
new free route
price change
provider-route outlier
```

Do not call every model's detailed provider endpoint every poll.

Expand only:

```text
new models
changed models
active deals
top candidates
```

---

# 15. OpenCode Go adapter — implement this FIRST

This is the highest priority because it proves the exact missing capability.

Current OpenCode Go explicitly publishes plan economics, model-specific limits and temporary model labels such as `2x usage`; its docs also describe model-specific allowance economics. ([OpenCode][1])

Create:

```text
app/sources/opencode.py
```

Monitor official:

```text
Go landing page
Go documentation
OpenCode data page
```

Extract:

```text
model identity
literal multiplier label

subscription fee
first-month fee where relevant

model-specific nominal allowance

input price
output price
cache-read price
cache-write price

requests / 5h
requests / week
requests / month

provider-published typical token mix
```

Example extraction:

```json
{
  "provider": "opencode-go",
  "model_alias": "GPT 5.6 Luna",

  "offer_kind": "subscription_allowance",

  "subscription_usd": 10,
  "included_nominal_usd": 15,

  "usage_multiplier": 2,

  "requests_5h": 4100,

  "raw_label":
    "GPT 5.6 Luna (2x usage)"
}
```

Critical behavior:

```text
literal "2x usage"
    ->
observed multiplier=2
```

But:

```text
request estimate doubles
without explicit "2x"
    ->
derived economic change
NOT an observed literal multiplier
```

Keep the distinction.

---

# 16. OpenCode promo lifecycle

Fixture A:

```text
Luna (2x usage)
4100 requests/5h
```

Fixture B:

```text
Luna
2050 requests/5h
```

Expected result:

```text
snapshot A appended

promotion:
usage_multiplier=2
status=active

snapshot B appended

event:
promo_ended
2 -> 1
```

Exactly one ending event.

Now Fixture C:

```text
Cloudflare error
or
page template changed
or
parser extracts zero rows
```

Expected:

```text
source degraded

NO MULTIPLIER CHANGE
NO MASS PROMO ENDING
```

This test is mandatory.

---

# 17. Nous Portal adapter — implement SECOND

Nous is the second proving ground because its public Portal catalog itself exposes a large model catalog with live Portal pricing/free options, making it useful as a direct offer source rather than merely a social-media signal. ([Nous Portal][2])

Create:

```text
app/sources/nous.py
```

Ingest:

```text
model
Portal price
free state
subscription plan bonuses
catalog state
```

Then separately ingest official announcement/blog prose.

Example:

```text
DeepSeek V4 Flash
90% off
for seven days
```

Promotion:

```text
event_type:
promo_started

discount_fraction:
0.90

starts_at:
...

expires_at:
...
```

If catalog economics independently verify the discount:

```text
corroboration_count += 1
confidence increases
```

---

# 18. Independent blogs are lead generators

Generic RSS watcher should support high-signal niche blogs.

Create:

```text
app/sources/rss.py
```

Flow:

```text
GET homepage

discover:
<link
    rel="alternate"
    type="application/rss+xml">

or Atom

fetch only new posts

keyword prefilter

store lead

verify against provider
```

Prefilter:

```text
off
discount
free

promo
promotion

launch pricing
launch price

credits
bonus

2x
3x
5x

usage

limited time

until
through

extended
extension

off-peak

price cut
price drop
```

---

# 19. Hacker News adapter

Use HN's official public Firebase API rather than scraping; its documentation currently describes near-real-time public data and no rate limit. ([GitHub][3])

Watch new stories for:

```text
OpenCode
OpenRouter
Nous
DeepSeek
MiMo
MiniMax
GLM
Qwen
inference
API pricing
free LLM
discount
coding plan
```

Keep:

```text
last_seen_story_ids
```

No full historical crawl required.

HN creates:

```text
community_lead
```

not canonical pricing.

---

# 20. Reddit adapter

Optional.

Requires configured OAuth.

If credentials absent:

```text
source_status = disabled
```

not:

```text
source_status = failed
```

Use only as discovery.

Never trust a Reddit post's quoted token price without verifying it.

---

# 21. Provider/changelog layer

After OpenCode + Nous are proven, add:

```text
Vercel AI Gateway changelog

Xiaomi MiMo plans
MiniMax plans
Z.ai plans

DeepSeek pricing
DeepSeek off-peak

Upstage
SiliconFlow

Cloudflare Workers AI

Together
Fireworks
DeepInfra

Groq
Cerebras
```

Vercel is particularly useful because its changelog can contain explicit launch-pricing windows and expiration dates, which is exactly the type of temporal fact V2 needs to preserve. ([Vercel][4])

Every provider adapter requires:

```text
fixture
parser test
identity test
source-health behavior
```

No untested scraper sprawl.

---

# 22. Promotion extraction engine

Create:

```text
app/promo_extract.py
```

Start deterministic.

## Nx usage

```regex
(?i)\b(\d+(?:\.\d+)?)\s*[x×]\s*
(?:usage|credits?|allowance|quota)\b
```

Also:

```text
Model Name (2x usage)
```

## Percentage discount

```regex
(?i)\b(\d{1,3}(?:\.\d+)?)\s*%
\s*(?:off|discount(?:ed)?)\b
```

## Free windows

Parse:

```text
free for 7 days
free for seven days
free for one week

free until September 10

available free through August 18
```

## Extensions

Parse:

```text
extended
extended for another three days
promotion extended through DATE
```

## Price expressions

Parse:

```text
$0.03/M input
$0.12/M output

$0.03 per 1M

$20/month

$22 monthly credits
```

## Temporal information

Extract explicit:

```text
starts_at
expires_at
```

If not known:

```text
NULL
```

Do not guess.

---

# 23. Optional LLM extraction

Only add after deterministic parsing works.

Input:

```text
bounded relevant announcement paragraph
```

Output strict schema:

```json
{
  "is_inference_deal": true,

  "provider": "nous-portal",
  "model": "deepseek-v4-flash",

  "deal_type": "percent_discount",

  "discount_fraction": 0.9,

  "starts_at": null,
  "expires_at": "...",

  "confidence": 0.82,

  "evidence": "..."
}
```

Then validator checks:

```text
Does source contain the model?
Does source contain the number?
Does source contain the date?
```

Only then may it become a candidate.

The LLM NEVER directly writes canonical economics.

---

# 24. Semantic diff engine

Create:

```text
app/source_diff.py
```

Keep:

```text
raw SHA
normalized SHA
structured row hashes
```

Do not create deal events merely because the entire HTML document hash changed.

Parse old facts.

Parse new facts.

Compare facts.

Examples:

```text
input price:
0.20 -> 0.10
```

=> price drop.

```text
free:
false -> true
```

=> free_started.

```text
usage multiplier:
1 -> 2
```

=> usage_multiplier.

```text
2 -> 1
```

=> promo_ended.

```text
expires:
Aug 20 -> Aug 27
```

=> promo_extended.

---

# 25. Parser health

Create:

```text
app/source_health.py
```

Store:

```text
last_success
last_http_status

last_changed

consecutive_failures

records_extracted
previous_records_extracted

parser_health

fetch_latency_ms

etag
last_modified
```

Rules:

```text
HTTP 500:
source degraded

20 models -> 0:
parser suspicious

250 catalog models -> 4:
parser suspicious

same body hash + parser now zero:
parser bug

successful valid parse showing promo disappeared:
potential real promo end
```

This is essential for avoiding false alerts.

---

# 26. Economics engine

Create:

```text
app/economics.py
```

The central principle:

```text
DO NOT NORMALIZE WEIRD BILLING AWAY.
```

Represent it faithfully first.

Calculate later.

---

# 27. Metered API economics

Given workload:

```text
fresh_input
cached_input
cache_write
output
```

calculate:

```python
cost = (
    fresh_input / 1e6 * input_per_m
    + cached_input / 1e6 * cache_read_per_m
    + cache_write / 1e6 * cache_write_per_m
    + output / 1e6 * output_per_m
)
```

This matters enormously for agent workloads.

A cache-heavy agent and a translation worker should not see identical provider rankings.

---

# 28. Subscription economics

Represent:

```text
monthly fee

included nominal usage

5h limit
weekly limit
monthly limit

model-specific usage allowance

multiplier
```

Calculate:

```text
nominal API-equivalent task cost

fully utilized effective cost

effective cost at expected monthly volume

break-even utilization

remaining usable allowance

quota fit
```

Example:

```text
plan fee = $10

nominal allowance = $60

maximum subsidy factor = 6x
```

But:

```text
user consumes $6 nominal usage
```

then the real cost is:

```text
$10
```

not:

```text
$1
```

The engine must understand this.

---

# 29. Credit plan economics

Represent:

```text
purchase price
credits included

credits / fresh token
credits / cached token
credits / output token

time-window modifiers
```

Then:

```text
workload
 ->
credits
 ->
effective dollars
```

This makes Xiaomi-style token plans directly comparable with normal APIs and OpenCode subscriptions.

---

# 30. Off-peak tariffs

Represent conditionally:

```json
{
  "condition": "time_window",
  "timezone": "UTC",

  "windows": [
    ...
  ],

  "multiplier": 0.5
}
```

Expose:

```text
cost_now

normal_cost

cheapest_daily_cost

next_discount_window
```

---

# 31. Workload profiles

Create:

```text
app/workloads.py
```

Defaults:

```python
WORKLOADS = {

    "coding_agent_cache_heavy": {
        "fresh_input": 800,
        "cached_input": 70000,
        "cache_write": 0,
        "output": 300,

        "calls_per_day": 1000,
        "latency_sensitive": 0.4,
    },

    "coding_agent_general": {
        "fresh_input": 12000,
        "cached_input": 30000,
        "output": 3000,

        "calls_per_day": 200,
        "latency_sensitive": 0.6,
    },

    "bulk_translation": {
        "fresh_input": 10000,
        "cached_input": 4000,
        "output": 5000,

        "calls_per_day": 1000,
        "latency_sensitive": 0.1,
    },

    "long_context_agent": {
        "fresh_input": 5000,
        "cached_input": 150000,
        "output": 2500,

        "calls_per_day": 100,
        "latency_sensitive": 0.3,
    },

    "simple_extraction": {
        "fresh_input": 4000,
        "cached_input": 0,
        "output": 800,

        "calls_per_day": 5000,
        "latency_sensitive": 0.2,
    },
}
```

Allow API users to override every number.

Do not turn defaults into supposed scientific truths.

---

# 32. Quality plane

Add:

```text
app/quality_join.py
```

Priority:

```text
Artificial Analysis measured data

then

models.dev measured benchmark metadata

then

benchmark_quality.py

then

family estimate
```

Persist:

```text
score
task
benchmark
source
observed_at
```

Artificial Analysis' current free API allowance is 100 requests/day, which is ample for a cached daily refresh but should not be spent on request-time lookups. ([Artificial Analysis][5])

---

# 33. Market baseline

Create:

```text
app/deal_score.py
```

For each model/workload establish normal cost from:

```text
1. median credible current non-promo metered offers

else

2. historical 30-day median

else

3. official list price

else

4. unknown
```

Then:

```text
baseline_task_cost

current_task_cost

fully_utilized_task_cost

discount_fraction

arbitrage_factor
```

Formula:

```text
arbitrage_factor =
baseline_task_cost
/
current_task_cost
```

Interpretation:

```text
1.0 = ordinary

2.0 = roughly half normal cost

10.0 = roughly one-tenth normal cost
```

Free should display separately rather than literally using infinity everywhere.

---

# 34. Workhorse score

Do not hide the world in one unexplained scalar.

Expose components:

```text
quality

task_quality

cost_value

throughput

latency

context

quota_fit

cache_advantage

reliability

confidence

expiry_urgency
```

Possible workhorse weights:

```python
WORKHORSE_WEIGHTS = {

    "quality": 0.24,
    "task_quality": 0.18,

    "cost_value": 0.22,

    "quota_fit": 0.12,

    "throughput": 0.07,
    "context": 0.06,

    "cache_advantage": 0.05,

    "reliability": 0.04,
    "confidence": 0.02,
}
```

Return:

```text
workhorse_score

arbitrage_score

quality score

all component values
```

An agent should be able to disagree intelligently with the ranking.

---

# 35. Offer-aware routing

Create:

```text
app/routing_v2.py
```

Do NOT put subscription parsing inside `routing.py`.

Input:

```python
current_route_candidates(
    workload,
    task,
    now
)
```

Candidate:

```json
{
  "model_id":
    "xiaomi/mimo-v2.5",

  "offer_id":
    "opencode-go:mimo-v2.5:go",

  "provider":
    "opencode-go",

  "effective_task_cost":
    0.000066,

  "quality":
    38,

  "context":
    1000000,

  "quota_fit":
    1.0,

  "promo":
    true,

  "expires_at":
    null
}
```

Initially:

```text
V1 remains default.

V2 exposed with:
engine=v2
```

Only switch default once V2 parity tests pass on ordinary non-promo offers.

---

# 36. API V2

Preserve V1.

Add:

```text
GET /v2/deals

GET /v2/deals/{event_id}

GET /v2/changes?since=24h

GET /v2/expiring?within=7d

GET /v2/offers?model=<model>

GET /v2/offers/{offer_id}/history

GET /v2/workhorse
    ?task=coding
    &workload=coding_agent_cache_heavy

GET /v2/compare
    ?models=a,b
    &workload=...

GET /v2/sources

GET /v2/sources/{source_id}

GET /v2/alerts

POST /v2/refresh
```

---

# 37. `/v2/deals`

Filters:

```text
active

provider
model

min_discount

min_quality

deal_type

verified

sort:
    hot
    value
    discount
    quality
    expiring

limit
```

Compact row:

```json
{
  "id": "...",

  "model": "...",
  "provider": "...",

  "kind": "usage_multiplier",
  "headline": "2x usage",

  "effective_cost": 0.0001,
  "baseline_cost": 0.0006,

  "arbitrage": 6.0,

  "quality": 39,
  "context": 1000000,

  "quota_fit": 1.0,

  "confidence": 1.0,

  "expires_at": null,

  "basis":
    "official_pricing_page"
}
```

---

# 38. `/v2/changes`

This is one of the most valuable endpoints.

Return independent groups:

```text
new_deals

ended_deals

price_drops

price_increases

new_free

free_ended

usage_multiplier_changes

quota_changes

extensions

new_models

source_warnings

parser_warnings
```

Never mix:

```text
parser failed
```

with:

```text
promotion ended
```

---

# 39. MCP V2

Current MCP design is correct in one important respect: **few goal-oriented tools beat dozens of raw tools**.

Add at most:

```text
find_inference_deals(
    task,
    workload,
    min_quality
)

compare_inference_offers(
    model_or_models,
    workload
)

get_deal_changes(
    hours=24
)

explain_deal(
    deal_id
)
```

Potentially enrich:

```text
check_live_prices()
```

with V2 source health instead of making another health tool.

---

# 40. `find_inference_deals`

Return:

```text
model

provider
plan

effective workload cost

normal market baseline

arbitrage factor

quality

context

quota fit

throughput

active promotion

expiry

confidence

one-line explanation
```

Then an agent can actually ask:

```text
anything beat MiMo Go
for raw coding-agent work?
```

and get a meaningful answer.

---

# 41. `explain_deal`

Return:

```text
What changed?

What was observed?

What was derived?

Which workload was used?

Fresh tokens?
Cached tokens?
Output?

How was subscription utilization modeled?

What's normal market cost?

What's current effective cost?

What's the evidence source?

When was it first seen?

When was it last verified?

Does it expire?

Confidence?
```

This is crucial for trust.

---

# 42. Web V2

Keep Astro.

Keep zero-JS.

Do not build a giant SPA.

Add sections:

```text
HOT RIGHT NOW

NEW / CHANGED IN 24H

BEST WORKHORSES

FREE NOW

EXPIRING SOON

RECENTLY ENDED

SOURCE HEALTH
```

Current site is deliberately a lean agent-first static surface, so extend that architecture rather than replacing it.

Rows should show:

```text
model

provider

deal

quality

context

effective workhorse value

expiry

verified/source
```

---

# 43. Static machine-readable exports

Generate:

```text
web/public/deals.json

web/public/changes.json

web/public/workhorses.json
```

Useful even if API service is offline.

---

# 44. Fix current Astro path

Current `web/src/lib/models.js` hardcodes:

```text
/root/dealradar/data/canonical-models.json
```

which should be replaced while touching this system.

Use:

```text
DEALRADAR_DATA_DIR
```

or repo-relative resolution.

---

# 45. Poll scheduler

Create:

```text
app/poll.py
```

Registry-based cadence:

```text
models.dev:
24h

Artificial Analysis:
24h

OpenRouter:
6h

OpenCode Go:
2h

OpenCode docs/data:
4h

Nous Portal:
2h

provider pricing:
6h

RSS/blogs:
2h

Vercel changelog:
2h

Hacker News:
2h

Reddit:
6h optional

full market rebaseline:
24h
```

Command:

```bash
python -m app.poll --due
```

Also:

```bash
python -m app.poll --source opencode-go

python -m app.poll --source nous-portal

python -m app.poll --all

python -m app.poll --dry-run
```

One hourly cron is enough.

The registry decides what is due.

---

# 46. Discovery pipeline

Create:

```text
app/discovery.py
```

Exact flow:

```text
FETCH

-> save source observation

-> extract structured facts

-> resolve model/provider/offer identity

-> append offer snapshot

-> compare previous snapshot

-> generate candidate events

-> corroborate community leads

-> calculate economics

-> join quality

-> calculate deal/workhorse scores

-> update materialized projections

-> emit alerts

-> write poll report
```

---

# 47. Poll report

Generate:

```text
data/poll-report.json
```

Containing:

```text
started_at
completed_at

sources_due
sources_ok
sources_failed
sources_degraded

observations_created

offer_snapshots_created

events_created

events_ended

community_leads

verification_failures

parser_warnings

duration_ms
```

---

# 48. Alert engine

Create:

```text
app/alerts.py
```

Start with an internal event queue.

Do not immediately build Telegram/email/etc.

Alert when:

```text
price falls >=25%

promotion >=50%

usage multiplier >=2x

paid -> free

subscription subsidy >=2x

new offer enters top-10 workhorse list

new deal beats existing best
by >=15%

free offer exceeds configured
quality threshold

promotion expires within 48h

important promotion ends
```

Materialize:

```text
data/alerts.json
```

Then any external notifier can consume that later.

---

# 49. Provenance confidence

Initial priors:

```text
official machine-readable API:
1.00

official pricing/catalog page:
1.00

official changelog/blog:
0.95

official social announcement:
0.90

independent technical publication:
0.70

HN/Reddit/community:
0.40
```

Corroboration can raise confidence.

But:

```text
10 reposts of same claim
!=
10 independent confirmations
```

---

# 50. Unit-test fixtures

Create:

```text
tests/fixtures/

    opencode-go-2x.html

    opencode-go-normal.html

    opencode-go-parser-broken.html

    nous-90-off.html

    nous-free-model.html

    vercel-launch-pricing.html

    openrouter-models-before.json

    openrouter-models-after.json

    rss-deal.xml

    hn-story.json
```

Network access should never be required for unit tests.

---

# 51. Required identity tests

```text
MiMo aliases merge.

MiMo Pro stays separate.

Luna/Luna Pro stay separate.

Qwen Plus/Max stay separate.

provider prefix does not change
underlying model identity.

low-confidence fuzzy match
cannot attach canonical economics.
```

---

# 52. Required OpenCode tests

```text
Extract 2x multiplier.

Extract input/output/cache.

Extract model-specific allowance.

Extract request estimates.

2x -> normal
creates exactly one end event.

broken parser
creates ZERO ended events.

HTTP error
creates ZERO ended events.
```

---

# 53. Required promotion tests

```text
90% off

50% discount

free for one week

free for 7 days

free until date

available through date

promotion extension

usage multiplier

price increase

price decrease
```

---

# 54. Economics tests

Test:

```text
metered API

cache-heavy workload

subscription fully utilized

subscription 10% utilized

credit plan

off-peak pricing

batch pricing

free model with high quota

free model with insufficient quota
```

Critical expected behavior:

```text
free model
+
50 requests/day
+
need 5000/day
```

must NOT automatically beat a cheap paid workhorse.

---

# 55. History tests

```text
new snapshot appends

previous snapshot remains

unchanged poll does not spam
identical snapshots

price decrease produces event

price increase produces event

free begins

free ends

promo extends

promo ends

source dies
but promo does not falsely end
```

---

# 56. API/MCP tests

Prove:

```text
same model exposes multiple providers

/v2/deals returns only genuine events

/v2/changes separates source warnings

workhorse response includes
component scores

MCP compact response remains small

explain_deal includes math and evidence
```

Keep all existing tests green.

Before V2 becomes default:

```text
target >=100 deterministic tests
```

---

# 57. Data retention

Do not append identical full state every two hours forever.

Rules:

```text
Source observation:
metadata each fetch.

Full bounded evidence:
when page materially changed.

Offer snapshot:
only on economic/availability change.

Plus:
one heartbeat snapshot / 24h.

Promotion events:
retain permanently.

Community leads:
dedupe by external ID/URL/hash.
```

SQLite will remain tiny for years.

---

# 58. Performance

Do not overengineer.

Expected:

```text
<100 high-value sources

few thousand model/provider offers

hourly scheduler

years of historical changes
```

SQLite WAL is enough.

Optimize:

```text
ETag

If-Modified-Since

hash before expensive parsing

AA once/day

only expand OpenRouter endpoint
details for candidates

precompute rankings after poll
```

---

# 59. Current repo corrections to make alongside V2

### Provider conflation

Inference provider must become explicit and independent of model author.

### Source overwrite

Current `merged.update()` model projection cannot be the canonical offer store.

Keep it only for V1 projection.

### AA hot-path networking

Persist AA data at refresh instead of querying during request processing.

### Free semantics

Unknown zero price must stop appearing equivalent to genuine free access.

### Latency

Use measured:

```text
throughput_tps
latency_ms
```

where available.

Current reasoning/non-reasoning proxy remains only fallback.

### `/deals`

Legacy `/deals` stays for compatibility.

Real temporal promotions live at:

```text
/v2/deals
```

### Astro path

Remove `/root/dealradar`.

### Trivial cleanup

Remove duplicate unreachable:

```python
return out
return out
```

in `_from_hf_router` when normalize is next touched.

---

# 60. Implementation sequence

## CP0 — Freeze V1

Before editing:

```text
run all tests

record current SHA

record model count

record pass count

capture sample:
/models
/recommend
/deals
MCP pick_model
```

Gate:

```text
baseline reproducible
```

---

## CP1 — SQLite kernel

Implement:

```text
db.py
schema
migration runner
temp test DB
```

Functions:

```python
connect()

migrate()

upsert_model()

upsert_provider()

upsert_offer()

insert_observation()

insert_snapshot_if_changed()

previous_snapshot()

insert_event()
```

Gate:

```text
migration idempotent

snapshot history append-only
```

---

## CP2 — Strict identity

Implement:

```text
identity.py
import_legacy.py
```

Import existing canonical model DB into `models`.

Do NOT alter existing JSON.

Gate:

```text
base/Pro variants remain correct
```

---

## CP3 — Generic sources

Implement:

```text
base adapter

models.dev

OpenRouter

AA cache
```

Gate:

```text
multiple provider offers survive

unchanged poll does not duplicate
economic snapshots
```

---

## CP4 — OpenCode Go

Highest-priority checkpoint.

Implement complete OpenCode parser and transition tests.

Gate:

```text
2x appearing
works

2x disappearing
works

parser failure
does not create false deal changes
```

Do not proceed to twenty other scrapers before this passes.

---

## CP5 — Nous Portal

Second proving ground.

Gate:

```text
same model simultaneously has:

OpenCode offer
Nous offer
OpenRouter offer

and none overwrite each other
```

Prove:

```text
free promo

percentage promo

extension
```

---

## CP6 — RSS/blog/HN discovery

Implement:

```text
generic feed discovery

keyword prefilter

HN ingestion

optional Reddit
```

Gate:

```text
community lead
cannot directly modify canonical price
```

---

## CP7 — Event engine

Implement deterministic:

```text
starts
ends
extensions
price movements
quota changes
multipliers
free-state changes
```

Event IDs deterministic.

No duplicate notifications.

---

## CP8 — Economics

Implement all billing models.

Table-driven math tests.

Gate:

```text
same underlying model
can have different effective costs
depending on workload
```

---

## CP9 — Market baseline + workhorse

Implement:

```text
normal market baseline

arbitrage

workhorse ranking

current materialized projections
```

Gate:

```text
cache-heavy workload
selects differently from
non-cached translation workload
where economics warrant it
```

---

## CP10 — API V2

Add new endpoints.

Do not alter V1 contracts.

---

## CP11 — MCP V2

Add compact deal-oriented tools.

Gate question:

```text
Anything beat MiMo Go
for cache-heavy coding work?
```

Answer must contain:

```text
offer
provider
quality
cost
baseline
quota
context
promotion
evidence
```

not merely model family rankings.

---

## CP12 — Astro

Add current-deal surfaces.

Keep zero-JS.

Generate JSON snapshots.

---

## CP13 — Production polling + alerts

Implement:

```text
--due scheduler

source health

alert queue
```

Final adversarial test:

```text
OpenCode parser dies.

System does NOT send:
"all OpenCode deals ended."
```

---

## CP14 — Provider expansion

Only now expand aggressively.

One adapter at a time.

Every adapter requires:

```text
fixture
test
health handling
identity handling
```

---

# 61. Definition of “hot”

Default deal candidate must be:

```text
active

fresh enough

confidence >=0.7
```

and at least one:

```text
discount >=25%

multiplier >=2x

temporary free

subscription subsidy >=2x

enters top-10 workhorse value
```

Ranking should incorporate:

```text
value improvement

absolute quality

usable quota

context

confidence

freshness

expiry urgency
```

A useless tiny model that is 99% off must not automatically become #1.

---

# 62. Finished product architecture

```text
                  MODEL / QUALITY PLANE

        models.dev
        Artificial Analysis
        benchmark datasets

                  |
                  v

            MODEL IDENTITY

                  |
       -------------------------
       |                       |
       v                       v

 OFFER / PRICE PLANE      DISCOVERY PLANE

 APIs                     RSS
 pricing pages            changelogs
 catalogs                 blogs
 subscriptions            HN
 credit plans             Reddit
 free plans               announcements

       |                       |
       v                       v

 OFFER SNAPSHOTS          COMMUNITY LEADS
       |                       |
       -----------+------------
                   |
                   v

              EVENT ENGINE

                   |
                   v

       PROMOTION / PRICE / QUOTA HISTORY

                   |
                   v

             ECONOMICS ENGINE

      workload + utilization + cache mix

                   |
                   v

             MARKET BASELINE

                   |
                   v

       DEAL / WORKHORSE FRONTIERS

          |          |          |
          v          v          v

         API        MCP       Astro
```

---

# 63. The moat

The moat is **not**:

```text
a table of model token prices
```

There are already dozens of those.

The moat is:

> A historical, evidence-backed market of LLM inference offers that understands subscriptions, free quotas, token credits, caching, temporary multipliers, provider discounts, launch offers and expiration windows — and can tell an agent what intelligence is unusually cheap **right now for its exact workload**.

That is what garglecum should become.

---

# 64. Coding-agent rules

For every checkpoint:

```text
Inspect before editing.

Never rewrite an existing system just
because a cleaner abstraction is possible.

Preserve V1 compatibility.

Use fixtures for parsers.

No internet dependency in unit tests.

Run all old and new tests.

One coherent commit/checkpoint.

Report:
files changed
tests
results
remaining risks

Never guess a model alias.

Never guess a price.

Never treat missing as free.

Never bypass anti-bot controls.

A blocked source becomes degraded.

Do not claim a parser/source works
without fixture or live smoke evidence.
```

**First development session should complete CP0–CP4.**

Do not let the agent spend the first session adding 30 providers.

The first proof is:

```text
Can garglecum detect
OpenCode 2x appearing,
preserve it historically,
price it correctly,
and detect its disappearance
without confusing parser failure
with promo ending?
```

Once that works, Nous becomes proof #2.

Everything else is expansion.

The current repo architecture supports this cleanly: existing routing already understands cost, quota and task quality, so V2 should feed it **offer-specific economics** rather than replace it.  The OpenRouter API also exposes structured model pricing/catalog data, making it appropriate for the baseline layer while page/changelog adapters capture promotions the structured model layer misses. ([openrouter.ai][6])

[1]: https://dev.opencode.ai/go?utm_source=chatgpt.com "OpenCode Go | Low cost coding models for everyone"
[2]: https://portal.nousresearch.com/?utm_source=chatgpt.com "Nous Portal"
[3]: https://github.com/HackerNews/API?utm_source=chatgpt.com "GitHub - HackerNews/API: Documentation and Samples for the Official HN API · GitHub"
[4]: https://vercel.com/changelog/claude-sonnet-5-ai-gateway?utm_source=chatgpt.com "Claude Sonnet 5 now available on Vercel AI Gateway - Vercel"
[5]: https://artificialanalysis.ai/data-api/docs?utm_source=chatgpt.com "Data API docs · Artificial Analysis"
[6]: https://openrouter.ai/docs/api/api-reference/models/get-models?utm_source=chatgpt.com "List all models and their properties | OpenRouter | Documentation"

Yeah — what’s surprising is that **pieces exist, but the exact product you’re describing is still fragmented**.

There are already good **static price-comparison** products. PricePerToken says it tracks 610+ models, including dozens available free, while LLM Price Check and Artificial Analysis-style tools focus on comparing standard provider/model pricing. ([Price Per Token][1]) There are also curated lists specifically for permanent free APIs. ([GitHub][2])

I even found a tiny GitHub project explicitly calling itself an **“LLM API Token Price Aggregator & Promotion Tracker”** — but it currently has essentially no traction. ([GitHub][3])

The gap is that nobody obvious owns:

> **“What is the best LLM inference opportunity available *today*?”**

That is subtly different from a pricing database.

For example, your system should understand:

**$0.20/M tokens**
versus
**$10/month but currently 2× usage**
versus
**5M free tokens for new accounts**
versus
**free 1,000 requests/day**
versus
**$100 startup credits**
versus
**off-peak pricing**
versus
**temporary launch subsidy**
versus
**same model being dramatically cheaper through another provider**

Those aren't easily represented by a normal `$ / million tokens` table.

And this market is becoming *more* suited to that approach. Providers are actively using credits and discounts to acquire developers, while research is documenting extremely rapid declines in inference prices and increasing competition between providers. ([The Wall Street Journal][4])

So I'd make **LLM Deals** less like PCPartPicker and more like **Slickdeals + CoinMarketCap for inference**:

```text
🔥 HOT

OpenCode Go
MiMo V2.5
2× usage
Effective cost: $____ / 1M
Expires: ?
Verified: 14 min ago
🔥 94 Deal Score


DeepSeek
V4 Flash
$0.14 / $0.28 M
5M-token signup credit
Off-peak discount available
⚡ 89 Deal Score


Provider X
Model Y
FREE
1,000 req/day
Rate limit: ...
Quality: 71/100
💎 86 Deal Score
```

And that's also where your earlier monetization question gets interesting. **You don't need to charge users.** Once people actually use it to decide *where to spend their inference money*, you're sitting directly before a commercial transaction. Referral/affiliate agreements, sponsored-but-clearly-labelled placements, provider lead generation, newsletter sponsorship, and eventually aggregate market intelligence can fund the free public product without corrupting the rankings.

The key rule I'd establish immediately is:

> **Nobody can pay to alter Deal Score or rankings.**

Then providers can pay for a clearly marked promotion while your actual database remains credible.

The really valuable asset eventually isn't even the website. It's the **historical dataset**:

`provider × model × date × list price × effective price × promotion × limits × availability × performance`

After a year, you'd have a dataset showing the economics of LLM inference that basically doesn't exist in a clean form today. A 2026 economics paper had to assemble data from OpenRouter, Epoch AI and manually cross-validated observations to study essentially this market. ([arXiv][5])

**That is the moat.** The blog gets Google traffic, the deal feed gets repeat users, the API gets agents, and the historical database becomes the genuinely unusual asset.

[1]: https://pricepertoken.com/?utm_source=chatgpt.com "LLM API Pricing 2026 - Compare 300+ AI Model Costs"
[2]: https://github.com/mnfst/awesome-free-llm-apis?utm_source=chatgpt.com "mnfst/awesome-free-llm-apis"
[3]: https://github.com/icexun/ai-token-price?utm_source=chatgpt.com "GitHub - icexun/ai-token-price"
[4]: https://www.wsj.com/tech/ai/ai-giants-are-handing-out-tons-of-free-computing-power-to-grab-startup-share-c00a5c5c?utm_source=chatgpt.com "AI Giants Are Handing Out Tons of Free Computing Power to Grab Startup Share"
[5]: https://arxiv.org/abs/2603.28576?utm_source=chatgpt.com "Tiered Super-Moore's Law: Price Evolution, Production Frontiers, and Market Competition in Large Language Model Inference Services"
