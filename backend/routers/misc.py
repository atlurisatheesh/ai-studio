"""Misc: root, public stats, engine status, asset serving."""
import mimetypes
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from core.config import UPLOAD_DIR, OUTPUT_DIR
from core.db import get_db
from engines import stt, tts, llm, avatar

router = APIRouter(tags=["misc"])


@router.get("/")
async def root():
    return {"service": "ArcVox Private Studio", "status": "online",
            "version": "2.0.0", "self_hosted": True}


@router.get("/stats")
async def public_stats():
    db = await get_db()

    async def count(sql, *args):
        cur = await db.execute(sql, args)
        return (await cur.fetchone())[0]

    return {
        "videos_generated": await count("SELECT COUNT(*) FROM avatar_jobs WHERE status = 'completed'"),
        "voices_generated": await count("SELECT COUNT(*) FROM projects WHERE kind = 'tts'"),
        "transcriptions": await count("SELECT COUNT(*) FROM projects WHERE kind = 'transcription'"),
        "users": await count("SELECT COUNT(*) FROM users"),
    }


@router.get("/engines/status")
async def engines_status():
    """Live health of every local AI engine — shown in the studio UI."""
    return {
        "stt": stt.status(),
        "tts": tts.status(),
        "llm": await llm.status(),
        "avatar": avatar.status(),
        "privacy": "All inference runs on this server. No external AI APIs.",
    }


@router.get("/assets/{file_name}")
async def get_asset(file_name: str):
    for base in (OUTPUT_DIR, UPLOAD_DIR):
        candidate = (base / file_name).resolve()
        # safe-join: reject any path that escapes the storage dirs
        if candidate.parent != base.resolve():
            continue
        if candidate.exists():
            media, _ = mimetypes.guess_type(str(candidate))
            return FileResponse(candidate, media_type=media or "application/octet-stream")
    raise HTTPException(status_code=404, detail="Asset not found")
