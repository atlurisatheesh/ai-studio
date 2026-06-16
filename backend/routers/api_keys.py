"""API keys — programmatic access for bulk/catalog jobs (no browser session).

Send the key as a Bearer token: `Authorization: Bearer ak_live_...` — the same
header used for the JWT, so every existing authenticated endpoint (including
/dub/generate) already works with an API key, no client changes required.
"""
import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from core.db import get_db
from core.security import CurrentUser, generate_api_key, now_iso

router = APIRouter(prefix="/keys", tags=["api-keys"])


class CreateKeyIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)


@router.post("")
async def create_key(payload: CreateKeyIn, user: CurrentUser):
    plaintext, prefix, key_hash = generate_api_key()
    key_id = str(uuid.uuid4())
    created_at = now_iso()
    db = await get_db()
    await db.execute(
        "INSERT INTO api_keys (id, user_id, name, prefix, key_hash, created_at) VALUES (?,?,?,?,?,?)",
        (key_id, user["id"], payload.name, prefix, key_hash, created_at),
    )
    await db.commit()
    return {
        "id": key_id, "name": payload.name, "prefix": prefix, "created_at": created_at,
        "key": plaintext,  # shown once — not retrievable again after this response
    }


@router.get("")
async def list_keys(user: CurrentUser):
    db = await get_db()
    cur = await db.execute(
        "SELECT id, name, prefix, created_at, last_used_at, revoked_at FROM api_keys "
        "WHERE user_id = ? ORDER BY created_at DESC",
        (user["id"],),
    )
    return [dict(r) for r in await cur.fetchall()]


@router.delete("/{key_id}")
async def revoke_key(key_id: str, user: CurrentUser):
    db = await get_db()
    cur = await db.execute(
        "SELECT id FROM api_keys WHERE id = ? AND user_id = ? AND revoked_at IS NULL",
        (key_id, user["id"]),
    )
    if not await cur.fetchone():
        raise HTTPException(status_code=404, detail="Key not found or already revoked")
    await db.execute("UPDATE api_keys SET revoked_at = ? WHERE id = ?", (now_iso(), key_id))
    await db.commit()
    return {"ok": True}
