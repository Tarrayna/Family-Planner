#!/usr/bin/env python3
"""One-time carry-over from the old Postgres container to the new SQLite
file. This is a throwaway script — delete it once the migration is done.

Run from the repo root, after `docker compose up -d --build` on the new
SQLite-backed stack (so the schema already exists) and BEFORE tearing down
the old Postgres container/volume:

    python3 scripts/migrate_pg_to_sqlite.py

Preserves the original row ids — person.photo_path filenames are the
person id, so they must match for existing photos to keep working.
"""
import csv
import io
import json
import subprocess
import sys

PG_CONTAINER = "calendar-db-1"
API_SERVICE = "api"

PERSON_COLUMNS = ["id", "name", "color", "photo_path", "has_phone", "created_at"]
TASK_COLUMNS = [
    "id", "title", "assignee_id", "due_date", "due_time_hint", "rrule",
    "rrule_until", "rrule_count", "series_id", "completed_at", "created_at",
    "vacation_id", "checklist_group", "note",
]

IMPORT_SCRIPT = '''
import asyncio, json, sys
from dateutil import parser as dtparser
from app import db

def norm_ts(v):
    return dtparser.parse(v).isoformat() if v else None

def norm_bool(v):
    return v == "t"

async def main():
    payload = json.loads(sys.stdin.read())
    conn = await db.create_pool()
    for p in payload["people"]:
        await conn.execute(
            "INSERT INTO person (id, name, color, photo_path, has_phone, created_at) "
            "VALUES ($1, $2, $3, $4, $5, $6)",
            p["id"], p["name"], p["color"], p["photo_path"] or None,
            norm_bool(p["has_phone"]), norm_ts(p["created_at"]),
        )
    for t in payload["tasks"]:
        await conn.execute(
            "INSERT INTO task (id, title, assignee_id, due_date, due_time_hint, rrule, "
            "rrule_until, rrule_count, series_id, completed_at, created_at, vacation_id, "
            "checklist_group, note) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14)",
            t["id"], t["title"], t["assignee_id"] or None, t["due_date"] or None,
            t["due_time_hint"], t["rrule"] or None, t["rrule_until"] or None,
            int(t["rrule_count"]) if t["rrule_count"] else None,
            t["series_id"] or None, norm_ts(t["completed_at"]), norm_ts(t["created_at"]),
            t["vacation_id"] or None, t["checklist_group"] or None, t["note"] or None,
        )
    await conn.close()

asyncio.run(main())
'''


def pg_copy(columns: list[str], table: str) -> list[dict]:
    sql = f"COPY (SELECT {', '.join(columns)} FROM {table}) TO STDOUT WITH (FORMAT csv)"
    out = subprocess.run(
        ["docker", "exec", PG_CONTAINER, "psql", "-U", "planner", "-d", "planner", "-c", sql],
        check=True, capture_output=True, text=True,
    ).stdout
    return [dict(zip(columns, row)) for row in csv.reader(io.StringIO(out))]


def main() -> None:
    people = pg_copy(PERSON_COLUMNS, "person")
    tasks = pg_copy(TASK_COLUMNS, "task")
    print(f"Exporting {len(people)} people, {len(tasks)} tasks...", file=sys.stderr)

    payload = json.dumps({"people": people, "tasks": tasks})
    subprocess.run(
        ["docker", "compose", "exec", "-T", API_SERVICE, "python3", "-c", IMPORT_SCRIPT],
        input=payload, check=True, text=True,
    )
    print("Done. Verify via GET /api/people and /api/day before tearing "
          "down the old Postgres container.", file=sys.stderr)


if __name__ == "__main__":
    main()
