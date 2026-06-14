"""Text-to-speech with zero-shot voice cloning — fully local.

Three interchangeable backends:

  chatterbox   — Resemble AI's Chatterbox (MIT, commercial-safe). Near-ElevenLabs
                 quality + zero-shot voice cloning. 23 languages incl. Hindi.
                 Needs a GPU (~12 GB VRAM).

  indic_parler — AI4Bharat Indic Parler-TTS (Apache-2.0, commercial-safe).
                 21 languages including all major Indian ones: Hindi, Tamil,
                 Telugu, Bengali, Gujarati, Kannada, Malayalam, Marathi, Punjabi,
                 Odia, Assamese, Urdu, Kashmiri, Sanskrit, Sindhi, Nepali, + English.
                 Voice is controlled by a natural-language description; the
                 language is inferred from the input script. No cloning. GPU.
                 (Gated model — accept terms on HF and set HF_TOKEN to download.)

  piper        — Rhasspy Piper (MIT). Real-time on CPU, decent quality, no
                 cloning. Lets the studio run on any machine.

The active backend is chosen by TTS_ENGINE (auto picks chatterbox when
importable, else piper). Voice ids starting with "cv_" refer to a user's
cloned voice and resolve to its reference sample.

synthesize_stream() yields a complete WAV per sentence so the caller can
start playing audio ~300ms after the first sentence instead of waiting
for the full clip.
"""
import asyncio
import io
import re
import wave
from pathlib import Path

from core.config import (TTS_ENGINE, CHATTERBOX_DEVICE, INDIC_PARLER_DEVICE,
                         INDIC_PARLER_MODEL, PIPER_VOICES_DIR, logger)

# Style presets exposed as the "system voice library" when Chatterbox is
# active. Chatterbox has one base voice; presets vary delivery. Cloned
# voices are the real differentiator.
CHATTERBOX_PRESETS = [
    {"id": "studio", "name": "Studio", "gender": "neutral", "tags": ["balanced", "narration"], "exaggeration": 0.5, "cfg_weight": 0.5},
    {"id": "calm", "name": "Calm", "gender": "neutral", "tags": ["calm", "documentary"], "exaggeration": 0.3, "cfg_weight": 0.7},
    {"id": "energetic", "name": "Energetic", "gender": "neutral", "tags": ["energetic", "ad"], "exaggeration": 0.8, "cfg_weight": 0.4},
    {"id": "dramatic", "name": "Dramatic", "gender": "neutral", "tags": ["expressive", "trailer"], "exaggeration": 1.0, "cfg_weight": 0.3},
]

# Indic Parler controls the voice via a natural-language description.
# Each preset is a description string; the spoken language comes from the
# script of the input text (e.g. Devanagari → Hindi, Tamil script → Tamil).
INDIC_PARLER_PRESETS = [
    {"id": "studio", "name": "Studio Narrator", "gender": "neutral", "tags": ["balanced", "narration"],
     "description": "A clear, neutral narrator with crisp, studio-quality recording and a moderate pace."},
    {"id": "warm_female", "name": "Warm Female", "gender": "female", "tags": ["warm", "friendly"],
     "description": "A warm, friendly female voice speaking clearly at a moderate pace with high recording quality."},
    {"id": "news_male", "name": "News Anchor", "gender": "male", "tags": ["news", "confident"],
     "description": "A confident male news anchor voice, articulate and clear, with professional recording quality."},
    {"id": "calm", "name": "Calm Soft", "gender": "neutral", "tags": ["calm", "soft"],
     "description": "A calm, soft-spoken voice with a gentle, soothing tone and very clear recording."},
]

# Languages Indic Parler-TTS can speak (ISO codes).
INDIC_LANGUAGES = [
    {"code": "hi", "name": "Hindi"}, {"code": "ta", "name": "Tamil"},
    {"code": "te", "name": "Telugu"}, {"code": "bn", "name": "Bengali"},
    {"code": "gu", "name": "Gujarati"}, {"code": "kn", "name": "Kannada"},
    {"code": "ml", "name": "Malayalam"}, {"code": "mr", "name": "Marathi"},
    {"code": "pa", "name": "Punjabi"}, {"code": "or", "name": "Odia"},
    {"code": "as", "name": "Assamese"}, {"code": "ur", "name": "Urdu"},
    {"code": "ks", "name": "Kashmiri"}, {"code": "sa", "name": "Sanskrit"},
    {"code": "sd", "name": "Sindhi"}, {"code": "ne", "name": "Nepali"},
    {"code": "en", "name": "English"},
]

_chatterbox = None
_chatterbox_error: str | None = None
_piper_voices: dict[str, object] = {}
_indic = None  # (model, prompt_tokenizer, description_tokenizer)
_indic_error: str | None = None

