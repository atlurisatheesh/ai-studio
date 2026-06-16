# ArcVox Private Studio

A self-hosted **HeyGen + ElevenLabs alternative**. Voice synthesis, voice
cloning, transcription and avatar lipsync **always run on hardware you
control** — your voice, your face, your audio never leave your server.

The only component that can optionally use the cloud is the **LLM** (scripts,
translation, voice-agent chat). It defaults to a fully-local model via
[Ollama](https://ollama.com); you may switch it to **Grok / xAI** for stronger
results, in which case only the text prompt and reply are sent to xAI. The
studio shows a clear **"CLOUD LLM ACTIVE"** banner whenever that mode is on,
and `GET /api/engines/status` reports it honestly (`cloud_llm_active`).

## Modules

| Module | Engine | Privacy | License | Runs on |
|---|---|---|---|---|
| Voice / TTS | [Chatterbox](https://github.com/resemble-ai/chatterbox) (HD, 23 langs) · [Indic Parler-TTS](https://hf.co/ai4bharat/indic-parler-tts) (21 langs incl. Tamil/Telugu/Hindi/Bengali/…) · [Piper](https://github.com/rhasspy/piper) (fast CPU) | always local | MIT / Apache-2.0 | GPU / CPU |
| Voice Cloning | Chatterbox zero-shot (10–30s sample) | always local | MIT | GPU |
| Transcription | [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (up to large-v3) | always local | MIT | CPU / GPU |
| Script / Translate / Voice Agent | [Ollama](https://ollama.com) (local) **or** Grok/xAI (cloud, opt-in) | local by default | varies | CPU / GPU / cloud |
| AI Avatar | [SadTalker](https://github.com/OpenTalker/SadTalker) / [MuseTalk](https://github.com/TMElyralab/MuseTalk) / [EchoMimic](https://github.com/BadToBest/EchoMimic) / [LivePortrait](https://github.com/KwaiVision/LivePortrait) lipsync of **your own photo** | always local | check repo | GPU 8–24GB |
| Dubbing | Transcribe (Whisper) → Translate (LLM) → Re-voice (TTS) → mux or lip-resync (MuseTalk), one pipeline | local by default* | — | CPU / GPU |
| Project Library | SQLite — one file on your disk | always local | — | anywhere |

\* Dubbing's translation step uses whichever LLM you've configured — same disclosed cloud exception as Script/Translate/Agent above.

Every module degrades gracefully: with no GPU and no models installed the
API stays up and reports exactly what's missing at `GET /api/engines/status`
(also shown on the dashboard).

## Privacy posture (read this)

- **No analytics, no trackers, no external scripts** in the frontend. The page
  loads zero third-party resources — fonts included (system-font fallbacks ship
  by default; self-host the brand faces via `scripts/setup_fonts.sh`).
- **Audio, faces, transcripts stay local — always.** There is no code path that
  sends them off the box.
- **Cloud LLM is the one opt-in exception.** With `LLM_PROVIDER=grok`, agent /
  script / translate text goes to xAI. Leave it `ollama` for a fully-offline
  deployment.

## Accuracy — honest expectations

- **Transcription:** Whisper `large-v3` matches or beats commercial APIs. This is your strongest module.
- **TTS / cloning:** Chatterbox is near-ElevenLabs quality; Piper (CPU) is good but clearly synthetic.
- **Indian languages:** set `TTS_ENGINE=indic_parler` for AI4Bharat's Indic Parler-TTS — Hindi, Tamil, Telugu, Bengali, Gujarati, Kannada, Malayalam, Marathi, Punjabi, Odia, Assamese, Urdu and more (Apache-2.0). Transcription of Indian languages already works via Whisper `large-v3`. The TTS Studio shows a language picker when an Indic engine is active.
- **One deployment for both:** set `TTS_ENGINE=multi` and the studio auto-routes each request by the text's script — Indian scripts → Indic Parler-TTS, everything else → Chatterbox, and voice cloning always → Chatterbox. Mixed-language messages route per sentence. (Install both engines on a GPU host.)
- **Avatars:** SadTalker/MuseTalk are solid but **behind HeyGen** — the open-source gap is real here. What you win instead: unlimited renders, zero per-minute fees, total privacy.
- **Dubbing:** upload any audio or video clip and the **Dubbing Studio** (`/studio/dub`, `POST /api/dub/generate`) transcribes it, translates it, and re-synthesizes it in the target language — one pipeline instead of stitching Transcribe → Translate → TTS by hand. It also emits **timed, downloadable captions** (`.srt`/`.vtt`) in both the original and target language, line-aligned to Whisper's segment timing. Audio files always work. Video files get the new audio muxed in by default; set `AVATAR_ENGINE=musetalk` to additionally re-sync mouth movement to the translated speech. Requires `ffmpeg` on the host for video (audio-only dubbing doesn't need it).
- **Reliability:** dub/avatar jobs persist in SQLite and **auto-resume on restart** — a crash or redeploy no longer loses in-flight work.
- **Programmatic access:** create an API key at `/studio/api-keys` (`POST /api/keys`) and call any endpoint with `Authorization: Bearer ak_live_...` — no browser session needed, for scripting bulk/catalog-scale jobs.

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
- `ffmpeg` (system package, not an env var) — required for **video** dubbing only; install via `apt install ffmpeg` / `brew install ffmpeg`

## Tests

```bash
cd backend && .venv/bin/python -m pytest tests/ -v
```

AI engines are mocked in tests, so the suite verifies the full
HTTP/auth/storage stack on any machine.

## Roadmap

- **Phase 3 — cinematic text-to-video** (Wan 2.2 / LTX-Video): deferred —
  needs 48–80GB VRAM and is the weakest open-vs-commercial area today.
- Real job queue (Arq/Celery) to replace the in-process `asyncio` queue —
  jobs currently don't survive a restart.
- Avatar-engine license audit before any commercial sale (SadTalker/MuseTalk/
  EchoMimic/LivePortrait licenses need a one-time check per deployment).
