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
        # No server config for this: the TV's own page origin (LAN IP or
        # planner.home, whatever it was loaded as) already is a phone-
        # reachable URL, so js/tv.js falls back to location.origin when this
        # is null. A static value here would just be one more place the LAN
        # IP drift (see Caddyfile) could go stale.
        "phone_url": None,
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
