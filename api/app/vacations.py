import datetime as dt
from typing import Iterable, Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel

from app import stream

router = APIRouter()

# Fixed editable template (SPEC.md §8 resolved 2026-08-29): every new
# vacation gets copied in as real checklist tasks, due 3 days before
# departure. Family edits/completes them like any other task from there —
# no "learn from past trips" history to manage.
CHECKLIST_TEMPLATE = [
    ("House", [
        ("Hold the mail", None),
        ("Set the thermostat", None),
        ("Take out all the trash", None),
        ("Lock up and set the alarm", None),
    ]),
    ("Kids", [
        ("Pack weather-appropriate clothes", None),
        ("Pack any medications", None),
        ("Charge tablets/devices", None),
    ]),
    ("Travel", [
        ("Fill up the car", None),
        ("Print or download reservations", None),
        ("Check the weather at the destination", None),
    ]),
]


class VacationIn(BaseModel):
    name: str
    starts_on: dt.date
    ends_on: dt.date
    pause_repeating: bool = True
    pause_overdue: bool = True
    hide_tasks_on_tv: bool = True
    keep_calendar_events: bool = False


def date_in_any_window(d: dt.date, windows: Iterable[tuple[dt.date, dt.date]]) -> bool:
    return any(start <= d <= end for start, end in windows)


def days_late(
    due_date: dt.date, today: dt.date, pause_windows: Iterable[tuple[dt.date, dt.date]] = ()
) -> int:
    """Days between due_date and today, minus any days inside a
    pause_overdue vacation window (SPEC.md §3: those days don't count)."""
    if due_date is None or due_date >= today:
        return 0
    total = (today - due_date).days
    yesterday = today - dt.timedelta(days=1)
    paused = 0
    for start, end in pause_windows:
        overlap_start = max(due_date, start)
        overlap_end = min(yesterday, end)
        if overlap_start <= overlap_end:
            paused += (overlap_end - overlap_start).days + 1
    return max(0, total - paused)


async def pause_overdue_windows(db, start: dt.date, end: dt.date) -> list[tuple[dt.date, dt.date]]:
    rows = await db.fetch(
        "SELECT starts_on, ends_on FROM vacation WHERE pause_overdue = true "
        "AND starts_on <= $2 AND ends_on >= $1",
        start,
        end,
    )
    return [(r["starts_on"], r["ends_on"]) for r in rows]


async def pause_repeating_windows(db, start: dt.date, end: dt.date) -> list[tuple[dt.date, dt.date]]:
    rows = await db.fetch(
        "SELECT starts_on, ends_on FROM vacation WHERE pause_repeating = true "
        "AND starts_on <= $2 AND ends_on >= $1",
        start,
        end,
    )
    return [(r["starts_on"], r["ends_on"]) for r in rows]


async def active_vacation(db, on: dt.date) -> Optional[dict]:
    row = await db.fetchrow(
        "SELECT * FROM vacation WHERE starts_on <= $1 AND ends_on >= $1 ORDER BY starts_on LIMIT 1", on
    )
    if row is None:
        return None
    return {
        "id": str(row["id"]),
        "name": row["name"],
        "starts_on": row["starts_on"].isoformat(),
        "ends_on": row["ends_on"].isoformat(),
        "pause_overdue": row["pause_overdue"],
        "hide_tasks_on_tv": row["hide_tasks_on_tv"],
    }


def _to_checklist_item(row) -> dict:
    return {
        "id": str(row["id"]),
        "title": row["title"],
        "note": row["note"],
        "assignee_id": str(row["assignee_id"]) if row["assignee_id"] else None,
        "done": row["completed_at"] is not None,
    }


async def _to_vacation(db, row) -> dict:
    items = await db.fetch(
        "SELECT id, title, note, assignee_id, completed_at, checklist_group "
        "FROM task WHERE vacation_id = $1 ORDER BY created_at",
        row["id"],
    )
    groups: dict[str, list[dict]] = {}
    order: list[str] = []
    for item in items:
        group = item["checklist_group"]
        if group not in groups:
            groups[group] = []
            order.append(group)
        groups[group].append(_to_checklist_item(item))
    return {
        "id": str(row["id"]),
        "name": row["name"],
        "starts_on": row["starts_on"].isoformat(),
        "ends_on": row["ends_on"].isoformat(),
        "pause_repeating": row["pause_repeating"],
        "pause_overdue": row["pause_overdue"],
        "hide_tasks_on_tv": row["hide_tasks_on_tv"],
        "keep_calendar_events": row["keep_calendar_events"],
        "checklist": [{"group": g, "items": groups[g]} for g in order],
    }


@router.get("/api/vacations")
async def list_vacations(request: Request):
    rows = await request.app.state.db.fetch("SELECT * FROM vacation ORDER BY starts_on DESC")
    return [await _to_vacation(request.app.state.db, row) for row in rows]


@router.post("/api/vacations", status_code=201)
async def create_vacation(body: VacationIn, request: Request):
    db = request.app.state.db
    row = await db.fetchrow(
        "INSERT INTO vacation (name, starts_on, ends_on, pause_repeating, pause_overdue, "
        "hide_tasks_on_tv, keep_calendar_events) VALUES ($1, $2, $3, $4, $5, $6, $7) RETURNING *",
        body.name,
        body.starts_on,
        body.ends_on,
        body.pause_repeating,
        body.pause_overdue,
        body.hide_tasks_on_tv,
        body.keep_calendar_events,
    )
    checklist_due = body.starts_on - dt.timedelta(days=3)
    for group, items in CHECKLIST_TEMPLATE:
        for title, note in items:
            await db.execute(
                "INSERT INTO task (title, note, due_date, vacation_id, checklist_group) "
                "VALUES ($1, $2, $3, $4, $5)",
                title,
                note,
                checklist_due,
                row["id"],
                group,
            )
    stream.broadcast("vacations")
    stream.broadcast("tasks")
    return await _to_vacation(db, row)
