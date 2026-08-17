Yes. I’d now freeze the concept as **LLM Deals = a verified, machine-readable inference-market data layer**, with Hermes acting as the autonomous research/curation workforce around it.

The key architectural rule should be:

> **Deterministic systems observe. Agents interpret. Evidence decides. Humans only intervene where legal/account/payment ambiguity requires them.**

Hermes is unusually well suited to this because its current scheduler supports recurring jobs, attached skills, fresh agent sessions, and a `--no-agent`/script mode with zero LLM involvement. Nous also explicitly designs Hermes around a narrow core with capabilities living in skills/plugins rather than continually expanding the core. ([GitHub][1])

# 1. The canonical architecture

I would structure the whole system like this:

```text
                    DISCOVERY
                       │
       ┌───────────────┼────────────────┐
       │               │                │
 official sources   communities      web search
 APIs/docs/RSS      Reddit/HN/etc    multilingual
       │               │                │
       └───────────────┬────────────────┘
                       ▼
                  SOURCE REGISTRY
                       │
                       ▼
                DETERMINISTIC FETCH
            HTTP / RSS / API / git / crawl
                       │
                  content changed?
                   /           \
                 NO             YES
                 │               │
              finish             ▼
                           OBSERVATION
                                │
                           cheap parser
                                │
                          candidate claims
                                │
                                ▼
                        HERMES INVESTIGATOR
                     "What actually changed?"
                                │
                      ┌─────────┴─────────┐
                      ▼                   ▼
                 irrelevant          candidate deal
                                          │
                                          ▼
                                  HERMES VERIFIER
                              seek canonical evidence
                                          │
                                          ▼
                                    CLAIM GRAPH
                                          │
                                          ▼
                                      DEAL EVENT
                                          │
                    ┌─────────────────────┼───────────────┐
                    ▼                     ▼               ▼
                 website                 API          changefeed
                                                        │
                                                  other agents
                                                  routers/IDEs
```

**Never let Hermes directly edit the canonical deal row because it “thinks” something changed.**

Hermes proposes:

```text
CandidateDeal
CandidateClaim
CandidateExpiry
CandidateEligibility
CandidateActivationRecipe
```

A deterministic commit layer checks schemas, evidence, temporal consistency and identity before creating a new version.

That distinction is what turns this from a scraping project into infrastructure.

---

# 2. Don't make `Deal` your permanent truth

I would have roughly these core entities:

```text
Provider
Model
ProviderOffering
CommercialPlan

Source
SourceObservation

Claim
Evidence

Deal
DealEvent

EligibilityRule
ActivationRecipe
TermsSnapshot

UsageUnit
QuotaRule

Verification
```

The important layer is:

```text
SOURCE
   ↓
OBSERVATION
   ↓
CLAIM
   ↓
DEAL
```

For example, the OpenCode page may say:

```text
"Luna: 2x usage"
```

That becomes an immutable observation.

Then:

```json
{
  "subject": "opencode/go/gpt-5.6-luna",
  "predicate": "usage_multiplier",
  "value": 2,
  "source_observation_id": "...",
  "valid_from": "...",
  "valid_until": null
}
```

The current `Deal` is just the projection of the best supported claims.

If tomorrow the text becomes `1x usage`, you **don't update 2 → 1**.

You append:

```text
DEAL_ACTIVATED  2x
DEAL_CHANGED    2x → 1x
DEAL_EXPIRED
```

That historical stream becomes one of your strongest assets.

# 3. Make source provenance absurdly good

Every source gets a registry object:

```json
{
  "source_id": "opencode-go-pricing",
  "provider_id": "opencode",

  "url": "...",
  "type": "official_pricing",

  "authority": "primary",
  "language": "en",
  "region": "global",

  "fetch_method": "http",
  "extractor": "opencode_go_v3",

  "freshness_class": "hot",
  "next_check_at": "...",

  "etag": "...",
  "last_modified": "...",

  "last_success_at": "...",
  "last_change_at": "...",
  "consecutive_errors": 0,

  "robots_allowed": true
}
```

Use HTTP validators such as `ETag` and `Last-Modified` whenever the server supplies them, rather than downloading/processing unchanged bodies repeatedly; both are standard HTTP validator mechanisms. ([IETF Datatracker][2])

