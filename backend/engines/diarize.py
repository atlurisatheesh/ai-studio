"""Speaker diarization — "who spoke when" — fully local (pyannote.audio).

Optional engine, off by default. When pyannote isn't installed (or no HF_TOKEN
for its gated model), `diarize()` returns an empty list and the dubbing pipeline
behaves exactly as before: one speaker, one voice. Installing it upgrades dubbing
so each caption line is labelled by speaker and the job reports how many speakers
were heard — the single biggest visible gap in multi-speaker dubbing today.

Nothing leaves the machine: diarization runs locally on the same audio Whisper
already transcribed.

The model is gated: accept terms at hf.co/pyannote/speaker-diarization-3.1 and
set HF_TOKEN in .env. Install with: pip install pyannote.audio

The pure helpers below (`assign_speakers`, `speaker_count`,
`label_segments_for_caption`) do the actual segment↔speaker reconciliation and
have no I/O or model dependency, so they're unit-tested without a GPU.
"""
from core.config import HF_TOKEN, logger

_PIPELINE_ID = "pyannote/speaker-diarization-3.1"
_pipeline = None
_load_failed = False


def _is_installed() -> bool:
    try:
        import pyannote.audio  # noqa: F401
        return True
    except Exception:
        return False


def available() -> bool:
    """True only when both the library is importable and a token is configured."""
    return _is_installed() and bool(HF_TOKEN)


def status() -> dict:
    return {
        "engine": "pyannote",
        "model": _PIPELINE_ID,
        "installed": _is_installed(),
        "token_set": bool(HF_TOKEN),
        "available": available(),
    }


def _get_pipeline():
    global _pipeline, _load_failed
    if _pipeline is not None or _load_failed:
        return _pipeline
    try:
        from pyannote.audio import Pipeline
        import torch
        pipe = Pipeline.from_pretrained(_PIPELINE_ID, use_auth_token=HF_TOKEN)
        if torch.cuda.is_available():
            pipe.to(torch.device("cuda"))
        _pipeline = pipe
    except Exception:
        logger.exception("Could not load diarization pipeline — dubbing stays single-speaker")
        _load_failed = True
    return _pipeline


def _diarize_sync(path: str) -> list[dict]:
    pipe = _get_pipeline()
    if pipe is None:
        return []
    annotation = pipe(path)
    turns = []
    for turn, _, speaker in annotation.itertracks(yield_label=True):
        turns.append({"start": float(turn.start), "end": float(turn.end), "speaker": str(speaker)})
    return turns


async def diarize(audio_path) -> list[dict]:
    """Return speaker turns [{start, end, speaker}] for an audio file.

    Returns [] (and the caller falls back to single-speaker behaviour) when the
    engine isn't available or the model fails to load — never raises.
    """
    if not available():
        return []
    import asyncio
    try:
        return await asyncio.to_thread(_diarize_sync, str(audio_path))
    except Exception:
        logger.exception("Diarization failed — falling back to single-speaker")
        return []


# ── Pure reconciliation helpers (no model, unit-tested) ────────────────────


def assign_speakers(segments: list[dict], turns: list[dict]) -> list[dict]:
    """Tag each transcript segment with the speaker whose turn overlaps it most.

    Pure function. Returns a new list. With no turns, segments pass through
    unchanged (and untagged), preserving the original single-speaker behaviour.
    """
    if not turns:
        return [dict(s) for s in segments]
    tagged = []
    for s in segments:
        ss, se = s.get("start", 0.0), s.get("end", 0.0)
        best_speaker, best_overlap = None, 0.0
        for t in turns:
            overlap = min(se, t["end"]) - max(ss, t["start"])
            if overlap > best_overlap:
                best_overlap, best_speaker = overlap, t["speaker"]
        tagged.append({**s, "speaker": best_speaker})
    return tagged


def speaker_count(turns: list[dict]) -> int:
    return len({t["speaker"] for t in turns})


def label_segments_for_caption(segments: list[dict]) -> list[dict]:
    """Prefix each line's text with a stable, 1-based "[Speaker N] " tag.

    Only applies when 2+ distinct speakers are present (a single-speaker clip
    needs no labels). Pure function; returns a new list. Speakers are numbered
    by first appearance so the labels read naturally top-to-bottom.
    """
    order: list[str] = []
    for s in segments:
        sp = s.get("speaker")
        if sp and sp not in order:
            order.append(sp)
    if len(order) < 2:
        return [dict(s) for s in segments]
    number = {sp: i + 1 for i, sp in enumerate(order)}
    out = []
    for s in segments:
        sp = s.get("speaker")
        text = f"[Speaker {number[sp]}] {s['text']}" if sp in number else s["text"]
        out.append({**s, "text": text})
    return out
