import asyncio
import json
from typing import AsyncIterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

router = APIRouter()
_subscribers: set[asyncio.Queue] = set()


def broadcast(kind: str) -> None:
    for q in _subscribers:
        q.put_nowait(kind)


async def _events() -> AsyncIterator[str]:
    q: asyncio.Queue = asyncio.Queue()
    _subscribers.add(q)
    try:
        while True:
            try:
                kind = await asyncio.wait_for(q.get(), timeout=15)
                yield f"data: {json.dumps({'type': kind})}\n\n"
            except asyncio.TimeoutError:
                yield ": keepalive\n\n"
    finally:
        _subscribers.discard(q)


@router.get("/api/stream")
async def stream():
    return StreamingResponse(
        _events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