And respect the Robots Exclusion Protocol and provider-specific crawling rules rather than hammering pages. ([Google for Developers][3])

# 4. Polling should be adaptive, not one giant cron

Do **not** do:

```text
*/5 * * * *
crawl_everything()
```

Web-crawling research specifically treats freshness as a scheduling problem where change rates are learned online and resources allocated accordingly. ([arXiv][4])

Start with these priors:

| Source                         | Initial cadence |
| ------------------------------ | --------------: |
| Active promo page              |          15 min |
| Provider pricing page          |       30–60 min |
| Provider changelog             |          30 min |
| Provider RSS/API               |       15–30 min |
| Models.dev catalog             |          1 hour |
| Regular docs page              |         6 hours |
| Startup/research-credit page   |        12 hours |
| Terms page                     |        24 hours |
| Whole-provider site discovery  |        24 hours |
| Stable page unchanged 30+ days |        2–3 days |
| Stable page unchanged 90+ days |          weekly |

Then maintain:

```text
observed_change_rate
deal_importance
source_authority
active_deal_count
time_to_known_expiry
recent_launch_activity
fetch_cost
error_rate
```

and derive:

```text
next_check_at
```

A currently hot OpenCode promotion could stay at 15 minutes.

A boring provider terms page unchanged for six months can drop to weekly.

When something changes, temporarily boost it:

```text
normal: 6h

change detected
↓
15m
30m
1h
3h
6h
↓
back to learned baseline
```

That is much smarter than fixed cron frequency.

# 5. Use events whenever possible

Polling should be the fallback.

The hierarchy should be:

```text
webhook
↓
official API
↓
RSS / Atom
↓
GitHub release/feed
↓
HTTP conditional GET
↓
HTML diff
↓
JS browser crawl
↓
Hermes/browser investigation
```

RSSHub is useful for turning large numbers of otherwise awkward global sources into feeds, while Hacker News' Algolia API provides programmatic search over HN data and says its index is updated in real time from the official HN API. ([GitHub][5])

Firecrawl's current monitoring system is also almost a reference design for parts of this: it distinguishes known-page monitoring, whole-site monitoring and web-scale search monitoring; emits `same/new/changed/removed/error`; supports JSON field-level diffs; and can push changes via webhooks. ([Firecrawl Docs][6])

I wouldn't make Firecrawl mandatory, though. Your cheap path should be native HTTP/RSS/API + your own hash/diff logic. Use Firecrawl or browser automation for difficult sites.

`changedetection.io` is another strong self-hostable building block specifically built for monitoring page changes and price changes. ([GitHub][7])

---

# 6. Hermes should wake up **because something happened**

This is where you save huge amounts of inference.

Instead of:

```text
Hermes:
"Read these 2,000 pages every hour."
```

do:

```text
Python:
2,000 cheap HTTP checks

1,973 unchanged
27 changed

cheap structural diff:
19 irrelevant layout/nav changes
8 potentially relevant

Hermes:
investigate 8
```

And perhaps only 3 require a serious model.

So you get:

```text
2,000 source checks
      ↓
27 diffs
      ↓
8 candidate changes
      ↓
3 serious investigations
      ↓
1 new deal
```

Hermes already supports scheduled jobs that load skills and a no-agent script mode, so you can run the deterministic scanner without an LLM and reserve actual agent sessions for investigation. ([GitHub][1])

A good Hermes decomposition is:

```text
deal-scout
deal-extractor
deal-verifier
terms-auditor
temporal-parser
regional-researcher
duplicate-resolver
stale-deal-reaper
source-curator
```

Each becomes a skill rather than bespoke application logic.

---

# 7. Make “how automated is this deal?” a first-class field

This is an excellent addition.

People don't merely care:

> “Free model available.”

They care:

> “Can my agent actually start using this without me spending half an hour creating accounts?”

I'd introduce an **Activation Class**.

