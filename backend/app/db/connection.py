"""SQLite connections. One short-lived connection per unit of work."""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

BUSY_TIMEOUT_SECONDS = 5


@contextmanager
def connect(path: Path, *, read_only: bool = False) -> Iterator[sqlite3.Connection]:
    """Open the database, commit on success, roll back on error, always close.

    A read-only connection never creates the file, so it fails if it is missing.
    """
    if read_only:
        conn = sqlite3.connect(
            f"{path.resolve().as_uri()}?mode=ro", uri=True, timeout=BUSY_TIMEOUT_SECONDS
        )
    else:
        conn = sqlite3.connect(path, timeout=BUSY_TIMEOUT_SECONDS)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        with conn:
            yield conn
    finally:
        conn.close()
