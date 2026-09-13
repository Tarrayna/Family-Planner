import asyncio
import datetime as dt
import os
import tempfile
from pathlib import Path

from app import db


def _run(coro):
    return asyncio.run(coro)


def _fresh_db(tmp: str) -> db.Database:
    os.environ["DATABASE_URL"] = str(Path(tmp) / "test.db")
    return _run(db.create_pool())


def test_migrations_apply_and_are_idempotent():
    with tempfile.TemporaryDirectory() as tmp:
        conn = _fresh_db(tmp)
        applied = _run(conn.fetch("SELECT filename FROM schema_migrations ORDER BY filename"))
        assert [r["filename"] for r in applied] == [
            "0001_person.sql", "0002_task.sql", "0003_display_settings.sql", "0004_vacation.sql",
        ]
        # Re-running the migration loop against an already-migrated database
        # must be a no-op, not a "table already exists" error.
        _run(db._migrate(conn))
        applied_again = _run(conn.fetch("SELECT filename FROM schema_migrations"))
        assert len(applied_again) == len(applied)
        _run(conn.close())


def test_boolean_round_trips_as_bool_not_int():
    with tempfile.TemporaryDirectory() as tmp:
        conn = _fresh_db(tmp)
        row = _run(conn.fetchrow(
            "INSERT INTO person (name, color, has_phone) VALUES ($1, $2, $3) "
            "RETURNING has_phone",
            "Test", "blue", True,
        ))
        assert row["has_phone"] is True
        _run(conn.close())


def test_date_round_trips_as_date_not_string():
    with tempfile.TemporaryDirectory() as tmp:
        conn = _fresh_db(tmp)
        due = dt.date(2026, 8, 24)
        row = _run(conn.fetchrow(
            "INSERT INTO task (title, due_date) VALUES ($1, $2) RETURNING due_date",
            "Pack", due,
        ))
        assert row["due_date"] == due
        assert isinstance(row["due_date"], dt.date)
        _run(conn.close())


def test_repeated_placeholder_is_reused_not_consumed():
    # tasks.py's materialize_series relies on asyncpg-style $1 reuse:
    # "WHERE id = $1 OR series_id = $1" with a single bound argument.
    with tempfile.TemporaryDirectory() as tmp:
        conn = _fresh_db(tmp)
        master = _run(conn.fetchrow(
            "INSERT INTO task (title) VALUES ($1) RETURNING id", "Series master",
        ))
        _run(conn.execute(
            "INSERT INTO task (title, series_id) VALUES ($1, $2)", "Occurrence", master["id"],
        ))
        matches = _run(conn.fetch(
            "SELECT title FROM task WHERE id = $1 OR series_id = $1", master["id"],
        ))
        assert {r["title"] for r in matches} == {"Series master", "Occurrence"}
        _run(conn.close())
