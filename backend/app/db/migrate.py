"""Applies numbered SQL migrations, tracked with PRAGMA user_version.

Files are named NNNN_description.sql. Each is applied once, in order, inside a
transaction together with the version bump, so a failure leaves the database
at the previous version.
"""

import re
import sqlite3
from pathlib import Path

MIGRATION_NAME = re.compile(r"^(\d{4})_[a-z0-9_]+\.sql$")


def list_migrations(migrations_dir: Path) -> list[tuple[int, Path]]:
    migrations = []
    for path in sorted(migrations_dir.glob("*.sql")):
        match = MIGRATION_NAME.match(path.name)
        if not match:
            raise ValueError(f"Invalid migration file name: {path.name}")
        migrations.append((int(match.group(1)), path))
    numbers = [number for number, _ in migrations]
    if numbers != list(range(1, len(numbers) + 1)):
        raise ValueError(f"Migrations must be numbered 0001..N without gaps: {numbers}")
    return migrations


def latest_version(migrations_dir: Path) -> int:
    return len(list_migrations(migrations_dir))


def current_version(conn: sqlite3.Connection) -> int:
    return conn.execute("PRAGMA user_version").fetchone()[0]


def run_migrations(database_path: Path, migrations_dir: Path) -> int:
    """Bring the database up to date and return its version."""
    migrations = list_migrations(migrations_dir)
    database_path.parent.mkdir(parents=True, exist_ok=True)
    # Autocommit mode: each migration manages its own transaction below.
    conn = sqlite3.connect(database_path, isolation_level=None)
    try:
        version = current_version(conn)
        if version > len(migrations):
            raise RuntimeError(
                f"Database is at version {version}, newer than this build ({len(migrations)})"
            )
        for number, path in migrations:
            if number <= version:
                continue
            try:
                conn.executescript(
                    f"BEGIN;\n{path.read_text()}\nPRAGMA user_version = {number};\nCOMMIT;"
                )
            except sqlite3.Error:
                if conn.in_transaction:
                    conn.execute("ROLLBACK")
                raise
        return current_version(conn)
    finally:
        conn.close()
