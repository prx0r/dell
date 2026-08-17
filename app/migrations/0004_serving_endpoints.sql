-- D0-01: Serving endpoints and quota policies

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

CREATE INDEX IF NOT EXISTS idx_endpoints_model ON serving_endpoints(model_id);
CREATE INDEX IF NOT EXISTS idx_endpoints_provider ON serving_endpoints(serving_provider_id);
CREATE INDEX IF NOT EXISTS idx_endpoints_free ON serving_endpoints(is_free);
CREATE INDEX IF NOT EXISTS idx_quota_provider ON quota_policies(provider);
CREATE INDEX IF NOT EXISTS idx_quota_model ON quota_policies(model_id);
CREATE INDEX IF NOT EXISTS idx_perf_endpoint ON performance_observations(endpoint_id);
CREATE INDEX IF NOT EXISTS idx_perf_time ON performance_observations(timestamp);
