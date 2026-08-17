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

-- Offers (canonical truth)
CREATE TABLE IF NOT EXISTS offers (
    offer_id TEXT PRIMARY KEY,
    provider_id TEXT NOT NULL,
    model_id TEXT,
    offer_type TEXT NOT NULL DEFAULT 'metered_api',
    input_per_m REAL,
    output_per_m REAL,
    free INTEGER NOT NULL DEFAULT 0,
    context_tokens INTEGER,
    requests_per_day INTEGER,
    source_url TEXT,
    region TEXT DEFAULT 'global',
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
