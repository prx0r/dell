-- D0-01: Verification and tool events

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
