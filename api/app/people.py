import os
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, HTTPException, Request, Response, UploadFile
from itsdangerous import URLSafeSerializer
from pydantic import BaseModel

from app import stream

router = APIRouter()
session_signer = URLSafeSerializer(os.environ["SESSION_SECRET"], salt="planner-session")

PHOTOS_DIR = Path("photos")
PHOTOS_DIR.mkdir(exist_ok=True)
ALLOWED_PHOTO_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}


class PersonIn(BaseModel):
    name: str
    color: str
    has_phone: bool = True


class PersonPatch(BaseModel):
    name: Optional[str] = None
    color: Optional[str] = None
    has_phone: Optional[bool] = None


class SessionIn(BaseModel):
    person_id: uuid.UUID


def _to_person(row) -> dict:
    return {
        "id": str(row["id"]),
        "name": row["name"],
        "color": row["color"],
        "photo_url": f"/photos/{row['photo_path']}" if row["photo_path"] else None,
        "has_phone": row["has_phone"],
    }


@router.get("/api/people")
async def list_people(request: Request):
    rows = await request.app.state.db.fetch(
        "SELECT id, name, color, photo_path, has_phone FROM person ORDER BY created_at"
    )
    return [_to_person(r) for r in rows]


@router.post("/api/people", status_code=201)
async def create_person(body: PersonIn, request: Request):
    row = await request.app.state.db.fetchrow(
        "INSERT INTO person (name, color, has_phone) VALUES ($1, $2, $3) "
        "RETURNING id, name, color, photo_path, has_phone",
        body.name,
        body.color,
        body.has_phone,
    )
    stream.broadcast("people")
    return _to_person(row)


@router.patch("/api/people/{person_id}")
async def update_person(person_id: uuid.UUID, body: PersonPatch, request: Request):
    fields = body.model_dump(exclude_unset=True)
    if not fields:
        row = await request.app.state.db.fetchrow(
            "SELECT id, name, color, photo_path, has_phone FROM person WHERE id = $1", person_id
        )
    else:
        set_clause = ", ".join(f"{k} = ${i + 2}" for i, k in enumerate(fields))
        row = await request.app.state.db.fetchrow(
            f"UPDATE person SET {set_clause} WHERE id = $1 "
            "RETURNING id, name, color, photo_path, has_phone",
            person_id,
            *fields.values(),
        )
    if row is None:
        raise HTTPException(404, "person not found")
    stream.broadcast("people")
    return _to_person(row)


@router.post("/api/people/{person_id}/photo")
async def upload_photo(person_id: uuid.UUID, request: Request, file: UploadFile = File(...)):
    ext = ALLOWED_PHOTO_TYPES.get(file.content_type)
    if ext is None:
        raise HTTPException(415, "photo must be JPEG, PNG, or WebP")
    filename = f"{person_id}{ext}"
    (PHOTOS_DIR / filename).write_bytes(await file.read())
    row = await request.app.state.db.fetchrow(
        "UPDATE person SET photo_path = $2 WHERE id = $1 "
        "RETURNING id, name, color, photo_path, has_phone",
        person_id,
        filename,
    )
    if row is None:
        raise HTTPException(404, "person not found")
    stream.broadcast("people")
    return _to_person(row)


@router.delete("/api/people/{person_id}", status_code=204)
async def delete_person(person_id: uuid.UUID, request: Request):
    await request.app.state.db.execute("DELETE FROM person WHERE id = $1", person_id)
    stream.broadcast("people")


@router.post("/api/session", status_code=204)
async def set_session(body: SessionIn, response: Response):
    response.set_cookie(
        "planner_person",
        session_signer.dumps(str(body.person_id)),
        max_age=60 * 60 * 24 * 400,
        httponly=True,
        secure=True,
        samesite="lax",
    )
