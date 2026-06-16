"""Dubbing pipeline — translate + re-voice (+ optional lip-resync), fully local.

Pipeline per job:
  1. If the source is a video, extract its audio track with ffmpeg; if it's
     already an audio file, use it directly.
  2. Transcribe the audio with the local STT engine (faster-whisper).
  3. Translate the transcript to the target language with the configured
     LLM (local Ollama by default, or Grok/xAI if the operator opted in —
     same disclosed exception as the rest of the app).
  4. Re-synthesize the translated text with the local TTS engine (voice
     cloning carries over if the original creator's cloned voice is used).
  5. If the source was a video: when AVATAR_ENGINE=musetalk is configured
     (video-driven lipsync), re-sync the mouth to the new audio. Otherwise
     fall back to muxing the new audio track onto the original video — the
     same approach traditional film/TV dubbing uses.

Nothing leaves this machine except transcript/translation text, and only
when LLM_PROVIDER=grok (the one disclosed cloud exception).
"""
import asyncio
import shutil
import subprocess
import uuid
from pathlib import Path

from core.config import AVATAR_ENGINE, MUSETALK_DIR, AVATAR_PYTHON, OUTPUT_DIR, logger
from core.db import get_db
from core.security import now_iso, save_project
from engines import tts, stt, llm, subtitles

VIDEO_EXTS = {"mp4", "mov", "mkv", "webm", "avi"}


def is_video(filename: str) -> bool:
    suffix = (filename or "").rsplit(".", 1)[-1].lower()
    return suffix in VIDEO_EXTS


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def status() -> dict:
    return {
        "ffmpeg_installed": ffmpeg_available(),
        "audio_dubbing_available": True,  # needs only STT + LLM + TTS, all already gated by their own status
        "video_muxing_available": ffmpeg_available(),
        "lipsync_resync_available": (
            AVATAR_ENGINE == "musetalk" and bool(MUSETALK_DIR) and Path(MUSETALK_DIR).exists()
        ),
    }


async def _set(job_id: str, **fields):
    db = await get_db()
    cols = ", ".join(f"{k} = ?" for k in fields)
    await db.execute(f"UPDATE dub_jobs SET {cols} WHERE id = ?", (*fields.values(), job_id))
    await db.commit()


def _extract_audio(video_path: str, audio_out: Path):
    cmd = ["ffmpeg", "-y", "-i", video_path, "-vn", "-ac", "1", "-ar", "24000", str(audio_out)]
    subprocess.run(cmd, check=True, capture_output=True, timeout=600)


def _mux_audio(video_path: str, audio_path: str, video_out: Path):
    cmd = [
        "ffmpeg", "-y", "-i", video_path, "-i", audio_path,
        "-c:v", "copy", "-map", "0:v:0", "-map", "1:a:0", "-shortest", str(video_out),
    ]
    subprocess.run(cmd, check=True, capture_output=True, timeout=600)


def _run_musetalk_resync(video_path: str, audio_path: str, work_dir: Path) -> Path:
    """Re-sync mouth movement in the original video to the new-language audio.

    MuseTalk drives lipsync from a *video* (not just a still photo), which is
    exactly what dubbing needs: keep the speaker's video, replace the audio,
    regenerate the mouth to match. Falls back to a plain audio mux if this
    raises (e.g. MuseTalk not actually installed despite the env pointing at it).
    """
    cmd = [
        AVATAR_PYTHON, "-m", "scripts.inference",
        "--video_path", video_path,
        "--audio_path", audio_path,
        "--result_dir", str(work_dir),
    ]
    subprocess.run(cmd, cwd=MUSETALK_DIR, check=True, capture_output=True, timeout=1800)
    results = sorted(work_dir.rglob("*.mp4"), key=lambda p: p.stat().st_mtime)
    if not results:
        raise RuntimeError("MuseTalk produced no resynced video")
    return results[-1]


def _write_caption(name: str, content: str) -> str:
    (OUTPUT_DIR / name).write_text(content, encoding="utf-8")
    return f"/api/assets/{name}"


async def _translate_aligned(segments: list[dict], source_text: str, target_language: str):
    """Translate the transcript to the target language.

    Tries a single line-aligned call so each caption keeps its original timing
    (the Dubbing-Studio approach). Returns (full_text, translated_segments);
    translated_segments is None when the model didn't return one line per
    segment, in which case the caller emits source captions only.
    """
    if segments:
        sys_msg = (
            "You are an expert dubbing translator. Translate each numbered line "
            "faithfully into the target language, natural to SPEAK ALOUD and close "
            "to the original length/pacing. Keep the exact [n] markers, output one "
            "translated line per input line, and nothing else."
        )
        prompt = f"Target language: {target_language}\n\n" + subtitles.build_numbered_prompt(segments)
        raw = (await llm.complete(sys_msg, prompt, temperature=0.3)).strip()
        lines = subtitles.parse_aligned_translation(raw, len(segments))
        if lines is not None:
            translated_segments = [
                {"start": s.get("start", 0.0), "end": s.get("end", 0.0), "text": t}
                for s, t in zip(segments, lines)
            ]
            return " ".join(lines).strip(), translated_segments

    # fallback: translate the whole transcript at once (no aligned captions)
    sys_msg = (
        "You are an expert dubbing translator. Translate the given transcript "
        "faithfully into the target language, keeping it natural to SPEAK ALOUD "
        "and close to the original length and pacing so it can replace the "
        "original narration. Output ONLY the translated text, no commentary."
    )
    prompt = f"Target language: {target_language}\n\nTranscript:\n{source_text}"
    translated = (await llm.complete(sys_msg, prompt, temperature=0.3)).strip()
    return translated, None


