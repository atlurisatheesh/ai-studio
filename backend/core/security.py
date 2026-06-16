"""JWT + password helpers, current-user dependency, project autosave."""
import hashlib
import json
import secrets
import uuid
from datetime import datetime, timezone, timedelta
from typing import Annotated

import bcrypt
import jwt
from fastapi import HTTPException, Request, Depends

from core.config import JWT_SECRET, JWT_ALGORITHM, ACCESS_TOKEN_MINUTES
from core.db import get_db, row_to_dict

API_KEY_PREFIX = "ak_live_"


def generate_api_key() -> tuple[str, str, str]:
    """Return (plaintext_key, prefix_for_display, sha256_hash_to_store).

    The plaintext is shown to the user exactly once at creation time, same as
    GitHub/Stripe-style tokens — only its hash is ever persisted.
    """
    plaintext = API_KEY_PREFIX + secrets.token_urlsafe(32)
    display_prefix = plaintext[: len(API_KEY_PREFIX) + 6]
    key_hash = hashlib.sha256(plaintext.encode("utf-8")).hexdigest()
    return plaintext, display_prefix, key_hash


async def _user_from_api_key(token: str) -> dict | None:
    key_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    db = await get_db()
    cur = await db.execute(
        "SELECT id, user_id, revoked_at FROM api_keys WHERE key_hash = ?", (key_hash,)
    )
    row = await cur.fetchone()
    if not row or row["revoked_at"]:
        return None
    await db.execute("UPDATE api_keys SET last_used_at = ? WHERE id = ?", (now_iso(), row["id"]))
    await db.commit()
    cur = await db.execute(
        "SELECT id, email, name, role, plan, created_at FROM users WHERE id = ?", (row["user_id"],)
    )
    user = await cur.fetchone()
    return dict(user) if user else None


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def create_access_token(user_id: str, email: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "type": "access",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_MINUTES),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


async def get_current_user(request: Request) -> dict:
    token = None
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
    if not token:
        token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    if token.startswith(API_KEY_PREFIX):
        user = await _user_from_api_key(token)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid or revoked API key")
        return user
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid token type")
    db = await get_db()
    cur = await db.execute(
        "SELECT id, email, name, role, plan, created_at FROM users WHERE id = ?", (payload["sub"],)
    )
    row = await cur.fetchone()
    if not row:
        raise HTTPException(status_code=401, detail="User not found")
    return dict(row)


CurrentUser = Annotated[dict, Depends(get_current_user)]


async def save_project(user_id: str, kind: str, title: str, payload: dict) -> dict:
    project = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "kind": kind,
        "title": title,
        "payload": payload,
        "created_at": now_iso(),
    }
    db = await get_db()
    await db.execute(
        "INSERT INTO projects (id, user_id, kind, title, payload, created_at) VALUES (?,?,?,?,?,?)",
        (project["id"], user_id, kind, title, json.dumps(payload), project["created_at"]),
    )
    await db.commit()
    return project
