import datetime as dt
import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, field_validator

from app import stream

router = APIRouter()

MONTH_ABBR = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
TASK_COLUMNS = "id, title, assignee_id, due_date, due_time_hint, completed_at"


class TaskIn(BaseModel):
    title: str
    assignee_id: Optional[uuid.UUID] = None
    due_date: Optional[dt.date] = None
    due_time_hint: str = "none"
    rrule: Optional[str] = None
    rrule_until: Optional[str] = None
    rrule_count: Optional[int] = None

    @field_validator("assignee_id", "due_date", "rrule", "rrule_until", "rrule_count", mode="before")
    @classmethod
    def blank_to_none(cls, v):
        return None if v == "" else v


class TaskPatch(BaseModel):
    title: Optional[str] = None
    assignee_id: Optional[uuid.UUID] = None
    due_date: Optional[dt.date] = None
    due_time_hint: Optional[str] = None


class CompleteIn(BaseModel):
    done: bool


def _due_label(due_date: Optional[dt.date], days_late: int) -> str:
    if due_date is None:
        return ""
    if days_late > 0:
        return f"Due {MONTH_ABBR[due_date.month - 1]} {due_date.day} · {days_late} day{'s' if days_late != 1 else ''} late"
    return "Due today"


def _to_task(row, today: dt.date) -> dict:
    due_date = row["due_date"]
    completed = row["completed_at"] is not None
    days_late = max(0, (today - due_date).days) if due_date and not completed else 0
    return {
        "id": str(row["id"]),
        "title": row["title"],
        "assignee_id": str(row["assignee_id"]) if row["assignee_id"] else None,
        "due_date": due_date.isoformat() if due_date else None,
        "due_time_hint": row["due_time_hint"],
        "completed_at": row["completed_at"].isoformat() if row["completed_at"] else None,
        "days_late": days_late,
        "due_label": _due_label(due_date, days_late),
    }


@router.get("/api/day")
async def day(date: dt.date, request: Request):
    rows = await request.app.state.db.fetch(
        f"SELECT {TASK_COLUMNS} FROM task "
        "WHERE due_date = $1 OR (due_date < $1 AND completed_at IS NULL) "
        "ORDER BY due_date",
        date,
    )
    return {
        "date": date.isoformat(),
        "weather": None,
        "vacation": None,
        "events": [],
        "tasks": [_to_task(r, date) for r in rows],
        "upcoming": [],
    }


@router.post("/api/tasks", status_code=201)
async def create_task(body: TaskIn, request: Request):
    row = await request.app.state.db.fetchrow(
        f"INSERT INTO task (title, assignee_id, due_date, due_time_hint, rrule, rrule_until, rrule_count) "
        f"VALUES ($1, $2, $3, $4, $5, $6, $7) RETURNING {TASK_COLUMNS}",
        body.title,
        body.assignee_id,
        body.due_date,
        body.due_time_hint,
        body.rrule,
        body.rrule_until,
        body.rrule_count,
    )
    stream.broadcast("tasks")
    return _to_task(row, dt.date.today())


@router.patch("/api/tasks/{task_id}")
async def update_task(task_id: uuid.UUID, body: TaskPatch, request: Request):
    fields = body.model_dump(exclude_unset=True)
    if not fields:
        row = await request.app.state.db.fetchrow(f"SELECT {TASK_COLUMNS} FROM task WHERE id = $1", task_id)
    else:
        set_clause = ", ".join(f"{k} = ${i + 2}" for i, k in enumerate(fields))
        row = await request.app.state.db.fetchrow(
            f"UPDATE task SET {set_clause} WHERE id = $1 RETURNING {TASK_COLUMNS}",
            task_id,
            *fields.values(),
        )
    if row is None:
        raise HTTPException(404, "task not found")
    stream.broadcast("tasks")
    return _to_task(row, dt.date.today())


@router.post("/api/tasks/{task_id}/complete")
async def complete_task(task_id: uuid.UUID, body: CompleteIn, request: Request):
    row = await request.app.state.db.fetchrow(
        f"UPDATE task SET completed_at = $2 WHERE id = $1 RETURNING {TASK_COLUMNS}",
        task_id,
        dt.datetime.now(dt.timezone.utc) if body.done else None,
    )
    if row is None:
        raise HTTPException(404, "task not found")
    stream.broadcast("tasks")
    return _to_task(row, dt.date.today())
