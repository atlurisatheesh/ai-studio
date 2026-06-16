"""Subtitle/caption helpers — turn timed transcript segments into SRT/VTT.

Pure functions, no AI and no I/O, so they run and test anywhere. This is the
piece that turns the dub pipeline into a real *Dubbing Studio*: timed,
downloadable, editable captions in both the source and target language —
exactly what ElevenLabs Dubbing Studio gives and a one-shot converter doesn't.
"""
from __future__ import annotations


def _ts(seconds: float, sep: str) -> str:
    """Format seconds as HH:MM:SS<sep>mmm (sep is ',' for SRT, '.' for VTT)."""
    if seconds < 0:
        seconds = 0.0
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}{sep}{ms:03d}"


def to_srt(segments: list[dict]) -> str:
    """Build an SRT document from [{start,end,text}, …]."""
    blocks = []
    for i, seg in enumerate(segments, start=1):
        text = (seg.get("text") or "").strip()
        if not text:
            continue
        start = _ts(float(seg.get("start", 0.0)), ",")
        end = _ts(float(seg.get("end", 0.0)), ",")
        blocks.append(f"{i}\n{start} --> {end}\n{text}")
    return "\n\n".join(blocks) + ("\n" if blocks else "")


def to_vtt(segments: list[dict]) -> str:
    """Build a WebVTT document from [{start,end,text}, …]."""
    lines = ["WEBVTT", ""]
    for seg in segments:
        text = (seg.get("text") or "").strip()
        if not text:
            continue
        start = _ts(float(seg.get("start", 0.0)), ".")
        end = _ts(float(seg.get("end", 0.0)), ".")
        lines.append(f"{start} --> {end}")
        lines.append(text)
        lines.append("")
    return "\n".join(lines)


def build_numbered_prompt(segments: list[dict]) -> str:
    """Number each segment so the LLM can translate them line-aligned in one call."""
    return "\n".join(f"[{i}] {(s.get('text') or '').strip()}"
                     for i, s in enumerate(segments, start=1))


def parse_aligned_translation(raw: str, expected_n: int) -> list[str] | None:
    """Parse a '[n] translated text' block back into a list of `expected_n` lines.

    Returns None if the model didn't return exactly one line per segment, so the
    caller can fall back to whole-text translation rather than emit misaligned
    captions.
    """
    out: dict[int, str] = {}
    for line in (raw or "").splitlines():
        line = line.strip()
        if not (line.startswith("[") and "]" in line):
            continue
        marker, _, text = line.partition("]")
        try:
            idx = int(marker[1:].strip())
        except ValueError:
            continue
        out[idx] = text.strip()
    if len(out) != expected_n or set(out) != set(range(1, expected_n + 1)):
        return None
    return [out[i] for i in range(1, expected_n + 1)]
