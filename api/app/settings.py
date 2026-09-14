import os
from typing import Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel

from app import stream

router = APIRouter()


class DisplayPatch(BaseModel):
    layout: Optional[str] = None
    show_weather: Optional[bool] = None
    show_upcoming: Optional[bool] = None
    time_format: Optional[str] = None


def _to_display(row) -> dict:
    return {
        "layout": row["layout"],
        "show_weather": row["show_weather"],
        "show_upcoming": row["show_upcoming"],
        "time_format": row["time_format"],
        # The TV and the phone app are two different hostnames now
        # (calendar-read.home vs. calendar.home — see Caddyfile), so the
        # TV's own page origin is no longer a phone-reachable URL and
        # js/tv.js's location.origin fallback would point the QR code back
        # at the read-only view. PHONE_URL is a fixed hostname, not an IP,
        # so — unlike the old LAN-IP-drift concern this comment used to
        # describe — it doesn't need updating unless the hostname itself
        # changes.
        "phone_url": os.environ.get("PHONE_URL"),
    }


@router.get("/api/settings/display")
async def get_display(request: Request):
    row = await request.app.state.db.fetchrow("SELECT * FROM display_settings WHERE id = true")
    return _to_display(row)


@router.patch("/api/settings/display")
async def update_display(body: DisplayPatch, request: Request):
    fields = body.model_dump(exclude_unset=True)
    if fields:
        set_clause = ", ".join(f"{k} = ${i + 1}" for i, k in enumerate(fields))
        await request.app.state.db.execute(
            f"UPDATE display_settings SET {set_clause} WHERE id = true", *fields.values()
        )
        stream.broadcast("settings")
    row = await request.app.state.db.fetchrow("SELECT * FROM display_settings WHERE id = true")
    return _to_display(row)