| Class            | Meaning                                            |
| ---------------- | -------------------------------------------------- |
| `ZERO_TOUCH`     | Directly usable with existing/public endpoint      |
| `KEY_ONLY`       | Human supplies API key; agent does everything else |
| `SIGNUP`         | Account must be created                            |
| `VERIFY`         | Email/phone verification required                  |
| `PAYMENT_METHOD` | Card/payment setup required                        |
| `SUBSCRIPTION`   | User must purchase/activate plan                   |
| `KYC`            | Identity/business verification                     |
| `APPLICATION`    | Startup/research/grant application                 |
| `REGION_LOCKED`  | Eligibility depends on region/account              |
| `UNKNOWN`        | Not sufficiently verified                          |

And separately:

```text
agent_automatable_fraction: 0.80

manual_steps: 1
agent_steps: 5

human_checkpoint_reason:
  "Terms acceptance"
```

This produces fantastic UI:

```text
SenseNova Public Beta

Cost             FREE
Setup            2 minutes
Agent-ready      HIGH
Manual action    Create account + API key
Agent can do     Configure SDK, test endpoint, add to LiteLLM
Card             No
KYC              No
Region            Global
```

# 8. Publish an exact machine-readable activation recipe

This might become one of LLM Deals' best features.

Instead of an article saying:

> “Sign up and copy your API key.”

return:

```json
{
  "deal_id": "...",

  "recipe_version": 3,

  "steps": [
    {
      "id": "open_signup",
      "type": "open_url",
      "actor": "human",
      "url": "...",
      "required": true
    },
    {
      "id": "accept_terms",
      "type": "legal_consent",
      "actor": "human",
      "required": true
    },
    {
      "id": "create_api_key",
      "type": "credential_creation",
      "actor": "human",
      "required": true
    },
    {
      "id": "configure",
      "type": "local_config",
      "actor": "agent",
      "depends_on": ["create_api_key"]
    },
    {
      "id": "verify",
      "type": "api_healthcheck",
      "actor": "agent"
    }
  ]
}
```

The agent should be able to say:

> “This deal requires one human action. Open this page, create an API key, then give the key to your existing secret manager. I can do the rest.”

That is much better than trying to make agents autonomously accept legal terms, payments, identity checks or regional restrictions.

**Legal consent, payments, KYC and identity verification should always be explicit human checkpoints.**

Everything around them can be agentic.

---

# 9. Terms need their own versioned object

Do not put:

```text
automation_allowed: true
```

in a random deal row with no evidence.

Make:

```text
TermsSnapshot
```

with:

```json
{
  "provider": "x",
  "observed_at": "...",
  "effective_at": "...",

  "source_url": "...",
  "content_hash": "...",

  "claims": {
    "api_use": "allowed",
    "automated_use": "allowed",
    "commercial_use": "unknown",
    "production_use": "restricted",
    "resale": "prohibited",
    "account_sharing": "prohibited",
    "rate_limit": "...",
    "geography": ["..."]
  },

  "confidence": 0.96
}
```

Then store the **actual supporting passage/location**.

Your agent-facing response becomes:

```text
automation_allowed:
  value: true
  confidence: 0.97
  verified_at: ...
  source: official_terms
```

This lets routers ask:

```http
?automation_allowed=true
&production_allowed=true
&confidence_gte=0.95
```

That's seriously useful infrastructure.

# 10. The countdown must represent uncertainty properly

This is another place most sites screw up.

Suppose a provider says:

> Offer ends 31 August.

You **do not know** whether they mean:

```text
00:00 local time
23:59 local time
23:59 UTC
some arbitrary backend cutoff
```

So do not fabricate:

> `13d 08h 32m 17s`

That is false precision.

Use:

```json
{
  "ends_at": null,
  "end_date": "2026-08-31",
  "timezone": null,
  "precision": "day",
  "boundary": "unknown"
}
```

UI:

> **Ends August 31 — exact cutoff not published**

But if terms say:

> August 31, 2026 at 23:59 PDT

store the real instant plus timezone:

```json
{
  "ends_at": "2026-09-01T06:59:00Z",
  "source_datetime": "2026-08-31T23:59:00-07:00",
  "timezone": "America/Los_Angeles",
  "precision": "minute",
  "boundary": "inclusive"
}
```

RFC 3339 gives you a standard Internet timestamp representation, while IANA's timezone database handles geographic timezone/DST rules; RFC 9557 additionally standardizes attaching timezone information to Internet timestamps. ([IETF Datatracker][8])

