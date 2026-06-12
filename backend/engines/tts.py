"""Text-to-speech with zero-shot voice cloning — fully local.

Two interchangeable backends:

  chatterbox — Resemble AI's Chatterbox (MIT license, commercial-safe).
               Near-ElevenLabs quality and clones any voice from a short
               reference clip. Needs a GPU (~12 GB VRAM) for usable speed.

  piper      — Rhasspy Piper (MIT). Real-time on CPU, good (not stunning)
               quality, no cloning. Lets the studio run on any machine.

The active backend is chosen by TTS_ENGINE (auto picks chatterbox when
importable, else piper). Voice ids starting with "cv_" refer to a user's
cloned voice and resolve to its reference sample.
"""
import asyncio
import io
import wave
from pathlib import Path

from core.config import TTS_ENGINE, CHATTERBOX_DEVICE, PIPER_VOICES_DIR, logger

# Style presets exposed as the "system voice library" when Chatterbox is
# active. Chatterbox has one base voice; presets vary delivery. Cloned
# voices are the real differentiator.
CHATTERBOX_PRESETS = [
    {"id": "studio", "name": "Studio", "gender": "neutral", "tags": ["balanced", "narration"], "exaggeration": 0.5, "cfg_weight": 0.5},
    {"id": "calm", "name": "Calm", "gender": "neutral", "tags": ["calm", "documentary"], "exaggeration": 0.3, "cfg_weight": 0.7},
    {"id": "energetic", "name": "Energetic", "gender": "neutral", "tags": ["energetic", "ad"], "exaggeration": 0.8, "cfg_weight": 0.4},
    {"id": "dramatic", "name": "Dramatic", "gender": "neutral", "tags": ["expressive", "trailer"], "exaggeration": 1.0, "cfg_weight": 0.3},
]

_chatterbox = None
_chatterbox_error: str | None = None
_piper_voices: dict[str, object] = {}


def _detect_backend() -> str:
    if TTS_ENGINE in ("chatterbox", "piper"):
        return TTS_ENGINE
    try:
        import chatterbox  # noqa: F401
        return "chatterbox"
    except ImportError:
        return "piper"


BACKEND = _detect_backend()


def _piper_available() -> bool:
    try:
        import piper  # noqa: F401
        return True
    except ImportError:
        return False


def _chatterbox_available() -> bool:
    try:
        import chatterbox  # noqa: F401
        return True
    except ImportError:
        return False


def list_piper_voices() -> list[dict]:
    voices = []
    if PIPER_VOICES_DIR.exists():
        for f in sorted(PIPER_VOICES_DIR.glob("*.onnx")):
            voices.append({"id": f.stem, "name": f.stem.replace("_", " ").title(),
                           "gender": "neutral", "tags": ["piper"]})
    return voices


def system_voices() -> list[dict]:
    if BACKEND == "chatterbox":
        return [{k: v for k, v in p.items() if k in ("id", "name", "gender", "tags")} for p in CHATTERBOX_PRESETS]
    return list_piper_voices()


def status() -> dict:
    return {
        "backend": BACKEND,
        "chatterbox_installed": _chatterbox_available(),
        "piper_installed": _piper_available(),
        "piper_voices": len(list_piper_voices()),
        "cloning_supported": BACKEND == "chatterbox",
        "error": _chatterbox_error,
    }


def _load_chatterbox():
    global _chatterbox, _chatterbox_error
    if _chatterbox is not None or _chatterbox_error is not None:
        return
    try:
        from chatterbox.tts import ChatterboxTTS
        logger.info(f"Loading Chatterbox TTS on {CHATTERBOX_DEVICE}…")
        _chatterbox = ChatterboxTTS.from_pretrained(device=CHATTERBOX_DEVICE)
        logger.info("Chatterbox ready")
    except Exception as e:
        _chatterbox_error = f"{type(e).__name__}: {e}"
        logger.error(f"Chatterbox load failed: {_chatterbox_error}")


def _wav_bytes_from_tensor(wav_tensor, sample_rate: int) -> bytes:
    import numpy as np
    data = wav_tensor.squeeze().cpu().numpy()
    pcm = (np.clip(data, -1.0, 1.0) * 32767).astype("<i2")
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(pcm.tobytes())
    return buf.getvalue()


def _synthesize_chatterbox(text: str, voice: str, speed: float, clone_sample: str | None) -> bytes:
    _load_chatterbox()
    if _chatterbox is None:
        raise RuntimeError(_chatterbox_error or "Chatterbox not loaded")
    kwargs = {}
    if clone_sample:
        kwargs["audio_prompt_path"] = clone_sample
    else:
        preset = next((p for p in CHATTERBOX_PRESETS if p["id"] == voice), CHATTERBOX_PRESETS[0])
        kwargs["exaggeration"] = preset["exaggeration"]
        kwargs["cfg_weight"] = preset["cfg_weight"]
    wav = _chatterbox.generate(text, **kwargs)
    return _wav_bytes_from_tensor(wav, _chatterbox.sr)


def _synthesize_piper(text: str, voice: str, speed: float) -> bytes:
    try:
        from piper import PiperVoice
    except ImportError:
        raise RuntimeError("Piper not installed. Run: pip install piper-tts")
    available = list_piper_voices()
    if not available:
        raise RuntimeError(
            f"No Piper voices found in {PIPER_VOICES_DIR}. "
            "Download .onnx voices from https://huggingface.co/rhasspy/piper-voices"
        )
    if voice not in [v["id"] for v in available]:
        voice = available[0]["id"]
    if voice not in _piper_voices:
        _piper_voices[voice] = PiperVoice.load(str(PIPER_VOICES_DIR / f"{voice}.onnx"))
    pv = _piper_voices[voice]
    from piper import SynthesisConfig
    cfg = SynthesisConfig(length_scale=1.0 / max(speed, 0.25))
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        pv.synthesize_wav(text, w, syn_config=cfg)
    return buf.getvalue()


def _synthesize_sync(text: str, voice: str, speed: float, clone_sample: str | None) -> bytes:
    if BACKEND == "chatterbox":
        return _synthesize_chatterbox(text, voice, speed, clone_sample)
    if clone_sample:
        raise RuntimeError("Voice cloning requires the Chatterbox engine (set TTS_ENGINE=chatterbox on a GPU host)")
    return _synthesize_piper(text, voice, speed)


async def synthesize(text: str, voice: str = "studio", speed: float = 1.0,
                     clone_sample: str | Path | None = None) -> bytes:
    """Synthesize speech, returning WAV bytes. Runs in a worker thread."""
    sample = str(clone_sample) if clone_sample else None
    return await asyncio.to_thread(_synthesize_sync, text, voice, speed, sample)
