-- Timestamps are ISO-8601 UTC strings.

CREATE TABLE page_state (
    page TEXT PRIMARY KEY,
    response_json TEXT,
    responded_at TEXT,
    acknowledged_at TEXT
);

CREATE TABLE page_opens (
    id INTEGER PRIMARY KEY,
    page TEXT NOT NULL,
    opened_at TEXT NOT NULL
);

CREATE INDEX idx_page_opens_page ON page_opens (page, opened_at);
