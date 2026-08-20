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
    price_state TEXT DEFAULT 'unknown',
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
    updated_at TEXT NOT NULL,
    -- Lifecycle / oracle state
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

-- Verification Runs (immutable)
CREATE TABLE IF NOT EXISTS verification_runs (
    run_id TEXT PRIMARY KEY,
    run_type TEXT NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    agent_framework TEXT,
    agent_model TEXT,
    skill_id TEXT,
    skill_version INTEGER,
    skill_sha256 TEXT,
    repo_git_sha TEXT,
    sources_attempted INTEGER DEFAULT 0,
    sources_successful INTEGER DEFAULT 0,
    sources_failed INTEGER DEFAULT 0,
    claims_confirmed INTEGER DEFAULT 0,
    claims_created INTEGER DEFAULT 0,
    claims_invalidated INTEGER DEFAULT 0,
    previous_run_root TEXT,
    event_log_hash TEXT,
    artifact_merkle_root TEXT,
    claim_merkle_root TEXT,
    run_root TEXT,
    signature TEXT,
    status TEXT DEFAULT 'started'
);

-- Tool Events (append-only hash chain)
CREATE TABLE IF NOT EXISTS tool_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    seq INTEGER NOT NULL,
    verification_run_id TEXT,
    tool TEXT NOT NULL,
    arguments_hash TEXT,
    result_hash TEXT,
    status TEXT,
    parent_event_hash TEXT,
    event_hash TEXT NOT NULL,
    created_at TEXT NOT NULL
);

-- Evidence (with selectors)
CREATE TABLE IF NOT EXISTS evidence_v2 (
    evidence_id INTEGER PRIMARY KEY AUTOINCREMENT,
    claim_id INTEGER,
    artifact_id TEXT,
    authority TEXT,
    selector_type TEXT,
    selector TEXT,
    byte_start INTEGER,
    byte_end INTEGER,
    excerpt TEXT,
    content_hash TEXT,
    verification_run_id TEXT,
    created_at TEXT NOT NULL
);

-- Source query recipes
CREATE TABLE IF NOT EXISTS query_recipes (
    recipe_id INTEGER PRIMARY KEY AUTOINCREMENT,
    language TEXT NOT NULL,
    region TEXT,
    query TEXT NOT NULL,
    last_run TEXT,
    new_source_yield INTEGER DEFAULT 0,
    verified_deal_yield INTEGER DEFAULT 0,
    false_positive_rate REAL DEFAULT 0,
    state TEXT DEFAULT 'active'
);

-- Model ledger (D0-03)
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
    created_at TEXT NOT NULL,
    speed_tokens_per_sec REAL,
    quantization TEXT DEFAULT 'UNKNOWN',
    notes TEXT,
    provenance_source TEXT,
    provenance_authority TEXT,
    provenance_confidence REAL,
    context_advertised INTEGER,
    context_effective_estimate INTEGER
);

CREATE TABLE IF NOT EXISTS model_providers (
    model_id TEXT NOT NULL,
    provider_id TEXT NOT NULL,
    offer_type TEXT,
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    PRIMARY KEY (model_id, provider_id)
);

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

-- Serving endpoints and quota policies (D0-04)
CREATE TABLE IF NOT EXISTS serving_endpoints (
    endpoint_id TEXT PRIMARY KEY,
    model_id TEXT NOT NULL,
    aggregator_id TEXT,
    serving_provider_id TEXT NOT NULL,
    provider_tag TEXT,
    variant TEXT,
    quantization TEXT DEFAULT 'UNKNOWN',
    context_tokens INTEGER,
    max_prompt_tokens INTEGER,
    max_output_tokens INTEGER,
    input_per_m REAL,
    output_per_m REAL,
    request_price REAL,
    image_price REAL,
    supports_tools INTEGER DEFAULT 0,
    supports_json_schema INTEGER DEFAULT 0,
    supports_stream INTEGER DEFAULT 1,
    supports_caching INTEGER DEFAULT 0,
    latency_p50_ms REAL,
    latency_p75_ms REAL,
    latency_p90_ms REAL,
    latency_p99_ms REAL,
    throughput_p50_tps REAL,
    throughput_p75_tps REAL,
    throughput_p90_tps REAL,
    throughput_p99_tps REAL,
    uptime_5m REAL,
    uptime_30m REAL,
    uptime_1d REAL,
    availability_state TEXT DEFAULT 'UNKNOWN',
    is_free INTEGER DEFAULT 0,
    free_mechanism TEXT,
    quota_rpd INTEGER,
    quota_rpm INTEGER,
    quota_tpd INTEGER,
    observed_at TEXT NOT NULL,
    source_url TEXT,
    raw_observation_hash TEXT
);

