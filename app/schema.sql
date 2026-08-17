-- Deal Radar V2 Schema
-- Temporal offer/promotion intelligence plane

CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER NOT NULL
);

-- Model identity (permanent-ish)
CREATE TABLE IF NOT EXISTS models (
    model_id TEXT PRIMARY KEY,
    canonical_name TEXT NOT NULL,
    author TEXT,
    family TEXT,
    context_tokens INTEGER,
    max_output_tokens INTEGER,
    reasoning INTEGER NOT NULL DEFAULT 0,
    tool_call INTEGER NOT NULL DEFAULT 0,
    structured_output INTEGER NOT NULL DEFAULT 0,
    open_weights INTEGER NOT NULL DEFAULT 0,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- Provider naming chaos resolution
CREATE TABLE IF NOT EXISTS model_aliases (
    source TEXT NOT NULL,
    alias TEXT NOT NULL,
    model_id TEXT NOT NULL REFERENCES models(model_id),
    confidence REAL NOT NULL,
    method TEXT NOT NULL,
    PRIMARY KEY(source, alias)
);

-- Providers (separate from model authors)
CREATE TABLE IF NOT EXISTS providers (
    provider_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    kind TEXT NOT NULL DEFAULT 'api',
    homepage TEXT,
    api_base TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}'
);

-- How someone can buy access
CREATE TABLE IF NOT EXISTS offers (
    offer_id TEXT PRIMARY KEY,
    provider_id TEXT NOT NULL REFERENCES providers(provider_id),
    model_id TEXT REFERENCES models(model_id),
    provider_model_slug TEXT,
    plan_id TEXT,
    offer_kind TEXT NOT NULL DEFAULT 'metered_api',
    region TEXT,
    currency TEXT NOT NULL DEFAULT 'USD',
    active INTEGER NOT NULL DEFAULT 1,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);

-- Every fetch is recorded
CREATE TABLE IF NOT EXISTS source_observations (
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
    extraction_status TEXT NOT NULL DEFAULT 'pending',
    evidence_text TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}'
);

-- Append-only price/economics snapshots
CREATE TABLE IF NOT EXISTS offer_snapshots (
    snapshot_id INTEGER PRIMARY KEY AUTOINCREMENT,
    offer_id TEXT NOT NULL REFERENCES offers(offer_id),
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

-- Temporal promotion/change events
CREATE TABLE IF NOT EXISTS promotion_events (
    event_id TEXT PRIMARY KEY,
    offer_id TEXT,
    model_id TEXT,
    provider_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    fact_basis TEXT NOT NULL DEFAULT 'observed',
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
    confidence REAL NOT NULL DEFAULT 1.0,
    source_observation_id INTEGER NOT NULL,
    corroboration_count INTEGER NOT NULL DEFAULT 0,
    metadata_json TEXT NOT NULL DEFAULT '{}'
);

-- Quarantined social signals
CREATE TABLE IF NOT EXISTS community_leads (
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
    verification_status TEXT NOT NULL DEFAULT 'unverified',
    metadata_json TEXT NOT NULL DEFAULT '{}'
);

-- Source health tracking
CREATE TABLE IF NOT EXISTS source_health (
    source_id TEXT PRIMARY KEY,
    last_fetch_at TEXT,
    last_success_at TEXT,
    last_error TEXT,
    consecutive_failures INTEGER NOT NULL DEFAULT 0,
    avg_latency_ms REAL,
    total_fetches INTEGER NOT NULL DEFAULT 0,
    total_failures INTEGER NOT NULL DEFAULT 0
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_snapshots_offer ON offer_snapshots(offer_id);
CREATE INDEX IF NOT EXISTS idx_snapshots_observed ON offer_snapshots(observed_at);
CREATE INDEX IF NOT EXISTS idx_events_provider ON promotion_events(provider_id);
CREATE INDEX IF NOT EXISTS idx_events_type ON promotion_events(event_type);
CREATE INDEX IF NOT EXISTS idx_events_status ON promotion_events(status);
CREATE INDEX IF NOT EXISTS idx_events_seen ON promotion_events(first_seen_at);
CREATE INDEX IF NOT EXISTS idx_offers_provider ON offers(provider_id);
CREATE INDEX IF NOT EXISTS idx_offers_model ON offers(model_id);
CREATE INDEX IF NOT EXISTS idx_obs_source ON source_observations(source_id);
CREATE INDEX IF NOT EXISTS idx_leads_source ON community_leads(source);
