import datetime as dt
import os
import sqlite3
import uuid
from pathlib import Path
from typing import Any, Optional

import aiosqlite

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"


def _adapt_date(d: dt.date) -> str:
    return d.isoformat()


def _convert_date(value: bytes) -> dt.date:
    return dt.date.fromisoformat(value.decode())


def _adapt_datetime(d: dt.datetime) -> str:
    return d.isoformat()


def _convert_datetime(value: bytes) -> dt.datetime:
    return dt.datetime.fromisoformat(value.decode())


def _convert_bool(value: bytes) -> bool:
    return bool(int(value))


sqlite3.register_adapter(dt.date, _adapt_date)
sqlite3.register_adapter(dt.datetime, _adapt_datetime)
sqlite3.register_adapter(uuid.UUID, str)
sqlite3.register_converter("DATE", _convert_date)
sqlite3.register_converter("TIMESTAMPTZ", _convert_datetime)
sqlite3.register_converter("BOOLEAN", _convert_bool)


def _placeholders(sql: str) -> str:
    # asyncpg's $1, $2, ... is identical to SQLite's numbered-parameter
    # syntax ?1, ?2, ... (including reuse of the same number twice, which
    # tasks.py's "WHERE id = $1 OR series_id = $1" relies on).
    return sql.replace("$", "?")


def _split_statements(script: str) -> list[str]:
    # sqlite3.Cursor.execute() only accepts one statement at a time, so a
    # migration file with several needs splitting. executescript() would do
    # that for us but always force-commits first, which would defeat running
    # the whole file as one transaction below. complete_statement() finds
    # statement boundaries correctly around comments/string literals.
    statements = []
    buf = ""
    for line in script.splitlines(keepends=True):
        buf += line
        if buf.strip() and sqlite3.complete_statement(buf):
            statements.append(buf.strip())
            buf = ""
    return statements


class Transaction:
    def __init__(self, conn: aiosqlite.Connection):
        self._conn = conn

    async def __aenter__(self) -> "Transaction":
        await self._conn.execute("BEGIN IMMEDIATE")
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if exc_type is None:
            await self._conn.commit()
        else:
            await self._conn.rollback()


class Database:
    def __init__(self, conn: aiosqlite.Connection):
        self._conn = conn

    async def fetch(self, sql: str, *args: Any) -> list[sqlite3.Row]:
        cursor = await self._conn.execute(_placeholders(sql), args)
        rows = await cursor.fetchall()
        await cursor.close()
        return rows

    async def fetchrow(self, sql: str, *args: Any) -> Optional[sqlite3.Row]:
        cursor = await self._conn.execute(_placeholders(sql), args)
        row = await cursor.fetchone()
        await cursor.close()
        return row

    async def fetchval(self, sql: str, *args: Any) -> Any:
        row = await self.fetchrow(sql, *args)
        return row[0] if row is not None else None

    async def execute(self, sql: str, *args: Any) -> None:
        await self._conn.execute(_placeholders(sql), args)

    def transaction(self) -> Transaction:
        return Transaction(self._conn)

    async def close(self) -> None:
        await self._conn.close()


async def create_pool() -> Database:
    path = os.environ["DATABASE_URL"]
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    # isolation_level=None puts the connection in real autocommit mode: every
    # statement lands immediately unless it's inside an explicit BEGIN (see
    # Transaction), matching what the call sites above assume.
    conn = await aiosqlite.connect(path, detect_types=sqlite3.PARSE_DECLTYPES, isolation_level=None)
    conn.row_factory = sqlite3.Row
    await conn.execute("PRAGMA journal_mode = WAL")
    await conn.execute("PRAGMA foreign_keys = ON")
    await conn.execute("PRAGMA busy_timeout = 5000")
    await conn.create_function("gen_random_uuid", 0, lambda: str(uuid.uuid4()))
    await conn.create_function("now", 0, lambda: dt.datetime.now(dt.timezone.utc).isoformat())
    db = Database(conn)
    await _migrate(db)
    return db


async def _migrate(db: Database) -> None:
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            filename TEXT PRIMARY KEY,
            applied_at TIMESTAMPTZ NOT NULL DEFAULT (now())
        )
        """
    )
    applied = {r["filename"] for r in await db.fetch("SELECT filename FROM schema_migrations")}
    for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
        if path.name in applied:
            continue
        async with db.transaction():
            for statement in _split_statements(path.read_text()):
                await db._conn.execute(statement)
            await db._conn.execute(
                "INSERT INTO schema_migrations (filename) VALUES (?1)", (path.name,)
            )
