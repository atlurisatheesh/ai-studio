"""ArcVox Private Studio — configuration.

Everything runs locally. No third-party AI APIs are ever called.
All settings come from environment variables with safe defaults.
"""
import os
import logging
import secrets
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("DATA_DIR", ROOT_DIR / "data"))
UPLOAD_DIR = DATA_DIR / "uploads"
OUTPUT_DIR = DATA_DIR / "outputs"
for d in (DATA_DIR, UPLOAD_DIR, OUTPUT_DIR):
    d.mkdir(parents=True, exist_ok=True)

DB_PATH = os.environ.get("DB_PATH", str(DATA_DIR / "arcvox.db"))

# --- Auth ---
JWT_SECRET = os.environ.get("JWT_SECRET") or secrets.token_hex(32)
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_MINUTES = 60 * 24 * 7
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@arcvox.ai").lower()
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")  # if empty, a random one is generated and logged once

CORS_ORIGINS = [o.strip() for o in os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(",") if o.strip()]

# --- Speech-to-text (faster-whisper, runs in-process) ---
# Accuracy ladder: tiny < base < small < medium < large-v3 (use large-v3 on GPU for max accuracy)
WHISPER_MODEL = os.environ.get("WHISPER_MODEL", "small")
WHISPER_DEVICE = os.environ.get("WHISPER_DEVICE", "auto")          # auto | cpu | cuda
WHISPER_COMPUTE = os.environ.get("WHISPER_COMPUTE", "default")     # default | int8 | float16 ...

# --- Text-to-speech ---
# chatterbox = highest quality + zero-shot voice cloning (GPU recommended)
# piper      = fast CPU fallback, no cloning
TTS_ENGINE = os.environ.get("TTS_ENGINE", "auto")                  # auto | chatterbox | piper
CHATTERBOX_DEVICE = os.environ.get("CHATTERBOX_DEVICE", "cuda")
PIPER_VOICES_DIR = Path(os.environ.get("PIPER_VOICES_DIR", DATA_DIR / "piper_voices"))

# --- Local LLM (Ollama) for scripts / translation / agent chat ---
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434").rstrip("/")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.1:8b")

# --- Avatar lipsync (Phase 2) ---
# sadtalker | musetalk | none  (none = portrait + audio preview only)
AVATAR_ENGINE = os.environ.get("AVATAR_ENGINE", "none")
SADTALKER_DIR = os.environ.get("SADTALKER_DIR", "")
MUSETALK_DIR = os.environ.get("MUSETALK_DIR", "")
AVATAR_PYTHON = os.environ.get("AVATAR_PYTHON", "python3")  # interpreter of the avatar engine's venv

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("arcvox")
