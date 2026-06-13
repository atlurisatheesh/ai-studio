"""Avatar router — talking-head jobs from the user's OWN photo.

Privacy by design: no face is AI-generated from a prompt and nothing is
sent anywhere. The creator uploads their portrait, the lipsync runs on
this machine.
"""
import uuid
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends

from core.config import UPLOAD_DIR
from core.db import get_db
from core.security import CurrentUser, get_current_user
from core.uploads import read_capped
from engines import avatar as avatar_engine
from routers.voice import _resolve_clone

router = APIRouter(prefix="/avatar", tags=["avatar"])

IMAGE_EXTS = {"jpg", "jpeg", "png", "webp"}


@router.post("/generate")
async def avatar_generate(
    script: str = Form(..., min_length=1, max_length=2000),
    voice: str = Form("studio"),
    portrait: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    suffix = (portrait.filename or "face.png").rsplit(".", 1)[-1].lower()
    if suffix not in IMAGE_EXTS:
        raise HTTPException(status_code=400, detail="Upload a portrait image (jpg/png/webp)")
    image_path = UPLOAD_DIR / f"portrait_{uuid.uuid4().hex}.{suffix}"
    image_path.write_bytes(await read_capped(portrait))

    clone_sample = await _resolve_clone(voice, user["id"])
    job = await avatar_engine.create_job(user["id"], script, voice, str(image_path), clone_sample)
    job["portrait_url"] = f"/api/assets/{image_path.name}"
    return job


@router.get("/jobs/{job_id}")
async def avatar_job_status(job_id: str, user: CurrentUser):
    db = await get_db()
    cur = await db.execute(
        "SELECT * FROM avatar_jobs WHERE id = ? AND user_id = ?", (job_id, user["id"])
    )
    row = await cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Job not found")
    job = dict(row)
    from pathlib import Path
    job["portrait_url"] = f"/api/assets/{Path(job['image_path']).name}"
    job.pop("image_path", None)
    return job


@router.get("/jobs")
async def avatar_jobs(user: CurrentUser, limit: int = 30):
    db = await get_db()
    cur = await db.execute(
        "SELECT id, script, voice, status, file, url, error, created_at, completed_at "
        "FROM avatar_jobs WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
        (user["id"], limit),
    )
    return [dict(r) for r in await cur.fetchall()]
