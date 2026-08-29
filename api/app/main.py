from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import db, people, stream, tasks


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.db = await db.create_pool()
    yield
    await app.state.db.close()


app = FastAPI(lifespan=lifespan)
app.include_router(people.router)
app.include_router(stream.router)
app.include_router(tasks.router)


@app.get("/api/health")
async def health():
    await app.state.db.fetchval("SELECT 1")
    return {"status": "ok"}
