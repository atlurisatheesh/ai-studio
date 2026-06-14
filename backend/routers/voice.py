"""Voice router: TTS, transcription, real voice cloning — all local."""
import base64
import json
import uuid
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from core.config import UPLOAD_DIR, logger
from core.db import get_db
from core.security import CurrentUser, get_current_user, save_project, now_iso
from core.uploads import read_capped
from engines import tts, stt

router = APIRouter(prefix="/voice", tags=["voice"])

AUDIO_EXTS = {"mp3", "mp4", "mpeg", "mpga", "m4a", "wav", "webm", "flac", "ogg"}


class TTSRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    voice: str = "studio"
    model: str = "local"   # kept for frontend compatibility; engine is chosen server-side
    speed: float = Field(default=1.0, ge=0.25, le=4.0)
    language: str = "auto"  # used by Indic Parler-TTS (hi/ta/te/bn/…); ignored otherwise


async def _resolve_clone(voice_id: str, user_id: str) -> str | None:
    """If voice is a cloned voice id (cv_*), return its sample path."""
    if not voice_id.startswith("cv_"):
        return None
    db = await get_db()
    cur = await db.execute(
        "SELECT sample_path FROM cloned_voices WHERE id = ? AND user_id = ?", (voice_id, user_id)
    )
    row = await cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Cloned voice not found")
    return row["sample_path"]


@router.get("/library")
async def voice_library(user: CurrentUser):
    db = await get_db()
    cur = await db.execute(
        "SELECT id, name, description, status, note, created_at FROM cloned_voices "
        "WHERE user_id = ? ORDER BY created_at DESC", (user["id"],)
    )
    cloned = [dict(r) for r in await cur.fetchall()]
    return {"system": tts.system_voices(), "cloned": cloned, "engine": tts.BACKEND,
            "languages": tts.supported_languages()}


@router.post("/tts")
async def voice_tts(req: TTSRequest, user: CurrentUser):
    clone_sample = await _resolve_clone(req.voice, user["id"])
    try:
        audio = await tts.synthesize(req.text, voice=req.voice, speed=req.speed,
                                     clone_sample=clone_sample, language=req.language)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.exception("TTS error")
        raise HTTPException(status_code=502, detail=f"TTS generation failed: {e}")
    audio_b64 = base64.b64encode(audio).decode()
    project = await save_project(user["id"], "tts", req.text[:60],
                                 {"voice": req.voice, "engine": tts.BACKEND,
                                  "text": req.text, "audio_base64": audio_b64})
    return {"audio_base64": audio_b64, "format": "wav", "project": project}


@router.post("/tts/stream")
async def voice_tts_stream(req: TTSRequest, user: CurrentUser):
    """SSE endpoint: yields one WAV chunk per sentence for low-latency playback.

    Use with fetch() + ReadableStream — EventSource is GET-only and can't
    carry a JSON body. Each event: data: {"chunk": "<base64>", "index": N}\n\n
    Final event: data: {"done": true, "total": N}\n\n
    """
    clone_sample = await _resolve_clone(req.voice, user["id"])

    async def event_stream():
        idx = 0
        try:
            async for wav in tts.synthesize_stream(req.text, voice=req.voice,
                                                    speed=req.speed,
                                                    clone_sample=clone_sample,
                                                    language=req.language):
                payload = json.dumps({"chunk": base64.b64encode(wav).decode(), "index": idx})
                yield f"data: {payload}\n\n"
                idx += 1
            yield f"data: {json.dumps({'done': True, 'total': idx})}\n\n"
        except RuntimeError as e:
            yield f"data: {json.dumps({'error': str(e), 'done': True})}\n\n"
        except Exception as e:
            logger.exception("TTS stream error")
            yield f"data: {json.dumps({'error': f'TTS generation failed: {e}', 'done': True})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/transcribe")
async def voice_transcribe(file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    suffix = (file.filename or "audio.mp3").rsplit(".", 1)[-1].lower()
    if suffix not in AUDIO_EXTS:
        suffix = "mp3"
    tmp_path = UPLOAD_DIR / f"stt_{uuid.uuid4().hex}.{suffix}"
    tmp_path.write_bytes(await read_capped(file))
    try:
        result = await stt.transcribe(tmp_path)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.exception("STT error")
        raise HTTPException(status_code=502, detail=f"Transcription failed: {e}")
    finally:
        tmp_path.unlink(missing_ok=True)

    project = await save_project(user["id"], "transcription", (file.filename or "audio")[:60],
                                 {**result, "file_name": file.filename})
    return {**result, "project": project}


@router.post("/clone")
async def voice_clone(
    name: str = Form(...),
    description: str = Form(""),
    sample: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    suffix = (sample.filename or "voice.wav").rsplit(".", 1)[-1].lower()
    if suffix not in AUDIO_EXTS:
        raise HTTPException(status_code=400, detail="Upload an audio file (wav/mp3/m4a/flac/ogg)")
    storage_path = UPLOAD_DIR / f"voice_{uuid.uuid4().hex}.{suffix}"
    storage_path.write_bytes(await read_capped(sample))

    cloning_live = tts.status()["cloning_supported"]
    record = {
        "id": f"cv_{uuid.uuid4().hex[:10]}",
        "user_id": user["id"],
        "name": name,
        "description": description,
        "sample_path": str(storage_path),
        "status": "ready" if cloning_live else "pending_engine",
        "note": ("Zero-shot clone ready — select this voice in TTS Studio." if cloning_live else
                 "Sample saved. Cloning activates when the Chatterbox engine runs on a GPU host."),
        "created_at": now_iso(),
    }
    db = await get_db()
    await db.execute(
        "INSERT INTO cloned_voices (id, user_id, name, description, sample_path, status, note, created_at) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (record["id"], user["id"], name, description, record["sample_path"],
         record["status"], record["note"], record["created_at"]),
    )
    await db.commit()
    return {k: v for k, v in record.items() if k != "sample_path"}


@router.delete("/clone/{voice_id}")
async def delete_clone(voice_id: str, user: CurrentUser):
    db = await get_db()
    cur = await db.execute(
        "DELETE FROM cloned_voices WHERE id = ? AND user_id = ?", (voice_id, user["id"])
    )
    await db.commit()
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="Voice not found")
    return {"ok": True}