CREATE TABLE IF NOT EXISTS quota_policies (
    policy_id INTEGER PRIMARY KEY AUTOINCREMENT,
    provider TEXT NOT NULL,
    plan TEXT DEFAULT 'free',
    model_id TEXT,
    metric TEXT NOT NULL,
    limit_value INTEGER,
    window TEXT,
    condition TEXT,
    reset_rule TEXT,
    source TEXT,
    observed_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS performance_observations (
    obs_id INTEGER PRIMARY KEY AUTOINCREMENT,
    endpoint_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    ttft_ms REAL,
    throughput_tps REAL,
    status_code INTEGER,
    is_429 INTEGER DEFAULT 0,
    source TEXT DEFAULT 'dell_probe',
    sample_n INTEGER DEFAULT 1,
    window TEXT
);

-- P0 hardening (D0-06)
CREATE TABLE IF NOT EXISTS offer_assertions (
    assertion_id INTEGER PRIMARY KEY AUTOINCREMENT,
    offer_id TEXT NOT NULL,
    field TEXT NOT NULL,
    normalized_value TEXT,
    claim_id INTEGER,
    observation_id INTEGER,
    valid_from TEXT NOT NULL,
    valid_until TEXT,
    confidence REAL DEFAULT 0.5,
    authority TEXT,
    state TEXT DEFAULT 'active',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS verification_dimensions (
    dimension_id INTEGER PRIMARY KEY AUTOINCREMENT,
    offer_id TEXT NOT NULL,
    dimension TEXT NOT NULL,
    status TEXT NOT NULL,
    checked_at TEXT,
    source_url TEXT,
    confidence REAL DEFAULT 0.5,
    details TEXT,
    created_at TEXT NOT NULL
);

-- Oracle-1 (D0-07)
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

-- Indexes for the added tables
CREATE INDEX IF NOT EXISTS idx_models_family ON models(family);
CREATE INDEX IF NOT EXISTS idx_prices_model ON model_prices(model_id);
CREATE INDEX IF NOT EXISTS idx_prices_provider ON model_prices(provider_id);
CREATE INDEX IF NOT EXISTS idx_providers_model ON model_providers(model_id);
CREATE INDEX IF NOT EXISTS idx_events_model ON model_events(model_id);
CREATE INDEX IF NOT EXISTS idx_endpoints_model ON serving_endpoints(model_id);
CREATE INDEX IF NOT EXISTS idx_endpoints_provider ON serving_endpoints(serving_provider_id);
CREATE INDEX IF NOT EXISTS idx_endpoints_free ON serving_endpoints(is_free);
CREATE INDEX IF NOT EXISTS idx_quota_provider ON quota_policies(provider);
CREATE INDEX IF NOT EXISTS idx_quota_model ON quota_policies(model_id);
CREATE INDEX IF NOT EXISTS idx_perf_endpoint ON performance_observations(endpoint_id);
CREATE INDEX IF NOT EXISTS idx_perf_time ON performance_observations(timestamp);
CREATE INDEX IF NOT EXISTS idx_assertions_offer ON offer_assertions(offer_id);
CREATE INDEX IF NOT EXISTS idx_assertions_field ON offer_assertions(field);
CREATE INDEX IF NOT EXISTS idx_assertions_state ON offer_assertions(state);
CREATE INDEX IF NOT EXISTS idx_vdim_offer ON verification_dimensions(offer_id);
CREATE INDEX IF NOT EXISTS idx_vdim_dimension ON verification_dimensions(dimension);
CREATE INDEX IF NOT EXISTS idx_neg_obs_model ON negative_observations(model_id);
CREATE INDEX IF NOT EXISTS idx_neg_obs_field ON negative_observations(field);
CREATE INDEX IF NOT EXISTS idx_reconc_offer ON claim_reconciliation(offer_id);
CREATE INDEX IF NOT EXISTS idx_access_offer ON economic_access(offer_id);
