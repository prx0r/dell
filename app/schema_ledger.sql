-- MODEL LEDGER: Canonical model info + append-only price history
-- This is the internal ledger for tracking all models, prices, and deals

-- MODEL LEDGER: Canonical model info
CREATE TABLE IF NOT EXISTS models (
    model_id TEXT PRIMARY KEY,
    family TEXT,
    base_model TEXT,
    context_window INTEGER,
    max_output INTEGER,
    architecture TEXT,
    license TEXT,
    open_weights INTEGER DEFAULT 0,
    release_date TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- MODEL PRICES: Append-only price ledger
CREATE TABLE IF NOT EXISTS model_prices (
    price_id INTEGER PRIMARY KEY AUTOINCREMENT,
    model_id TEXT NOT NULL,
    provider_id TEXT NOT NULL,
    input_per_m REAL,
    output_per_m REAL,
    free INTEGER DEFAULT 0,
    price_state TEXT DEFAULT 'unknown',
    quota_requests_per_day INTEGER,
    quota_requests_per_5h INTEGER,
    subscription_usd REAL,
    credits_included REAL,
    region TEXT,
    source_url TEXT,
    observed_at TEXT NOT NULL,
    expires_at TEXT,
    created_at TEXT NOT NULL
);

-- MODEL PROVIDERS: Which providers offer which models
CREATE TABLE IF NOT EXISTS model_providers (
    model_id TEXT NOT NULL,
    provider_id TEXT NOT NULL,
    offer_type TEXT,
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    PRIMARY KEY (model_id, provider_id)
);

-- MODEL EVENTS: Append-only change log
CREATE TABLE IF NOT EXISTS model_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    model_id TEXT NOT NULL,
    provider_id TEXT,
    event_type TEXT NOT NULL,
    previous_value TEXT,
    current_value TEXT,
    source_url TEXT,
    observed_at TEXT NOT NULL,
    created_at TEXT NOT NULL
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_models_family ON models(family);
CREATE INDEX IF NOT EXISTS idx_prices_model ON model_prices(model_id);
CREATE INDEX IF NOT EXISTS idx_prices_provider ON model_prices(provider_id);
CREATE INDEX IF NOT EXISTS idx_providers_model ON model_providers(model_id);
CREATE INDEX IF NOT EXISTS idx_events_model ON model_events(model_id);
