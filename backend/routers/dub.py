"""Dubbing router — translate + re-voice (+ optional lip-resync) of an upload.

Privacy: the uploaded clip never leaves this machine. Only the transcript
text crosses the wire if LLM_PROVIDER=grok (the one disclosed exception).
"""
import uuid
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends

from core.config import UPLOAD_DIR
from core.db import get_db
from core.security import CurrentUser, get_current_user
from core.uploads import read_capped
from engines import dub as dub_engine, tts
from routers.voice import _resolve_clone, AUDIO_EXTS

router = APIRouter(prefix="/dub", tags=["dub"])

_GLOBAL_LANGUAGES = [
    {"code": "en", "name": "English"}, {"code": "es", "name": "Spanish"},
    {"code": "fr", "name": "French"}, {"code": "de", "name": "German"},
    {"code": "ja", "name": "Japanese"}, {"code": "zh", "name": "Chinese (Mandarin)"},
    {"code": "ar", "name": "Arabic"}, {"code": "pt", "name": "Portuguese"},
    {"code": "ru", "name": "Russian"}, {"code": "ko", "name": "Korean"},
]


@router.get("/languages")
async def dub_languages():
    """Target languages for dubbing — Indian languages (TTS-capable) first, then common globals."""
    seen = set()
    out = []
    for lang in [*tts.INDIC_LANGUAGES, *_GLOBAL_LANGUAGES]:
        if lang["code"] not in seen:
            seen.add(lang["code"])
            out.append(lang)
    return out


@router.post("/generate")
async def dub_generate(
    target_language: str = Form(..., min_length=1, max_length=60),
    target_language_code: str = Form(""),
    voice: str = Form("studio"),
    source: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    suffix = (source.filename or "clip").rsplit(".", 1)[-1].lower()
    source_is_video = dub_engine.is_video(source.filename or "")
    if not source_is_video and suffix not in AUDIO_EXTS:
        raise HTTPException(status_code=400, detail="Upload an audio file or a video file to dub")
    source_path = UPLOAD_DIR / f"dubsrc_{uuid.uuid4().hex}.{suffix}"
    source_path.write_bytes(await read_capped(source))

    clone_sample = await _resolve_clone(voice, user["id"])
    job = await dub_engine.create_job(
        user["id"], str(source_path), source_is_video,
        target_language, target_language_code, voice, clone_sample,
    )
    return job


@router.get("/jobs/{job_id}")
async def dub_job_status(job_id: str, user: CurrentUser):
    db = await get_db()
    cur = await db.execute("SELECT * FROM dub_jobs WHERE id = ? AND user_id = ?", (job_id, user["id"]))
    row = await cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Job not found")
    job = dict(row)
    job.pop("source_file", None)
    return job


@router.get("/jobs")
async def dub_jobs(user: CurrentUser, limit: int = 30):
    db = await get_db()
    cur = await db.execute(
        "SELECT id, target_language, voice, status, mode, file, url, error, created_at, completed_at "
        "FROM dub_jobs WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
        (user["id"], limit),
    )
    return [dict(r) for r in await cur.fetchall()]