Then the **browser calculates the seconds remaining locally** from `ends_at`.

No cron is needed every second.

The server returns:

```text
server_now
ends_at
```

and JavaScript renders:

```text
2d 07h 18m 43s
2d 07h 18m 42s
2d 07h 18m 41s
```

That avoids server load and clock-drift issues.

# 11. Expiry has multiple semantics

I'd model:

```text
ABSOLUTE
2026-09-01T00:00Z

ROLLING
30 days after signup

QUOTA_RESET
every 5 hours

CALENDAR_RESET
monthly

CREDIT_EXPIRY
90 days after activation

UNTIL_BUDGET_EXHAUSTED

UNTIL_PUBLIC_BETA_ENDS

UNKNOWN
```

This matters enormously.

A deal such as:

```text
$5 credit / expires 30 days after signup
```

doesn't have one global countdown.

Your API instead returns:

```json
{
  "expiry_mode": "rolling",
  "duration": "P30D",
  "anchor": "account_activation"
}
```

An agent with the user's activation date can calculate their personal expiry.

---

# 12. Schedule checks *around* important boundaries

When an exact expiry is known:

```text
normal cadence
↓
T - 24h       verify
T - 1h        verify
T - 10m       verify
T + 1m        verify expiration
T + 1h        verify replacement/promotion
T + 24h       final state check
```

If the source removes the expiry or extends it, that generates another DealEvent.

This is much better than simply declaring it dead because your stored timestamp passed.

# 13. Yes, offer usage tracking — but make it optional and separate

I would **absolutely build this eventually**, but not make it necessary to use LLM Deals.

Call it something like:

```text
LLM Deals Meter
```

The core API remains completely stateless/public.

Users can optionally install middleware:

```text
Python SDK
Node SDK
LiteLLM callback
OpenTelemetry collector
OpenAI-compatible proxy plugin
Hermes skill
```

that records:

```text
provider
model
offering
deal_id
requests
input tokens
output tokens
cached tokens
latency
errors
estimated cost
quota consumed
```

OpenTelemetry is a very good basis rather than inventing your own telemetry vocabulary. Its GenAI semantic conventions standardize provider/model identity and token usage, and modern agent tools are increasingly emitting GenAI OTel telemetry. ([OpenTelemetry][9])

Crucially:

```text
prompt contents: OFF by default
completion contents: OFF by default
API keys: NEVER sent
```

LLM Deals only needs:

```text
model X
17,331 input tokens
4,129 output tokens
deal Y
```

not what the user actually said.

# 14. Usage has to support imperfect knowledge

Do not pretend you always know someone's remaining allowance.

Track:

```text
quota_source
```

as:

```text
PROVIDER_API
RESPONSE_HEADER
PROVIDER_DASHBOARD
LOCAL_MEASURED
USER_ENTERED
ESTIMATED
UNKNOWN
```

Example:

```json
{
  "quota": {
    "total": 1000,
    "remaining": 617,
    "unit": "requests",

    "remaining_source": "local_measured",
    "confidence": 0.82,

    "resets_at": "..."
  }
}
```

Then a future router can distinguish:

> “617 confirmed remaining”

from

> “probably ~617 remaining based on locally observed calls.”

That precision matters.

---

# 15. New-deal discovery needs a separate pipeline from monitoring

Known-source monitoring finds:

> “OpenCode changed its pricing.”

It doesn't find:

> “Random Japanese cloud provider just launched 3,000 free calls.”

So build a **Scout pipeline**.

Conceptually:

```text
KNOWN SOURCE MONITORING
        +
OPEN-WEB DISCOVERY
```

The discovery agent continuously searches combinations of:

```text
concept × region × language × time
```

For example:

```text
"LLM API" + "free quota"
"生成AI API" + "無料枠"
"大模型 API" + "限时免费"
"LLM API" + "무료 크레딧"
"API IA" + "créditos grátis"
```

Firecrawl now supports a distinct web-scale search monitor specifically for alerting when new results matching a goal appear, which is the right conceptual pattern even if you implement your own search layer. ([Firecrawl Docs][6])

Then add lead feeds from:

```text
Reddit
Hacker News
GitHub
RSSHub
provider blogs
release notes
developer newsletters
regional tech media
regional developer forums
```

