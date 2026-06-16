# ArcVox Private Studio — Project Handoff & State

> **Purpose of this file:** the single source of truth for what ArcVox is, every
> decision we made, what's built, what's *not* proven yet, and exactly what to do
> next. **To resume in a new session:** point Claude at this file and say
> *"read PROJECT_HANDOFF.md and continue."*
>
> **Last updated:** 2026-06-16 · **Branch:** `claude/arc-vox-analysis-fpn183`

---

## 1 · TL;DR — where we stand right now

ArcVox is a **self-hosted, privacy-first alternative to HeyGen + ElevenLabs**:
voice synthesis, voice cloning, transcription, a voice/LLM agent, and talking-head
avatars — all running on **pretrained open-source models you host yourself**. No
customer audio, face, or transcript ever leaves the operator's server. The LLM is
the one optional exception (Grok cloud), and the app flags it loudly when active.

- **Built & working in code:** full Phase 1 (voice) + Phase 2 (avatar), streaming
  TTS + LLM, Indian languages, privacy hardening, production guards, and now an
  **integrated dubbing pipeline** (transcribe → translate → re-voice → mux/lip-resync).
  **18/18 backend tests pass; frontend builds clean.**
- **The one big open item:** we have **never run the GPU models end-to-end** — all
  quality claims are still *unverified*. Two Colab/Kaggle notebooks were built to
  close this; **the user has not run them yet.** This is the #1 next action.
- **This dev environment cannot verify it for us:** the sandbox network blocks
  `huggingface.co`, `kaggle.com`, and `api.x.ai`, and has no GPU or `ffmpeg`.
  Verification *must* happen on the user's Google Colab / Kaggle, or a real host.

---

## 2 · The vision (and the decision that matters most)

**Goal:** a commercial product that does what HeyGen (avatars) and ElevenLabs
(voice) do, but **self-hosted and private** — the operator controls the hardware,
nothing is sent to a third-party AI API, and there are no per-generation fees.

**THE key decision — we do NOT train models.** This came up repeatedly and must
not be re-litigated:

- Training a base TTS/STT/avatar model from scratch needs **hundreds of GPUs,
  months, and millions of dollars** plus huge proprietary datasets (Whisper used
  680,000 hours of audio). It is infeasible and **pointless**.
- The models are **already trained** by Resemble AI, AI4Bharat, OpenAI/SYSTRAN,
  and avatar research labs, and released free under **MIT / Apache-2.0**. We
  **download the weights and run inference** — that is what "self-hosting" means.
- "Your own model / your own tool" = **your deployment, your hardware, your
  private data** — *not* weights trained from zero.
- The only training that could ever make sense is **optional per-voice
  fine-tuning** (hours on one GPU) as a future premium feature — and only if
  zero-shot cloning isn't good enough. Never base-model training.

**Commercial license constraint:** only **MIT / Apache-2.0** models are used.
Avoid non-commercial models (e.g. XTTS-v2, MMS-TTS for production).

---

## 3 · What's built

