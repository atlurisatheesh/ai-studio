"""Speech-to-text — faster-whisper running fully in-process.

Accuracy: Whisper large-v3 matches or beats commercial transcription
APIs on most benchmarks. Smaller models trade accuracy for speed/VRAM.
Audio never leaves this machine.
"""
import asyncio
from pathlib import Path

from core.config import WHISPER_MODEL, WHISPER_DEVICE, WHISPER_COMPUTE, logger

_model = None
_load_error: str | None = None


def _load():
    global _model, _load_error
    if _model is not None or _load_error is not None:
        return
    try:
        from faster_whisper import WhisperModel
        logger.info(f"Loading Whisper model '{WHISPER_MODEL}' on {WHISPER_DEVICE}…")
        _model = WhisperModel(WHISPER_MODEL, device=WHISPER_DEVICE, compute_type=WHISPER_COMPUTE)
        logger.info("Whisper ready")
    except Exception as e:  # missing package, missing CUDA, download blocked…
        _load_error = f"{type(e).__name__}: {e}"
        logger.error(f"Whisper load failed: {_load_error}")


def is_available() -> bool:
    try:
        import faster_whisper  # noqa: F401
        return True
    except ImportError:
        return False


def status() -> dict:
    return {
        "engine": "faster-whisper",
        "model": WHISPER_MODEL,
        "installed": is_available(),
        "loaded": _model is not None,
        "error": _load_error,
    }


def _transcribe_sync(path: str) -> dict:
    _load()
    if _model is None:
        raise RuntimeError(_load_error or "Whisper model not loaded")
    segments, info = _model.transcribe(path, vad_filter=True, word_timestamps=False)
    seg_list = []
    text_parts = []
    for s in segments:
        seg_list.append({"start": round(s.start, 2), "end": round(s.end, 2), "text": s.text.strip()})
        text_parts.append(s.text.strip())
    return {
        "text": " ".join(text_parts).strip(),
        "language": info.language,
        "language_probability": round(info.language_probability, 3),
        "duration": round(info.duration, 2),
        "segments": seg_list,
    }


async def transcribe(path: Path) -> dict:
    """Transcribe an audio file. Heavy work runs in a worker thread."""
    return await asyncio.to_thread(_transcribe_sync, str(path))