# Unicode blocks for the scripts Indic Parler-TTS handles. Text written in any
# of these routes to Indic Parler in "multi" mode; everything else (Latin, etc.)
# routes to Chatterbox. Urdu/Kashmiri/Sindhi use the Arabic block.
_INDIC_UNICODE_RANGES = [
    (0x0900, 0x097F),  # Devanagari — Hindi, Marathi, Sanskrit, Nepali
    (0x0980, 0x09FF),  # Bengali — Bengali, Assamese
    (0x0A00, 0x0A7F),  # Gurmukhi — Punjabi
    (0x0A80, 0x0AFF),  # Gujarati
    (0x0B00, 0x0B7F),  # Odia
    (0x0B80, 0x0BFF),  # Tamil
    (0x0C00, 0x0C7F),  # Telugu
    (0x0C80, 0x0CFF),  # Kannada
    (0x0D00, 0x0D7F),  # Malayalam
    (0x0600, 0x06FF),  # Arabic — Urdu, Kashmiri, Sindhi
]
# Non-English Indic language codes — selecting one in the UI forces Indic routing.
_INDIC_LANG_CODES = {l["code"] for l in INDIC_LANGUAGES if l["code"] != "en"}


def _is_indic_char(ch: str) -> bool:
    o = ord(ch)
    return any(lo <= o <= hi for lo, hi in _INDIC_UNICODE_RANGES)


def text_is_indic(text: str, threshold: float = 0.3) -> bool:
    """True if a meaningful share of the text's letters are in an Indic script."""
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return False
    indic = sum(1 for c in letters if _is_indic_char(c))
    return (indic / len(letters)) >= threshold


def _detect_backend() -> str:
    if TTS_ENGINE in ("chatterbox", "piper", "indic_parler", "multi"):
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


def _indic_available() -> bool:
    try:
        import parler_tts  # noqa: F401
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
    # In "multi" mode the Chatterbox presets are the default; routed Indic calls
    # map any unknown voice id to their closest preset, and the shared ids
    # (studio, calm) work in both engines.
    if BACKEND in ("chatterbox", "multi"):
        return [{k: v for k, v in p.items() if k in ("id", "name", "gender", "tags")} for p in CHATTERBOX_PRESETS]
    if BACKEND == "indic_parler":
        return [{k: v for k, v in p.items() if k in ("id", "name", "gender", "tags")} for p in INDIC_PARLER_PRESETS]
    return list_piper_voices()


def supported_languages() -> list[dict]:
    """Languages the active backend can speak (for the UI language picker)."""
    if BACKEND in ("indic_parler", "multi"):
        return INDIC_LANGUAGES
    return []


