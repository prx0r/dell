-- D0-01: P0 hardening tables

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

CREATE INDEX IF NOT EXISTS idx_assertions_offer ON offer_assertions(offer_id);
CREATE INDEX IF NOT EXISTS idx_assertions_field ON offer_assertions(field);
CREATE INDEX IF NOT EXISTS idx_assertions_state ON offer_assertions(state);
CREATE INDEX IF NOT EXISTS idx_vdim_offer ON verification_dimensions(offer_id);
CREATE INDEX IF NOT EXISTS idx_vdim_dimension ON verification_dimensions(dimension);