### Modules (all local unless noted)
| Module | Engine | License | Notes |
|---|---|---|---|
| Voice / TTS | Chatterbox (HD, 23 langs) · Indic Parler-TTS (21 langs) · Piper (CPU) | MIT / Apache-2.0 | engine auto-selected |
| Voice cloning | Chatterbox zero-shot (10–30s sample) | MIT | GPU |
| Transcription | faster-whisper `large-v3` | MIT | covers Indian languages |
| Script / Translate / Voice Agent | Ollama (local) **or** Grok/xAI (cloud, opt-in) | varies | local by default |
| AI Avatar | SadTalker · MuseTalk · EchoMimic · LivePortrait (lip-sync of the user's **own** photo) | check repo | GPU 8–24 GB |
| Dubbing | Whisper → LLM translate → TTS re-voice → ffmpeg mux / MuseTalk lip-resync | — | CPU (audio) / GPU (video lip-resync) |
| Project Library | SQLite (one file) | — | anywhere |

### Architecture
- **Backend:** FastAPI + **SQLite (aiosqlite)** — deliberately replaced MongoDB so
  all data is one local file the operator controls. JWT auth (httpOnly cookie) +
  bcrypt. Long jobs run via `asyncio.create_task` (in-process queue).
- **Frontend:** React + shadcn + Tailwind + Framer Motion. Brutalist "control
  room" aesthetic (void-black `#050505`, studio-red `#FF331F`). **Zero external
  trackers/scripts/fonts** — fully self-contained build.
- **Deploy:** Docker Compose (CPU profile default; GPU profile with Ollama).
- **Graceful degradation:** every engine reports health at
  `GET /api/engines/status`; the app stays up and says exactly what's missing.

### Key backend files
```
backend/
  server.py              # app entry, lifespan (seed admin, cleanup loop, mark interrupted jobs)
  core/
    config.py            # ALL env config (engines, devices, hardening knobs)
    db.py                # SQLite schema + async connection
    security.py          # JWT, bcrypt, CurrentUser dep, save_project()
    uploads.py           # read_capped() — size-limited upload reader (413 guard)
    ratelimit.py         # per-IP rate-limit middleware (429)
    cleanup.py           # periodic purge of old generated media
  engines/
    tts.py               # Chatterbox / Indic Parler / Piper + multi auto-router
    stt.py               # faster-whisper (word timestamps)
    llm.py               # Ollama + Grok backends, blocking + streaming
    avatar.py            # SadTalker/MuseTalk/EchoMimic/LivePortrait subprocess drivers
    dub.py                # transcribe → translate → re-voice → mux/lip-resync pipeline
  routers/
    voice.py             # /voice/tts, /voice/tts/stream (SSE), /transcribe, /clone, /library
    ai.py                # /ai/script, /ai/translate, /agent/chat, /agent/chat/stream (SSE)
    avatar.py            # /avatar/generate, /avatar/jobs
    dub.py                # /dub/generate, /dub/jobs, /dub/languages
    auth.py projects.py misc.py
  tests/test_api.py      # 18 tests, all engines mocked — runs without a GPU
```

### Key frontend pages
`Landing, Login, Signup, Dashboard, TTSStudio, VoiceClone, Transcribe,
AvatarStudio, DubbingStudio, VoiceAgent, ScriptStudio, Translate, ProjectsPage`

---

## 4 · Feature log (what we did, in order)

1. **Phase 1 + 2 build** — voice studio + avatar from user's own photo; MongoDB→SQLite; brutalist UI; 10 tests.
2. **Streaming TTS** — `synthesize_stream()` splits text into sentences, `POST /voice/tts/stream` (SSE); first audio ~300 ms instead of waiting for the full clip.
3. **Avatar engines added** — EchoMimic (~16 GB, best quality) + LivePortrait (~8 GB) alongside SadTalker/MuseTalk. (LongCat-Video-Avatar evaluated → it's a heavy video-diffusion model, deferred until a stable inference path exists.)
4. **LLM token streaming** — `chat_stream()` + `POST /agent/chat/stream` (SSE); Voice Agent shows text word-by-word and speaks each sentence as it completes.
5. **Transcript timestamps UI** — clickable `[MM:SS]` segments seek the audio player; active segment highlights; COPY SRT export.
6. **Grok/xAI LLM backend** — `LLM_PROVIDER=grok` alongside Ollama; same blocking + streaming interface.
7. **Privacy contradictions fixed** — removed PostHog (incl. session recording), the Emergent badge + script, external font CDNs, and all hot-linked CDN images; honest **"CLOUD LLM ACTIVE"** banner when Grok is on; `/engines/status` reports `cloud_llm_active`.
8. **Production hardening** — upload size cap (`MAX_UPLOAD_MB`, 413), per-IP rate limiting (`RATE_LIMIT_PER_MINUTE`, 429), periodic storage cleanup (`OUTPUT_TTL_HOURS`), JWT-secret startup warning.
9. **GPU verification notebooks** — `arcvox_gpu_verify.ipynb` (Colab/Kaggle) runs the real engines and produces artifacts; **no training**.
10. **Indian languages** — AI4Bharat **Indic Parler-TTS** (Apache-2.0, 21 languages incl. Tamil/Telugu/Bengali/Hindi…); `TTS_ENGINE=indic_parler`; language picker in TTS Studio; Whisper already covers Indian-language STT.
11. **Multi-engine auto-routing** — `TTS_ENGINE=multi` picks the engine **per request by the text's script**: Indic scripts → Indic Parler, else → Chatterbox, cloning → Chatterbox. Streaming routes each sentence independently.
12. **Quick-listen notebook** — `arcvox_quicklisten.ipynb`: zero uploads, zero keys, "Run all" → hear an English + Hindi voice and a transcription. For non-technical verification.
13. **Integrated dubbing pipeline** — `engines/dub.py` + `POST /api/dub/generate`: one upload (audio or video) runs transcribe (Whisper) → translate (the configured LLM) → re-voice (TTS, cloning-capable) → for video, mux the new audio in by default or, with `AVATAR_ENGINE=musetalk`, re-sync the mouth to the translated speech (MuseTalk drives lipsync from a video, which is exactly what a dub needs — falls back to a plain mux if that fails). New `dub_jobs` DB table, `Dubbing Studio` frontend page (`/studio/dub`), `/engines/status` reports a `dub` block (`ffmpeg_installed`, `lipsync_resync_available`). 4 new tests (audio job, video job w/ mux fallback, language list, bad-extension rejection) — 18/18 passing.

---

## 5 · The models — what, where, license

> You barely download anything by hand: `pip install` + first-run auto-download
> pulls the weights from Hugging Face. `scripts/setup_models.sh` orchestrates it.

| Engine | Source | License | How it's fetched |
|---|---|---|---|
| Chatterbox (TTS + cloning, 23 langs) | `hf.co/ResembleAI/chatterbox` | MIT | `pip install chatterbox-tts` → `from_pretrained()` |
| Whisper large-v3 (STT) | `hf.co/Systran/faster-whisper-large-v3` | MIT | `WhisperModel("large-v3")` |
| Indic Parler-TTS (21 Indian langs) | `hf.co/ai4bharat/indic-parler-tts` | Apache-2.0 | **gated** — accept terms + `HF_TOKEN`; `pip install git+…/parler-tts` |
| Piper voices (CPU TTS) | `hf.co/rhasspy/piper-voices` | MIT | `scripts/setup_models.sh` |
| LLM (local) | `ollama.com` → `ollama pull llama3.1:8b` | Llama community | local |
| LLM (cloud, opt-in) | Grok/xAI API | commercial | `LLM_PROVIDER=grok` + key |
| Avatar: SadTalker (~8 GB) | `github.com/OpenTalker/SadTalker` | check repo | `download_models.sh` |
| Avatar: MuseTalk (~12 GB) | `github.com/TMElyralab/MuseTalk` | check repo | per README |
| Avatar: EchoMimic (~16 GB) | `github.com/BadToBest/EchoMimic` | check repo | per README |
| Avatar: LivePortrait (~8 GB) | `github.com/KwaiVision/LivePortrait` | check repo | per README (audio fork needed) |

**Indian languages covered by Indic Parler-TTS:** Hindi, Tamil, Telugu, Bengali,
Gujarati, Kannada, Malayalam, Marathi, Punjabi, Odia, Assamese, Urdu, Kashmiri,
Sanskrit, Sindhi, Nepali (+ English).

---

## 6 · Honest gaps — what's still lacking

1. **Zero end-to-end GPU verification (BIGGEST).** Only Piper (CPU) has actually
   run. Chatterbox, Whisper-large, Indic Parler, and **all four avatar engines**
   have never produced output in this project. Every "matches commercial quality"
   claim is unproven until the notebooks are run.
2. **Avatars trail HeyGen even at best.** Open-source talking-head is head/face
   only, limited motion, sometimes uncanny. No full-body, gestures, or real-time
   interactive avatar.
3. **Streaming TTS isn't truly real-time.** Chatterbox synthesizes a whole
   sentence at once (~1 s first audio) vs ElevenLabs Flash (~75 ms).
4. **Not fully production-hardened.** In-process `asyncio` job queue (jobs die on
   restart, no retry); SQLite is single-writer (won't scale past one process); no
   TLS story documented. Upload caps / rate limiting / cleanup are in place.
5. **Missing commercial features:** ~~integrated dubbing pipeline~~ (done — see
   feature 13), video timeline/multi-scene, caption burn-in, programmatic API/SDK,
   team roles, **avatar-engine license audit** before sale.
6. **Dubbing's video path is also unverified.** The mux fallback only needs
   `ffmpeg` (untested here — not installed in this sandbox); the MuseTalk
   lip-resync path is wired but has never run (same GPU-verification gap as #1).

---

## 7 · Environment constraints (learned the hard way)

- **This dev sandbox blocks `huggingface.co`, `kaggle.com`, AND `api.x.ai`**
  (network allowlist; `x-deny-reason: host_not_allowed`) and has **no GPU**. →
  Claude **cannot run or verify the GPU models or Grok from here**, with or
  without API keys. Confirmed again in this session: Ollama isn't reachable
  either (nothing running on :11434), so the dub pipeline's translate step
  fails cleanly here with a descriptive error — that's the expected, honest
  degradation path, not a bug.
- Font CDNs (`fonts.googleapis.com`, `api.fontshare.com`) are also blocked — which
  is *why* the frontend ships self-hosted system fonts.
- **`ffmpeg` is not installed in this sandbox either.** Video dubbing's mux/
  extract steps are therefore covered by mocks in the test suite, never by a
  real `ffmpeg` invocation here. Audio-only dubbing has no such dependency.
- **Verification happens on the user's side** (Colab/Kaggle). Don't burn time
  trying to make it work in-sandbox.

---

## 8 · How to run & verify

### Easiest quality check (non-technical, ~5 min, no key)
1. **colab.research.google.com** → File → Upload notebook → `notebooks/arcvox_quicklisten.ipynb`
2. Runtime → Change runtime type → **GPU** → Save
3. Runtime → **Run all**, wait ~5–8 min, press ▶ on the audio players.
   → Hear English + Hindi voices and a transcription. No uploads, no keys.

### Full engine test (clone + avatar + 21 Indian languages)
`notebooks/arcvox_gpu_verify.ipynb` — needs a free **HF token** (for the gated
Indic Parler model) and a photo/voice upload. Every step is documented inside.

### Local dev
```bash
# backend
cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp ../.env.example .env        # set JWT_SECRET; optionally LLM_PROVIDER/keys
bash ../scripts/setup_models.sh
.venv/bin/python -m uvicorn server:app --port 8001
# frontend
cd frontend && yarn install
REACT_APP_BACKEND_URL=http://localhost:8001 yarn start
# tests (no GPU needed — engines mocked)
cd backend && .venv/bin/python -m pytest tests/ -v
```

### Engine selection (in `backend/.env`)
- `TTS_ENGINE=auto` — Chatterbox if installed, else Piper (default)
- `TTS_ENGINE=chatterbox` — HD + voice cloning (English/global)
- `TTS_ENGINE=indic_parler` — 21 Indian languages (needs `HF_TOKEN`)
- `TTS_ENGINE=multi` — **auto-route per request by script** (recommended for
  English + Indian in one deployment)
- `LLM_PROVIDER=ollama|grok` · `WHISPER_MODEL=large-v3` · `AVATAR_ENGINE=sadtalker|musetalk|echomimic|liveportrait|none`

---

## 9 · Decisions log (don't re-litigate)

| Decision | Why |
|---|---|
| **No model training, ever** | Infeasible (millions $, months); pretrained open weights already match commercial quality |
| Self-host pretrained MIT/Apache models | Commercial-safe, free, private |
| SQLite over MongoDB | One local file = total operator data control, no DB server |
| User uploads own photo for avatars | Privacy + no hallucinated faces |
| Grok is opt-in & loudly flagged | Honesty — cloud LLM contradicts "fully private" unless disclosed |
| No analytics/trackers/external fonts | A privacy product must not phone home |
| Indic Parler-TTS for Indian langs | Apache-2.0, 21 languages, the authoritative Indian lab (AI4Bharat) |
| `multi` routing by Unicode script | One deployment serves English + Indian without operator choosing |
| Dubbing defaults to ffmpeg audio-mux, MuseTalk lip-resync optional | Reuses existing STT/LLM/TTS engines with zero new ML deps; works on any host, upgrades automatically when `AVATAR_ENGINE=musetalk` is configured |

---

## 10 · Immediate next steps (the resume point)

1. **USER ACTION — run `arcvox_quicklisten.ipynb` on Colab** and judge the voice
   quality. This is the single thing blocking everything else. Report back how the
   English + Hindi voices sound.
2. Then run `arcvox_gpu_verify.ipynb` for cloning, avatars, and Tamil/Telugu/Hindi.
3. **Decide:** is zero-shot clone fidelity enough, or do we add an optional
   per-voice **fine-tuning** tier (hours on a GPU — *not* base training)?
4. **Security:** rotate the Grok and Kaggle keys that were pasted in chat.
5. Future build backlog: real job queue (Arq/Celery) for avatar + dub jobs;
   avatar-engine license audit; revisit LongCat when its inference path
   matures.

---

*Everything above is committed and pushed to `claude/arc-vox-analysis-fpn183`.
Feed this file back to Claude next session to continue without losing context.*
