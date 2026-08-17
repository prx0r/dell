-- LLM Deals Canonical Schema
-- SQLite WAL mode, strict typing

-- Source registry (durable, not RAM)
CREATE TABLE IF NOT EXISTS sources (
    source_id TEXT PRIMARY KEY,
    adapter_module TEXT NOT NULL,
    cadence_minutes INTEGER NOT NULL DEFAULT 1440,
    priority INTEGER NOT NULL DEFAULT 1,
    enabled INTEGER NOT NULL DEFAULT 1,
    last_fetch_at REAL DEFAULT 0,
    last_success_at REAL,
    consecutive_failures INTEGER DEFAULT 0,
    created_at TEXT NOT NULL
);

-- Source observations (immutable)
CREATE TABLE IF NOT EXISTS source_observations (
    observation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT NOT NULL,
    url TEXT NOT NULL,
    fetched_at TEXT NOT NULL,
    http_status INTEGER,
    content_hash TEXT,
    model_count INTEGER DEFAULT 0,
    metadata_json TEXT DEFAULT '{}'
);

-- Offers (canonical truth) — preserves ALL adapter data
CREATE TABLE IF NOT EXISTS offers (
    offer_id TEXT PRIMARY KEY,
    provider_id TEXT NOT NULL,
    model_id TEXT,
    offer_type TEXT NOT NULL DEFAULT 'metered_api',
    -- Pricing
    input_per_m REAL,
    output_per_m REAL,
    cache_read_per_m REAL,
    cache_write_per_m REAL,
    -- Free tier
    free INTEGER NOT NULL DEFAULT 0,
    -- Quota (preserved, not collapsed)
    requests_per_day INTEGER,
    requests_per_5h INTEGER,
    requests_per_minute INTEGER,
    tokens_per_day INTEGER,
    quota_scope TEXT,
    quota_window_hours REAL,
    -- Subscription
    subscription_usd REAL,
    credits_included REAL,
    usage_multiplier REAL,
    capacity_multiplier REAL,
    -- Context
    context_tokens INTEGER,
    max_output_tokens INTEGER,
    -- Eligibility (NULL = unknown, NOT 'global')
    region TEXT,
    automation_allowed INTEGER,
    requires_card INTEGER,
    requires_phone INTEGER,
    requires_kyc INTEGER,
    -- Timing
    starts_at TEXT,
    expires_at TEXT,
    expiry_precision TEXT,
    -- Classification
    deal_type TEXT,
    deal_status TEXT DEFAULT 'active',
    -- Provenance
    source_url TEXT,
    metadata_json TEXT DEFAULT '{}',
    -- Timestamps
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- Deal events (append-only)
CREATE TABLE IF NOT EXISTS deal_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    offer_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    previous_value TEXT,
    current_value TEXT,
    source_observation_id INTEGER,
    created_at TEXT NOT NULL
);

-- Source health (durable)
CREATE TABLE IF NOT EXISTS source_health (
    source_id TEXT PRIMARY KEY,
    last_check_at REAL,
    status TEXT DEFAULT 'unknown',
    latency_ms REAL,
    model_count INTEGER DEFAULT 0,
    consecutive_failures INTEGER DEFAULT 0
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_offers_provider ON offers(provider_id);
CREATE INDEX IF NOT EXISTS idx_offers_model ON offers(model_id);
CREATE INDEX IF NOT EXISTS idx_offers_free ON offers(free);
CREATE INDEX IF NOT EXISTS idx_events_offer ON deal_events(offer_id);
CREATE INDEX IF NOT EXISTS idx_obs_source ON source_observations(source_id);
CREATE INDEX IF NOT EXISTS idx_sources_enabled ON sources(enabled, priority, last_fetch_at);

-- Claims (immutable extraction from source)
CREATE TABLE IF NOT EXISTS claims (
    claim_id INTEGER PRIMARY KEY AUTOINCREMENT,
    offer_id TEXT NOT NULL,
    claim_type TEXT NOT NULL,
    claim_value TEXT NOT NULL,
    source_observation_id INTEGER,
    confidence REAL DEFAULT 0.5,
    created_at TEXT NOT NULL
);

-- Evidence (provenance for each claim)
CREATE TABLE IF NOT EXISTS evidence (
    evidence_id INTEGER PRIMARY KEY AUTOINCREMENT,
    claim_id INTEGER NOT NULL,
    evidence_type TEXT NOT NULL,
    source_url TEXT,
    excerpt TEXT,
    selector TEXT,
    content_hash TEXT,
    created_at TEXT NOT NULL
);

-- Verification checks
CREATE TABLE IF NOT EXISTS verification_checks (
    check_id INTEGER PRIMARY KEY AUTOINCREMENT,
    offer_id TEXT NOT NULL,
    check_type TEXT NOT NULL,
    status TEXT NOT NULL,
    checked_at TEXT NOT NULL,
    details TEXT,
    confidence REAL DEFAULT 0.5
);

-- Activation recipes (step-by-step setup instructions)
CREATE TABLE IF NOT EXISTS activation_recipes (
    recipe_id INTEGER PRIMARY KEY AUTOINCREMENT,
    provider_id TEXT NOT NULL,
    steps_json TEXT NOT NULL,
    requires_human INTEGER NOT NULL DEFAULT 1,
    requires_card INTEGER NOT NULL DEFAULT 0,
    requires_phone INTEGER NOT NULL DEFAULT 0,
    requires_kyc INTEGER NOT NULL DEFAULT 0,
    estimated_minutes INTEGER,
    created_at TEXT NOT NULL
);
