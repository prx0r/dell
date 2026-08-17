-- D0-01: Claims and evidence tables

CREATE TABLE IF NOT EXISTS claims (
    claim_id INTEGER PRIMARY KEY AUTOINCREMENT,
    offer_id TEXT NOT NULL,
    claim_type TEXT NOT NULL,
    claim_value TEXT NOT NULL,
    source_observation_id INTEGER,
    confidence REAL DEFAULT 0.5,
    created_at TEXT NOT NULL
);

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

CREATE TABLE IF NOT EXISTS verification_checks (
    check_id INTEGER PRIMARY KEY AUTOINCREMENT,
    offer_id TEXT NOT NULL,
    check_type TEXT NOT NULL,
    status TEXT NOT NULL,
    checked_at TEXT NOT NULL,
    details TEXT,
    confidence REAL DEFAULT 0.5
);