A community result **never becomes a deal** directly.

It becomes:

```text
Lead
  ↓
Hermes researches it
  ↓
find official source?
  ├─ yes → candidate verified
  └─ no  → community_reported
```

---

# 16. Let the Scout learn new sources

This is particularly suited to Hermes because of its skill/memory model.

Suppose the regional scout keeps finding Chinese deals through:

```text
provider.example.cn/news/promotion
```

Hermes should propose:

```json
{
  "action": "ADD_SOURCE",
  "url": "...",
  "reason": "Three verified promotions discovered here in 30 days",
  "recommended_poll_interval": "1h"
}
```

A deterministic source-curation policy can approve obviously valid additions or send uncertain ones for review.

This gives you a self-expanding radar:

```text
search
↓
lead
↓
verified deal
↓
source discovered
↓
source becomes permanent monitor
↓
future deal detected immediately
```

That is the flywheel.

# 17. Pruning should never mean deleting

Deal states:

```text
DISCOVERED
UNVERIFIED
VERIFIED_LIVE
ENDING_SOON
STALE_SUSPECTED
EXPIRED
WITHDRAWN
SUPERSEDED
DEAD_PROVIDER
UNKNOWN
```

If an active free offer disappears from the provider page:

```text
do NOT:
LIVE → EXPIRED immediately
```

Instead:

```text
LIVE
 ↓
STALE_SUSPECTED
 ↓
immediate re-fetch
 ↓
alternate official source check
 ↓
Hermes investigation
 ↓
EXPIRED / STILL_LIVE / UNKNOWN
```

Temporary 403s, Cloudflare failures and site redesigns shouldn't destroy your dataset.

The historical object stays forever.

Your active endpoint simply excludes it:

```http
GET /v1/deals?status=verified_live
```

while:

```http
GET /v1/deals/{id}/history
```

still shows everything.

---

# 18. Add a freshness SLA to every result

This would be a beautiful small feature.

Instead of merely:

> Verified.

Show:

```text
Official source
Verified 11 minutes ago
Source normally checked every 30 minutes
Next verification due in 19 minutes
```

And API:

```json
{
  "freshness": {
    "last_verified_at": "...",
    "next_check_at": "...",
    "target_max_age_seconds": 1800,
    "is_stale": false
  }
}
```

Now an autonomous router can decide:

```text
I only accept deal data verified < 1h ago.
```

That's how you become **agent infrastructure**.

# 19. Give downstream agents a changefeed, not just REST

Alongside:

```http
GET /v1/deals
```

provide:

```http
GET /v1/events?since=cursor
```

Returning:

```json
{
  "events": [
    {
      "type": "deal.activated",
      "deal_id": "...",
      "occurred_at": "..."
    },
    {
      "type": "price.changed",
      "offering_id": "...",
      "occurred_at": "..."
    },
    {
      "type": "deal.expiring",
      "deal_id": "...",
      "occurred_at": "..."
    }
  ],
  "next_cursor": "..."
}
```

Eventually add webhooks:

```text
deal.created
deal.changed
deal.expired
price.changed
provider.added
model.added
quota.changed
terms.changed
```

Then LiteLLM plugins, custom routers and agents don't need to continuously download your whole catalog.

# 20. Make agent integration ridiculously easy

I would eventually ship four tiny surfaces:

```text
REST API
OpenAPI spec
MCP server
Agent skill
```

The MCP/agent tools can remain extremely boring:

```text
search_deals()
get_deal()
get_deal_history()
get_activation_recipe()
get_terms()
compare_offerings()
get_free_capacity_options()
get_recent_changes()
```

No routing required.

A Hermes agent can call:

```text
get_deals(
    task="coding",
    free=true,
    automation_allowed=true,
    setup_class=["ZERO_TOUCH", "KEY_ONLY"]
)
```

and make its own decision.

That's exactly the position you want.

---

# 21. Hermes deployment: I would use it this way

Hermes currently supports cron scheduling, skills, subagents, terminal/browser tools and multiple execution backends. Its docs also note that parallel delegated subagents can share a container unless separate task environments are configured, while its Docker backend supports capability dropping and `no-new-privileges`. ([GitHub][10])

