-- D0-01: Oracle-1 tables

CREATE TABLE IF NOT EXISTS freshness_policies (
    policy_id INTEGER PRIMARY KEY AUTOINCREMENT,
    claim_type TEXT NOT NULL,
    source_type TEXT NOT NULL,
    ttl_seconds INTEGER NOT NULL,
    description TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS negative_observations (
    neg_id INTEGER PRIMARY KEY AUTOINCREMENT,
    observation_id INTEGER NOT NULL,
    model_id TEXT,
    field TEXT NOT NULL,
    absence_type TEXT NOT NULL,
    checked_at TEXT NOT NULL,
    source_url TEXT,
    details TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS claim_reconciliation (
    reconciliation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    offer_id TEXT NOT NULL,
    field TEXT NOT NULL,
    conflicting_values TEXT NOT NULL,
    resolution_policy TEXT,
    resolved_value TEXT,
    resolved_at TEXT,
    confidence REAL,
    notes TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS source_authority (
    authority_id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT NOT NULL,
    claim_type TEXT NOT NULL,
    authority_level TEXT NOT NULL,
    confidence REAL DEFAULT 0.5,
    notes TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS economic_access (
    access_id INTEGER PRIMARY KEY AUTOINCREMENT,
    offer_id TEXT NOT NULL,
    access_class TEXT NOT NULL,
    quota_details TEXT,
    conditions TEXT,
    observed_at TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_neg_obs_model ON negative_observations(model_id);
CREATE INDEX IF NOT EXISTS idx_neg_obs_field ON negative_observations(field);
CREATE INDEX IF NOT EXISTS idx_reconc_offer ON claim_reconciliation(offer_id);
CREATE INDEX IF NOT EXISTS idx_access_offer ON economic_access(offer_id);

-- Freshness policies
INSERT INTO freshness_policies (claim_type, source_type, ttl_seconds, description, created_at)
VALUES
    ('model_author', 'official_api', 31536000, 'permanent', datetime('now')),
    ('context_window', 'official_api', 2592000, 'weeks/months', datetime('now')),
    ('list_price', 'official_api', 86400, 'hours/day', datetime('now')),
    ('flash_promo', 'official_api', 3600, 'minutes/hours', datetime('now')),
    ('availability', 'official_api', 300, 'minutes', datetime('now')),
    ('throughput', 'official_api', 60, 'seconds/minutes', datetime('now')),
    ('rate_limit', 'official_api', 86400, 'hours/day', datetime('now')),
    ('endpoint_reachable', 'probe', 60, 'seconds/minutes', datetime('now')),
    ('list_price', 'aggregator', 43200, 'hours (aggregator less fresh)', datetime('now')),
    ('availability', 'aggregator', 600, 'minutes (aggregator less fresh)', datetime('now'));

-- Source authority
INSERT INTO source_authority (source_id, claim_type, authority_level, confidence, notes, created_at)
VALUES
    ('openrouter', 'price', 'primary', 0.95, 'OpenRouter API is authoritative for OpenRouter prices', datetime('now')),
    ('openrouter', 'availability', 'primary', 0.9, 'OpenRouter API is authoritative for endpoint availability', datetime('now')),
    ('openrouter', 'checkpoint', 'secondary', 0.7, 'OpenRouter reports but not authoritative for checkpoint details', datetime('now')),
    ('artificial_analysis', 'speed', 'primary', 0.85, 'AA measures actual speed', datetime('now')),
    ('artificial_analysis', 'quality', 'secondary', 0.7, 'AA benchmarks but not definitive', datetime('now')),
    ('models_dev', 'context_window', 'primary', 0.9, 'models.dev tracks context windows', datetime('now'));
