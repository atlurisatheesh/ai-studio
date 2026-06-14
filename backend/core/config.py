"""ArcVox Private Studio — configuration.

Voice, transcription, and avatar engines run fully locally.
LLM can be local (Ollama) or Grok (xAI) — set LLM_PROVIDER in .env.
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

if not os.environ.get("JWT_SECRET"):
    logging.getLogger("arcvox").warning(
        "JWT_SECRET is not set — using a random per-process secret. Tokens will "
        "invalidate on restart and break across multiple workers. Set JWT_SECRET in .env."
    )

# --- Production hardening ---
# Max size for any single uploaded file (audio sample, portrait, clip).
MAX_UPLOAD_MB = int(os.environ.get("MAX_UPLOAD_MB", "50"))
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024
# Generated media (TTS/avatar outputs) older than this are purged on a timer.
# 0 disables automatic cleanup.
OUTPUT_TTL_HOURS = int(os.environ.get("OUTPUT_TTL_HOURS", "48"))
# Simple per-IP request cap (requests per minute). 0 disables rate limiting.
RATE_LIMIT_PER_MINUTE = int(os.environ.get("RATE_LIMIT_PER_MINUTE", "120"))

# --- Speech-to-text (faster-whisper, runs in-process) ---
# Accuracy ladder: tiny < base < small < medium < large-v3 (use large-v3 on GPU for max accuracy)
WHISPER_MODEL = os.environ.get("WHISPER_MODEL", "small")
WHISPER_DEVICE = os.environ.get("WHISPER_DEVICE", "auto")          # auto | cpu | cuda
WHISPER_COMPUTE = os.environ.get("WHISPER_COMPUTE", "default")     # default | int8 | float16 ...

# --- Text-to-speech ---
# chatterbox   = highest quality + zero-shot voice cloning (23 langs incl. Hindi), GPU
# indic_parler = AI4Bharat Indic Parler-TTS, 21 langs incl. all major Indian
#                languages (Tamil/Telugu/Bengali/…), Apache-2.0, GPU. Gated model:
#                accept terms at hf.co/ai4bharat/indic-parler-tts and set HF_TOKEN.
# piper        = fast CPU fallback, no cloning, English-led
TTS_ENGINE = os.environ.get("TTS_ENGINE", "auto")                  # auto | chatterbox | indic_parler | multi | piper
CHATTERBOX_DEVICE = os.environ.get("CHATTERBOX_DEVICE", "cuda")
INDIC_PARLER_DEVICE = os.environ.get("INDIC_PARLER_DEVICE", "cuda")
INDIC_PARLER_MODEL = os.environ.get("INDIC_PARLER_MODEL", "ai4bharat/indic-parler-tts")
PIPER_VOICES_DIR = Path(os.environ.get("PIPER_VOICES_DIR", DATA_DIR / "piper_voices"))

# --- LLM backend: ollama (local, default) or grok (xAI cloud) ---
# LLM_PROVIDER=grok requires GROK_API_KEY. Voice/TTS/avatar always stay local.
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "ollama").lower()  # ollama | grok

# Ollama (local, privacy-first)
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434").rstrip("/")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.1:8b")

# Grok / xAI (optional cloud LLM — only the text prompt/response crosses the wire)
GROK_API_KEY = os.environ.get("GROK_API_KEY", "")
GROK_MODEL = os.environ.get("GROK_MODEL", "grok-3-mini")          # grok-3-mini | grok-3 | grok-beta
GROK_BASE_URL = "https://api.x.ai/v1"

# --- Avatar lipsync (Phase 2) ---
# sadtalker | musetalk | echomimic | liveportrait | none
# none = portrait + narrated audio preview (no motion), works on any machine
AVATAR_ENGINE = os.environ.get("AVATAR_ENGINE", "none")
SADTALKER_DIR = os.environ.get("SADTALKER_DIR", "")
MUSETALK_DIR = os.environ.get("MUSETALK_DIR", "")
ECHOMIMIC_DIR = os.environ.get("ECHOMIMIC_DIR", "")
LIVEPORTRAIT_DIR = os.environ.get("LIVEPORTRAIT_DIR", "")
AVATAR_PYTHON = os.environ.get("AVATAR_PYTHON", "python3")  # interpreter of the avatar engine's venv

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("arcvox")
