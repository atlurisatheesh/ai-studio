"""Safe upload handling — size caps to prevent memory-exhaustion DoS."""
from fastapi import HTTPException, UploadFile

from core.config import MAX_UPLOAD_BYTES, MAX_UPLOAD_MB


async def read_capped(upload: UploadFile, max_bytes: int = MAX_UPLOAD_BYTES) -> bytes:
    """Read an UploadFile in chunks, rejecting anything over the cap.

    Avoids loading an arbitrarily large body into memory: we stop and raise
    413 as soon as the running total exceeds the limit.
    """
    chunk_size = 1024 * 1024  # 1 MB
    total = 0
    parts: list[bytes] = []
    while True:
        chunk = await upload.read(chunk_size)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum upload size is {MAX_UPLOAD_MB} MB.",
            )
        parts.append(chunk)
    return b"".join(parts)
