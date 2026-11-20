-- Every secret word entered on the page gate. Wrong words are kept as typed;
-- a correct one is stored only as correct, never as text. Time zone and
-- approximate location are recorded as for opens.
CREATE TABLE gate_attempts (
    id INTEGER PRIMARY KEY,
    attempted_at TEXT NOT NULL,
    page TEXT NOT NULL,
    correct INTEGER NOT NULL CHECK (correct IN (0, 1)),
    word TEXT CHECK (correct = 0 OR word IS NULL),
    city TEXT,
    region TEXT,
    country TEXT,
    tz TEXT
);
