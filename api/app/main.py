import asyncio
import datetime as dt
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import db, people, stream, tasks

RECURRENCE_JOB_INTERVAL = dt.timedelta(hours=24)


async def _recurrence_job(app: FastAPI) -> None:
    """Rolls each recurring series' materialized window forward. Runs once at
    startup (covers a container restart missing a scheduled run) and every
    RECURRENCE_JOB_INTERVAL after that, per SPEC.md §3's "nightly job"."""
    while True:
        masters = await app.state.db.fetch(
            "SELECT id, title, assignee_id, due_date, due_time_hint, rrule "
            "FROM task WHERE rrule IS NOT NULL AND due_date IS NOT NULL"
        )
        for master in masters:
            await tasks.materialize_series(app.state.db, dict(master), dt.date.today())
        await asyncio.sleep(RECURRENCE_JOB_INTERVAL.total_seconds())


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.db = await db.create_pool()
    job = asyncio.create_task(_recurrence_job(app))
    yield
    job.cancel()
    await app.state.db.close()


app = FastAPI(lifespan=lifespan)
app.include_router(people.router)
app.include_router(stream.router)
app.include_router(tasks.router)


@app.get("/api/health")
async def health():
    await app.state.db.fetchval("SELECT 1")
    return {"status": "ok"}