async def run_job(job_id: str, user_id: str, source_path: str, source_is_video: bool,
                  target_language: str, target_language_code: str, voice: str,
                  clone_sample: str | None):
    await _set(job_id, status="processing", started_at=now_iso())
    try:
        # 1. get a clean audio track to transcribe
        if source_is_video:
            if not ffmpeg_available():
                raise RuntimeError(
                    "ffmpeg is not installed on this server — required to dub video. "
                    "Install it (e.g. apt install ffmpeg) or dub an audio file instead."
                )
            src_audio = OUTPUT_DIR / f"dub_src_{job_id}.wav"
            await asyncio.to_thread(_extract_audio, source_path, src_audio)
        else:
            src_audio = Path(source_path)

        # 2. transcribe
        transcript = await stt.transcribe(src_audio)
        source_text = (transcript.get("text") or "").strip()
        if not source_text:
            raise RuntimeError("No speech detected in the uploaded file.")
        segments = transcript.get("segments") or []
        await _set(job_id, transcript=source_text, source_language=transcript.get("language"))

        # 3. translate (line-aligned when we have timed segments)
        translated, translated_segments = await _translate_aligned(
            segments, source_text, target_language
        )
        await _set(job_id, translated_text=translated)

        # 3b. captions — timed, downloadable, editable, in source + target language
        caption_fields = {}
        if segments:
            caption_fields["source_srt_url"] = _write_caption(
                f"dub_{job_id}.src.srt", subtitles.to_srt(segments))
        if translated_segments:
            caption_fields["target_srt_url"] = _write_caption(
                f"dub_{job_id}.srt", subtitles.to_srt(translated_segments))
            caption_fields["target_vtt_url"] = _write_caption(
                f"dub_{job_id}.vtt", subtitles.to_vtt(translated_segments))
        if caption_fields:
            await _set(job_id, **caption_fields)

        # 4. re-voice in the target language
        dub_audio_bytes = await tts.synthesize(
            translated, voice=voice, clone_sample=clone_sample,
            language=target_language_code or "auto",
        )
        dub_audio = OUTPUT_DIR / f"dub_audio_{job_id}.wav"
        dub_audio.write_bytes(dub_audio_bytes)

        # 5. assemble the deliverable
        if not source_is_video:
            await _set(job_id, status="completed", file=dub_audio.name,
                       url=f"/api/assets/{dub_audio.name}", mode="audio", completed_at=now_iso())
        else:
            final_video = OUTPUT_DIR / f"dub_{job_id}.mp4"
            resynced = False
            if AVATAR_ENGINE == "musetalk" and MUSETALK_DIR and Path(MUSETALK_DIR).exists():
                try:
                    work_dir = OUTPUT_DIR / f"dub_work_{job_id}"
                    work_dir.mkdir(exist_ok=True)
                    video = await asyncio.to_thread(
                        _run_musetalk_resync, source_path, str(dub_audio), work_dir
                    )
                    shutil.copy(video, final_video)
                    shutil.rmtree(work_dir, ignore_errors=True)
                    resynced = True
                except Exception:
                    logger.exception("Lip-resync failed for dub job %s — falling back to audio mux", job_id)
            if not resynced:
                await asyncio.to_thread(_mux_audio, source_path, str(dub_audio), final_video)
            await _set(job_id, status="completed", file=final_video.name,
                       url=f"/api/assets/{final_video.name}",
                       mode="video_lipsync" if resynced else "video_dub",
                       completed_at=now_iso())

        await save_project(user_id, "dub", source_text[:60], {
            "source_language": transcript.get("language"), "target_language": target_language,
            "transcript": source_text, "translated_text": translated, "voice": voice,
        })
    except Exception as e:
        logger.exception("Dub job failed")
        await _set(job_id, status="failed", error=str(e)[:500], completed_at=now_iso())


async def create_job(user_id: str, source_path: str, source_is_video: bool,
                     target_language: str, target_language_code: str, voice: str,
                     clone_sample: str | None) -> dict:
    job_id = str(uuid.uuid4())
    created_at = now_iso()
    db = await get_db()
    await db.execute(
        "INSERT INTO dub_jobs (id, user_id, source_file, source_is_video, target_language, "
        "target_language_code, voice, status, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
        (job_id, user_id, source_path, int(source_is_video), target_language,
         target_language_code, voice, "queued", created_at),
    )
    await db.commit()
    asyncio.create_task(run_job(job_id, user_id, source_path, source_is_video,
                                target_language, target_language_code, voice, clone_sample))
    return {"id": job_id, "status": "queued", "created_at": created_at}
