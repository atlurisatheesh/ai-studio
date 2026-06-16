"""ArcVox Private Studio — entrypoint.

A self-hosted HeyGen + ElevenLabs alternative. Every AI engine (speech,
voice cloning, LLM, avatar lipsync) runs on hardware the operator
controls. No request ever leaves this server.
"""
from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

import asyncio  # noqa: E402
import os  # noqa: E402
import secrets  # noqa: E402
import uuid  # noqa: E402
from contextlib import asynccontextmanager  # noqa: E402

from fastapi import FastAPI, APIRouter  # noqa: E402
from starlette.middleware.cors import CORSMiddleware  # noqa: E402

from core.config import CORS_ORIGINS, ADMIN_EMAIL, ADMIN_PASSWORD, logger  # noqa: E402
from core.db import get_db, close_db  # noqa: E402
from core.security import hash_password, now_iso  # noqa: E402
from core.ratelimit import RateLimitMiddleware  # noqa: E402
from core.cleanup import cleanup_loop  # noqa: E402
from routers import auth, voice, ai, avatar, projects, misc, dub, api_keys  # noqa: E402
from engines import avatar as avatar_engine, dub as dub_engine  # noqa: E402


async def _seed_admin():
    """Seed an admin once. Never resets an existing password on restart."""
    db = await get_db()
    cur = await db.execute("SELECT id FROM users WHERE email = ?", (ADMIN_EMAIL,))
    if await cur.fetchone():
        return
    password = ADMIN_PASSWORD or secrets.token_urlsafe(12)
    await db.execute(
        "INSERT INTO users (id, email, name, password_hash, role, plan, created_at) "
        "VALUES (?,?,?,?,?,?,?)",
        (str(uuid.uuid4()), ADMIN_EMAIL, "ArcVox Admin", hash_password(password),
         "admin", "studio", now_iso()),
    )
    await db.commit()
    if ADMIN_PASSWORD:
        logger.info(f"Seeded admin {ADMIN_EMAIL}")
    else:
        # printed once at first boot only — change it after logging in
        logger.warning(f"Seeded admin {ADMIN_EMAIL} with generated password: {password}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await _seed_admin()
    # Crash-resilient jobs: re-dispatch anything a previous process left
    # mid-flight (jobs are persisted, so a restart no longer loses them).
    try:
        await avatar_engine.resume_incomplete()
        await dub_engine.resume_incomplete()
    except Exception:
        logger.exception("Job resume on startup failed (continuing)")
    cleanup_task = asyncio.create_task(cleanup_loop())
    yield
    cleanup_task.cancel()
    # Mark whatever is still running as interrupted so its state is honest if
    # this box stays down; the next startup will resume these automatically.
    db = await get_db()
    await db.execute(
        "UPDATE avatar_jobs SET status = 'interrupted', "
        "error = 'Server restarted while job was running — resuming on next start.', "
        "completed_at = ? WHERE status IN ('queued', 'processing')",
        (now_iso(),),
    )
    await db.execute(
        "UPDATE dub_jobs SET status = 'interrupted', "
        "error = 'Server restarted while job was running — resuming on next start.', "
        "completed_at = ? WHERE status IN ('queued', 'processing')",
        (now_iso(),),
    )
    await db.commit()
    await close_db()


app = FastAPI(title="ArcVox Private Studio", lifespan=lifespan)

api_router = APIRouter(prefix="/api")
api_router.include_router(misc.router)      # /, /stats, /engines/status, /assets
api_router.include_router(auth.router)      # /auth/*
api_router.include_router(voice.router)     # /voice/*
api_router.include_router(ai.router)        # /ai/*, /agent/*
api_router.include_router(avatar.router)    # /avatar/*
api_router.include_router(dub.router)       # /dub/* — translate + re-voice + lip-resync
api_router.include_router(api_keys.router)  # /keys/* — programmatic API access
api_router.include_router(projects.router)  # /projects
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=CORS_ORIGINS,  # explicit allowlist — '*' with credentials is invalid
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RateLimitMiddleware)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=os.environ.get("HOST", "0.0.0.0"),
                port=int(os.environ.get("PORT", "8001")))
