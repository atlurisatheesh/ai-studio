# ArcVox Private Studio

A self-hosted **HeyGen + ElevenLabs alternative**. Every AI model — speech
synthesis, voice cloning, transcription, LLM, avatar lipsync — runs on
hardware **you** control. No third-party AI API is ever called. Your voice,
your face, your scripts never leave your server.

## Modules

| Module | Engine (all local) | License | Runs on |
|---|---|---|---|
| Voice / TTS | [Chatterbox](https://github.com/resemble-ai/chatterbox) (HD) or [Piper](https://github.com/rhasspy/piper) (fast) | MIT | GPU / CPU |
| Voice Cloning | Chatterbox zero-shot (10–30s sample) | MIT | GPU |
| Transcription | [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (up to large-v3) | MIT | CPU / GPU |
| Script Writer / Translate / Voice Agent | Any [Ollama](https://ollama.com) model (default llama3.1:8b) | varies | CPU / GPU |
| AI Avatar | [SadTalker](https://github.com/OpenTalker/SadTalker) / [MuseTalk](https://github.com/TMElyralab/MuseTalk) lipsync of **your own photo** | check repo | GPU 16–24GB |
| Project Library | SQLite — one file on your disk | — | anywhere |

Every module degrades gracefully: with no GPU and no models installed the
API stays up and reports exactly what's missing at `GET /api/engines/status`
(also shown on the dashboard).

## Accuracy — honest expectations

- **Transcription:** Whisper `large-v3` matches or beats commercial APIs. This is your strongest module.
- **TTS / cloning:** Chatterbox is near-ElevenLabs quality; Piper (CPU) is good but clearly synthetic.
- **Avatars:** SadTalker/MuseTalk are solid but **behind HeyGen** — the open-source gap is real here. What you win instead: unlimited renders, zero per-minute fees, total privacy.

## Quick start (development)

```bash
# Backend
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp ../.env.example .env   # set JWT_SECRET (see file)
bash ../scripts/setup_models.sh
.venv/bin/python -m uvicorn server:app --port 8001

# Frontend
cd frontend
yarn install
REACT_APP_BACKEND_URL=http://localhost:8001 yarn start
```

First boot seeds an admin account (`ADMIN_EMAIL`); if `ADMIN_PASSWORD` is
unset a random one is printed **once** in the logs.

## Production (Docker)

```bash
cp .env.example .env       # fill in JWT_SECRET at minimum
docker compose up -d                   # CPU host
docker compose --profile gpu up -d     # GPU host (Ollama on GPU)
```

All user data (DB, uploads, generated media) lives in the `arcvox_data`
volume — back up that one volume and you've backed up everything.

## Hardware guide

| Tier | Hardware | What you get |
|---|---|---|
| CPU-only | any 4-core box | Whisper small STT, Piper real-time TTS, LLM (slow), avatar preview |
| 1× 12–16GB GPU (~$0.50/hr rented) | RTX 4090 / L4 | Chatterbox HD voices + cloning, Whisper large-v3, fast LLM |
| 1× 24GB GPU (~$0.80/hr) | RTX 3090/4090, A10G | + SadTalker/MuseTalk talking-head avatars |

GPU rental (RunPod, Lambda, Vast.ai) keeps this "your own" — the box is
yours for the hour; no AI vendor sees your data.

## Engine configuration

Everything is set via `.env` (see `.env.example`). Key switches:

- `WHISPER_MODEL=large-v3` — max transcription accuracy (GPU)
- `TTS_ENGINE=chatterbox` — HD voices + cloning (after `pip install chatterbox-tts`)
- `AVATAR_ENGINE=sadtalker` + `SADTALKER_DIR=…` — full lip-synced avatar videos
- `OLLAMA_MODEL=qwen2.5:14b` — stronger translation/scripts if you have VRAM

## Tests

```bash
cd backend && .venv/bin/python -m pytest tests/ -v
```

AI engines are mocked in tests, so the suite verifies the full
HTTP/auth/storage stack on any machine.

## Roadmap

- **Phase 3 — cinematic text-to-video** (Wan 2.2 / LTX-Video): deferred —
  needs 48–80GB VRAM and is the weakest open-vs-commercial area today.
- Streaming TTS for the voice agent; word-level timestamps UI for transcripts.
- Replace landing-page stock images (currently hot-linked from the old
  prototype's CDN) with own assets.
