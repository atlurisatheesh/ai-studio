"""Periodic cleanup of generated media so disk usage stays bounded.

Generated TTS/avatar outputs accumulate in OUTPUT_DIR forever otherwise.
We purge files older than OUTPUT_TTL_HOURS on a timer. User-uploaded source
material (UPLOAD_DIR) is left alone — cloned-voice samples and portraits are
referenced by DB rows and must persist.
"""
import asyncio
import time

from core.config import OUTPUT_DIR, OUTPUT_TTL_HOURS, logger


def purge_old_outputs(ttl_hours: int = OUTPUT_TTL_HOURS) -> int:
    """Delete output files older than ttl_hours. Returns count removed."""
    if ttl_hours <= 0:
        return 0
    cutoff = time.time() - ttl_hours * 3600
    removed = 0
    for path in OUTPUT_DIR.glob("*"):
        try:
            if path.is_file() and path.stat().st_mtime < cutoff:
                path.unlink()
                removed += 1
        except OSError:
            continue
    if removed:
        logger.info(f"Storage cleanup: purged {removed} output file(s) older than {ttl_hours}h")
    return removed


async def cleanup_loop(interval_seconds: int = 3600):
    """Run purge_old_outputs on a timer until cancelled."""
    if OUTPUT_TTL_HOURS <= 0:
        return
    while True:
        try:
            await asyncio.to_thread(purge_old_outputs)
        except Exception:
            logger.exception("Storage cleanup pass failed")
        await asyncio.sleep(interval_seconds)
