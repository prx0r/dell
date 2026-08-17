-- D0-01: Core tables (sources, observations, offers)

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

CREATE TABLE IF NOT EXISTS offers (
    offer_id TEXT PRIMARY KEY,
    provider_id TEXT NOT NULL,
    model_id TEXT,
    offer_type TEXT NOT NULL DEFAULT 'metered_api',
    input_per_m REAL,
    output_per_m REAL,
    cache_read_per_m REAL,
    cache_write_per_m REAL,
    free INTEGER NOT NULL DEFAULT 0,
    price_state TEXT DEFAULT 'unknown',
    requests_per_day INTEGER,
    requests_per_5h INTEGER,
    requests_per_minute INTEGER,
    tokens_per_day INTEGER,
    quota_scope TEXT,
    quota_window_hours REAL,
    subscription_usd REAL,
    credits_included REAL,
    usage_multiplier REAL,
    capacity_multiplier REAL,
    context_tokens INTEGER,
    max_output_tokens INTEGER,
    region TEXT,
    automation_allowed INTEGER,
    requires_card INTEGER,
    requires_phone INTEGER,
    requires_kyc INTEGER,
    starts_at TEXT,
    expires_at TEXT,
    expiry_precision TEXT,
    deal_type TEXT,
    deal_status TEXT DEFAULT 'active',
    source_url TEXT,
    metadata_json TEXT DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    first_seen_at TEXT,
    last_verified_at TEXT,
    next_check_at TEXT,
    discovered_by TEXT,
    value_state TEXT DEFAULT 'UNKNOWN',
    lifecycle_state TEXT DEFAULT 'ACTIVE_UNVERIFIED',
    last_source_success_at TEXT,
    stale_reason TEXT,
    valid_from TEXT,
    valid_until TEXT,
    superseded_at TEXT
);

CREATE TABLE IF NOT EXISTS deal_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    offer_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    previous_value TEXT,
    current_value TEXT,
    source_observation_id INTEGER,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS source_health (
    source_id TEXT PRIMARY KEY,
    last_check_at REAL,
    status TEXT DEFAULT 'unknown',
    latency_ms REAL,
    model_count INTEGER DEFAULT 0,
    consecutive_failures INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_offers_provider ON offers(provider_id);
CREATE INDEX IF NOT EXISTS idx_offers_model ON offers(model_id);
CREATE INDEX IF NOT EXISTS idx_offers_free ON offers(free);
CREATE INDEX IF NOT EXISTS idx_events_offer ON deal_events(offer_id);
CREATE INDEX IF NOT EXISTS idx_obs_source ON source_observations(source_id);
CREATE INDEX IF NOT EXISTS idx_sources_enabled ON sources(enabled, priority, last_fetch_at);