def status() -> dict:
    return {
        "backend": BACKEND,
        "chatterbox_installed": _chatterbox_available(),
        "indic_parler_installed": _indic_available(),
        "piper_installed": _piper_available(),
        "piper_voices": len(list_piper_voices()),
        "cloning_supported": BACKEND in ("chatterbox", "multi"),
        "multilingual": BACKEND in ("chatterbox", "indic_parler", "multi"),
        "auto_routing": BACKEND == "multi",
        "indic_languages": len(INDIC_LANGUAGES) if BACKEND in ("indic_parler", "multi") else 0,
        "error": _chatterbox_error if BACKEND == "chatterbox" else (_indic_error if BACKEND == "indic_parler" else None),
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


def _load_indic():
    global _indic, _indic_error
    if _indic is not None or _indic_error is not None:
        return
    try:
        from parler_tts import ParlerTTSForConditionalGeneration
        from transformers import AutoTokenizer
        logger.info(f"Loading Indic Parler-TTS ({INDIC_PARLER_MODEL}) on {INDIC_PARLER_DEVICE}…")
        model = ParlerTTSForConditionalGeneration.from_pretrained(INDIC_PARLER_MODEL).to(INDIC_PARLER_DEVICE)
        prompt_tok = AutoTokenizer.from_pretrained(INDIC_PARLER_MODEL)
        desc_tok = AutoTokenizer.from_pretrained(model.config.text_encoder._name_or_path)
        _indic = (model, prompt_tok, desc_tok)
        logger.info("Indic Parler-TTS ready")
    except Exception as e:
        _indic_error = f"{type(e).__name__}: {e}"
        logger.error(f"Indic Parler-TTS load failed: {_indic_error}")


def _wav_bytes_from_tensor(wav_tensor, sample_rate: int) -> bytes:
    import numpy as np
    data = wav_tensor.squeeze().cpu().numpy()
    return _wav_bytes_from_array(data, sample_rate)


def _wav_bytes_from_array(data, sample_rate: int) -> bytes:
    import numpy as np
    arr = np.asarray(data).squeeze()
    pcm = (np.clip(arr, -1.0, 1.0) * 32767).astype("<i2")
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


def _synthesize_indic_parler(text: str, voice: str, language: str) -> bytes:
    _load_indic()
    if _indic is None:
        raise RuntimeError(_indic_error or "Indic Parler-TTS not loaded")
    model, prompt_tok, desc_tok = _indic
    preset = next((p for p in INDIC_PARLER_PRESETS if p["id"] == voice), INDIC_PARLER_PRESETS[0])
    description = preset["description"]
    # Language is inferred from the script; naming it nudges the model when the
    # caller selected one explicitly (e.g. transliterated input).
    lang_name = next((l["name"] for l in INDIC_LANGUAGES if l["code"] == language), None)
    if lang_name:
        description = f"{description} The speaker speaks in {lang_name}."

    desc_ids = desc_tok(description, return_tensors="pt").to(INDIC_PARLER_DEVICE)
    prompt_ids = prompt_tok(text, return_tensors="pt").to(INDIC_PARLER_DEVICE)
    generation = model.generate(
        input_ids=desc_ids.input_ids,
        attention_mask=desc_ids.attention_mask,
        prompt_input_ids=prompt_ids.input_ids,
        prompt_attention_mask=prompt_ids.attention_mask,
    )
    audio = generation.cpu().numpy().squeeze()
    return _wav_bytes_from_array(audio, model.config.sampling_rate)


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


def _route_backend(text: str, clone_sample: str | None, language: str) -> str:
    """Pick an engine per-request in 'multi' mode.

    - Cloning always → Chatterbox (Indic Parler can't clone).
    - An explicitly selected Indian language, or text written in an Indic
      script → Indic Parler.
    - Otherwise → Chatterbox if available, else Piper.
    """
    if clone_sample:
        return "chatterbox"
    if language in _INDIC_LANG_CODES or text_is_indic(text):
        return "indic_parler"
    return "chatterbox" if _chatterbox_available() else "piper"


def _synthesize_sync(text: str, voice: str, speed: float, clone_sample: str | None,
                     language: str = "auto") -> bytes:
    backend = _route_backend(text, clone_sample, language) if BACKEND == "multi" else BACKEND
    if backend == "chatterbox":
        return _synthesize_chatterbox(text, voice, speed, clone_sample)
    if backend == "indic_parler":
        if clone_sample:
            raise RuntimeError("Voice cloning requires the Chatterbox engine; Indic Parler-TTS is description-controlled.")
        return _synthesize_indic_parler(text, voice, language)
    if clone_sample:
        raise RuntimeError("Voice cloning requires the Chatterbox engine (set TTS_ENGINE=chatterbox on a GPU host)")
    return _synthesize_piper(text, voice, speed)


async def synthesize(text: str, voice: str = "studio", speed: float = 1.0,
                     clone_sample: str | Path | None = None, language: str = "auto") -> bytes:
    """Synthesize speech, returning WAV bytes. Runs in a worker thread."""
    sample = str(clone_sample) if clone_sample else None
    return await asyncio.to_thread(_synthesize_sync, text, voice, speed, sample, language)


def _split_sentences(text: str) -> list[str]:
    """Split text into sentence-sized chunks for streaming synthesis.

    Merges short fragments so each chunk is ≥60 chars — avoids per-call
    overhead on single words while keeping latency per chunk under ~1s.
    Splits on Latin (.!?;) and Devanagari/Indic danda (।॥) sentence marks.
    """
    raw = re.split(r'(?<=[.!?;।॥])\s+', text.strip())
    chunks: list[str] = []
    buf = ""
    for part in raw:
        buf = (buf + " " + part).strip() if buf else part
        if len(buf) >= 60:
            chunks.append(buf)
            buf = ""
    if buf:
        if chunks:
            chunks[-1] = (chunks[-1] + " " + buf).strip()
        else:
            chunks.append(buf)
    return [c for c in chunks if c]


async def synthesize_stream(text: str, voice: str = "studio", speed: float = 1.0,
                             clone_sample: str | Path | None = None, language: str = "auto"):
    """Async generator: yields one complete WAV bytes object per sentence chunk.

    Callers can start playing the first chunk in ~300 ms instead of waiting
    for the full clip, matching ElevenLabs real-time streaming latency.
    """
    sample = str(clone_sample) if clone_sample else None
    for chunk in _split_sentences(text):
        wav = await asyncio.to_thread(_synthesize_sync, chunk, voice, speed, sample, language)
        yield wav