So I'd split it:

```text
HERMES PROFILE: scout
internet access
search/browser
NO production DB write
NO provider keys
outputs CandidateLead only


HERMES PROFILE: verifier
official-web access
reads observations
outputs CandidateClaims
NO canonical writes


HERMES PROFILE: curator
reads candidates + evidence
can call commit API
commit API itself enforces schemas/invariants


DETERMINISTIC WORKERS
fetch
hash
diff
schedule
expiry
API publication
```

Do **not** give the random-web Scout your production credentials.

Hermes' own design encourages capabilities to live in plugins/skills, which fits this separation cleanly. ([GitHub][11])

# 22. The V1 data model I would actually build

This is the minimum set I'd freeze:

```text
Provider
Model
Offering

Source
Observation

Claim
Evidence

Deal
DealEvent

ActivationRecipe
TermsSnapshot

Verification
```

And these fields are non-negotiable on `Deal`:

```text
stable_id

provider_id
model_ids[]
offering_ids[]

deal_type
status

benefit
quota
reset_rule

eligibility
regions

activation_class
activation_recipe_id

starts_at
ends_at
expiry_mode
time_precision
timezone

terms_snapshot_id

source_ids[]
verification_confidence
last_verified_at
next_check_at
```

Everything else can grow later.

---

# 23. The entire autonomous loop

The end state is wonderfully simple:

```text
00. deterministic scheduler asks:
    what sources are due?

01. cheap fetch

02. unchanged?
    stop

03. changed?
    persist immutable observation

04. deterministic diff/extractor

05. possibly relevant?
    enqueue candidate

06. Hermes investigator:
    classify change

07. Hermes verifier:
    find primary evidence
    resolve model/provider identity
    parse deal
    inspect terms
    construct activation recipe
    resolve time semantics

08. deterministic validator:
    schema valid?
    evidence valid?
    impossible dates?
    conflicting claims?
    duplicate?

09. commit DealEvent

10. API projection updates

11. subscribers get event

12. scheduler learns from change history

13. later:
    expiry/reverification runs

14. never delete history
```

**That is the product.**

And I would deliberately defer Hot Router. The more I think through this architecture, the more useful it is to let other people build routing systems against a genuinely excellent substrate.

The standout features I would prioritize beyond the obvious pricing table are **Activation Recipes, Automation Class, Terms Snapshots, exact-but-honest temporal semantics, Freshness SLA, immutable DealEvents, and the downstream changefeed**. Those make LLM Deals feel designed for agents rather than merely being a website with a JSON endpoint.

[1]: https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/cron.md "hermes-agent/website/docs/user-guide/features/cron.md at main · NousResearch/hermes-agent · GitHub"
[2]: https://datatracker.ietf.org/doc/html/rfc9110 "RFC 9110 - HTTP Semantics"
[3]: https://developers.google.com/search/docs/crawling-indexing/robots/intro?utm_source=chatgpt.com "Robots.txt Introduction and Guide | Google Search Central"
[4]: https://arxiv.org/abs/2004.02167 "[2004.02167] Change Rate Estimation and Optimal Freshness in Web Page Crawling"
[5]: https://github.com/diygod/rsshub?utm_source=chatgpt.com "DIYgod/RSSHub: 🧡 Everything is RSSible"
[6]: https://docs.firecrawl.dev/features/monitoring "Monitoring | Firecrawl"
[7]: https://github.com/dgtlmoon/changedetection.io?utm_source=chatgpt.com "Best and simplest tool for website change detection, web ..."
[8]: https://datatracker.ietf.org/doc/html/rfc3339.html?utm_source=chatgpt.com "RFC 3339: Date and Time on the Internet: Timestamps"
[9]: https://opentelemetry.io/blog/2026/genai-observability/ "Inside the LLM Call: GenAI Observability with OpenTelemetry | OpenTelemetry"
[10]: https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/configuration.md "hermes-agent/website/docs/user-guide/configuration.md at main · NousResearch/hermes-agent · GitHub"
[11]: https://github.com/NousResearch/hermes-agent/blob/main/AGENTS.md "hermes-agent/AGENTS.md at main · NousResearch/hermes-agent · GitHub"
