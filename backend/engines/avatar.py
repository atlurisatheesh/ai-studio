"""Talking-head avatar pipeline (Phase 2) — fully local.

Pipeline per job:
  1. Synthesize the script with the local TTS engine (cloned voice supported).
  2. Lip-sync the user's uploaded portrait photo to that audio using a
     locally installed engine:
        sadtalker — github.com/OpenTalker/SadTalker (one photo → talking head)
        musetalk  — github.com/TMElyralab/MuseTalk (higher fidelity, video input)
     Both are driven as subprocesses inside their own checkout/venv so their
     heavy dependency stacks stay isolated from this app.
  3. If AVATAR_ENGINE=none, the job completes as a "preview": portrait +
     narrated audio, no motion. The product still works on CPU-only hosts.

Privacy: the user's face photo and voice never leave this machine.
"""
import asyncio
import shutil
import uuid
from pathlib import Path

from core.config import (AVATAR_ENGINE, SADTALKER_DIR, MUSETALK_DIR,
                         AVATAR_PYTHON, OUTPUT_DIR, logger)
from core.db import get_db
from core.security import now_iso, save_project
from engines import tts


def status() -> dict:
    engine_dir = {"sadtalker": SADTALKER_DIR, "musetalk": MUSETALK_DIR}.get(AVATAR_ENGINE, "")
    return {
        "engine": AVATAR_ENGINE,
        "engine_dir": engine_dir,
        "engine_ready": AVATAR_ENGINE != "none" and bool(engine_dir) and Path(engine_dir).exists(),
        "mode": "lipsync" if AVATAR_ENGINE != "none" else "preview",
    }


async def _set(job_id: str, **fields):
    db = await get_db()
    cols = ", ".join(f"{k} = ?" for k in fields)
    await db.execute(f"UPDATE avatar_jobs SET {cols} WHERE id = ?", (*fields.values(), job_id))
    await db.commit()


def _run_sadtalker(image_path: str, audio_path: str, work_dir: Path) -> Path:
    import subprocess
    cmd = [
        AVATAR_PYTHON, "inference.py",
        "--driven_audio", audio_path,
        "--source_image", image_path,
        "--result_dir", str(work_dir),
        "--still", "--preprocess", "full", "--enhancer", "gfpgan",
    ]
    subprocess.run(cmd, cwd=SADTALKER_DIR, check=True, capture_output=True, timeout=1800)
    results = sorted(work_dir.rglob("*.mp4"), key=lambda p: p.stat().st_mtime)
    if not results:
        raise RuntimeError("SadTalker produced no video")
    return results[-1]


def _run_musetalk(image_path: str, audio_path: str, work_dir: Path) -> Path:
    import subprocess
    cmd = [
        AVATAR_PYTHON, "-m", "scripts.inference",
        "--video_path", image_path,
        "--audio_path", audio_path,
        "--result_dir", str(work_dir),
    ]
    subprocess.run(cmd, cwd=MUSETALK_DIR, check=True, capture_output=True, timeout=1800)
    results = sorted(work_dir.rglob("*.mp4"), key=lambda p: p.stat().st_mtime)
    if not results:
        raise RuntimeError("MuseTalk produced no video")
    return results[-1]


async def run_job(job_id: str, user_id: str, script: str, voice: str,
                  image_path: str, clone_sample: str | None):
    await _set(job_id, status="processing", started_at=now_iso())
    try:
        # 1. narration
        audio_bytes = await tts.synthesize(script, voice=voice, clone_sample=clone_sample)
        audio_file = OUTPUT_DIR / f"avatar_audio_{job_id}.wav"
        audio_file.write_bytes(audio_bytes)

        # 2. lipsync (or preview)
        if AVATAR_ENGINE in ("sadtalker", "musetalk") and status()["engine_ready"]:
            work_dir = OUTPUT_DIR / f"avatar_work_{job_id}"
            work_dir.mkdir(exist_ok=True)
            runner = _run_sadtalker if AVATAR_ENGINE == "sadtalker" else _run_musetalk
            video = await asyncio.to_thread(runner, image_path, str(audio_file), work_dir)
            final_name = f"avatar_{job_id}.mp4"
            shutil.copy(video, OUTPUT_DIR / final_name)
            shutil.rmtree(work_dir, ignore_errors=True)
            await _set(job_id, status="completed", file=final_name,
                       url=f"/api/assets/{final_name}", completed_at=now_iso())
            kind_payload = {"script": script, "voice": voice, "file": final_name,
                            "mode": "lipsync", "engine": AVATAR_ENGINE}
        else:
            # preview mode: serve portrait + audio side by side
            audio_name = audio_file.name
            await _set(job_id, status="completed_preview", file=audio_name,
                       url=f"/api/assets/{audio_name}", completed_at=now_iso(),
                       error=None if AVATAR_ENGINE == "none" else
                       f"Avatar engine '{AVATAR_ENGINE}' configured but not found — served preview instead")
            kind_payload = {"script": script, "voice": voice, "audio_file": audio_name,
                            "image_path": image_path, "mode": "preview"}
        await save_project(user_id, "avatar", script[:60], kind_payload)
    except Exception as e:
        logger.exception("Avatar job failed")
        await _set(job_id, status="failed", error=str(e)[:500], completed_at=now_iso())


async def create_job(user_id: str, script: str, voice: str, image_path: str,
                     clone_sample: str | None) -> dict:
    job_id = str(uuid.uuid4())
    job = {
        "id": job_id, "user_id": user_id, "script": script, "voice": voice,
        "image_path": image_path, "status": "queued", "file": None, "url": None,
        "error": None, "created_at": now_iso(), "started_at": None, "completed_at": None,
    }
    db = await get_db()
    await db.execute(
        "INSERT INTO avatar_jobs (id, user_id, script, voice, image_path, status, created_at) "
        "VALUES (?,?,?,?,?,?,?)",
        (job_id, user_id, script, voice, image_path, "queued", job["created_at"]),
    )
    await db.commit()
    asyncio.create_task(run_job(job_id, user_id, script, voice, image_path, clone_sample))
    return job
