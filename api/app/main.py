import os
from contextlib import asynccontextmanager

import asyncpg
from fastapi import FastAPI


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.db = await asyncpg.create_pool(os.environ["DATABASE_URL"])
    yield
    await app.state.db.close()


app = FastAPI(lifespan=lifespan)


@app.get("/api/health")
async def health():
    await app.state.db.fetchval("SELECT 1")
    return {"status": "ok"}
