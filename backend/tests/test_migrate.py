import sqlite3
from pathlib import Path

import pytest

from app.config import Settings
from app.db.connection import connect
from app.db.migrate import latest_version, list_migrations, run_migrations


def _tables(path: Path) -> set[str]:
    with connect(path, read_only=True) as conn:
        rows = conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        return {row["name"] for row in rows}


def test_fresh_database_gets_full_schema(settings: Settings) -> None:
    version = run_migrations(settings.database_path, settings.migrations_dir)
    assert version == latest_version(settings.migrations_dir) >= 1
    assert {"page_state", "page_opens"} <= _tables(settings.database_path)


def test_rerun_is_a_no_op_and_keeps_data(migrated: Settings) -> None:
    with connect(migrated.database_path) as conn:
        conn.execute("INSERT INTO page_state (page, response_json) VALUES ('demo', '{}')")
    version = run_migrations(migrated.database_path, migrated.migrations_dir)
    assert version == latest_version(migrated.migrations_dir)
    with connect(migrated.database_path, read_only=True) as conn:
        assert conn.execute("SELECT COUNT(*) FROM page_state").fetchone()[0] == 1


def test_new_migration_is_applied_on_top(tmp_path: Path) -> None:
    migrations = tmp_path / "migrations"
    migrations.mkdir()
    db = tmp_path / "test.db"
    (migrations / "0001_first.sql").write_text("CREATE TABLE a (id INTEGER PRIMARY KEY);")
    assert run_migrations(db, migrations) == 1
    (migrations / "0002_second.sql").write_text("CREATE TABLE b (id INTEGER PRIMARY KEY);")
    assert run_migrations(db, migrations) == 2
    assert {"a", "b"} <= _tables(db)


def test_failed_migration_rolls_back_completely(tmp_path: Path) -> None:
    migrations = tmp_path / "migrations"
    migrations.mkdir()
    db = tmp_path / "test.db"
    (migrations / "0001_first.sql").write_text("CREATE TABLE a (id INTEGER PRIMARY KEY);")
    (migrations / "0002_broken.sql").write_text(
        "CREATE TABLE b (id INTEGER PRIMARY KEY);\nINSERT INTO missing VALUES (1);"
    )
    with pytest.raises(sqlite3.Error):
        run_migrations(db, migrations)
    assert _tables(db) == {"a"}
    with connect(db, read_only=True) as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 1


def test_database_newer_than_build_is_refused(migrated: Settings) -> None:
    conn = sqlite3.connect(migrated.database_path)
    conn.execute("PRAGMA user_version = 999")
    conn.close()
    with pytest.raises(RuntimeError):
        run_migrations(migrated.database_path, migrated.migrations_dir)


@pytest.mark.parametrize("names", [["0002_only.sql"], ["0001_a.sql", "0003_c.sql"], ["first.sql"]])
def test_bad_migration_numbering_is_rejected(tmp_path: Path, names: list[str]) -> None:
    for name in names:
        (tmp_path / name).write_text("SELECT 1;")
    with pytest.raises(ValueError):
        list_migrations(tmp_path)
