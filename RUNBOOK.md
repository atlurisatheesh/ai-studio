# ArcVox Private Studio — Complete Runbook

> **Hand this file to any agent or person.** It contains everything needed to
> clone the repo, run backend tests, build the frontend, verify engines on a
> Kaggle GPU, and exercise the full API end-to-end. No prior context required.

---

## 1 · What is ArcVox?

A **self-hosted HeyGen + ElevenLabs alternative**. Voice synthesis, voice
cloning, transcription, dubbing, and avatar lipsync — all running on hardware
you control. The only optional cloud component is the LLM (for translation /
scripts / voice-agent chat), clearly disclosed.

**Repository:** `atlurisatheesh/ai-studio`
**Branch:** `claude/arc-vox-analysis-fpn183`

---

## 2 · Architecture at a glance

```
frontend/          React (CRA), Tailwind, Phosphor Icons
backend/
  server.py        FastAPI entry point (uvicorn)
  core/
    config.py      All env-var-driven configuration
    db.py          SQLite schema + async connection (aiosqlite)
    security.py    JWT + API-key auth, password hashing, project autosave
    uploads.py     Capped file reader
    cleanup.py     Output TTL purge loop
    ratelimit.py   Per-IP rate limiting middleware
  engines/
    tts.py         Chatterbox / Indic Parler-TTS / Piper (3 backends, auto-routed)
    stt.py         faster-whisper (Whisper large-v3)
    llm.py         Ollama (local) or Grok/xAI (cloud, opt-in)
    avatar.py      SadTalker / MuseTalk / EchoMimic / LivePortrait
    dub.py         Dubbing pipeline: transcribe → translate → re-voice → mux/lip-resync
    subtitles.py   SRT/VTT caption generation with line-aligned translation
  routers/
    auth.py        Register / login / logout / me
    voice.py       TTS, streaming TTS, voice library, clone management
    ai.py          Script writer, translator, voice agent chat
    avatar.py      Avatar job creation + status
    dub.py         Dubbing job creation + status + language list
    api_keys.py    Programmatic API key CRUD (create/list/revoke)
    projects.py    Project library CRUD
    misc.py        Root, stats, engine status, asset serving
  tests/
    test_api.py    23 tests — full HTTP/auth/storage stack, engines mocked
```

---

## 3 · Run backend tests (no GPU, no network, no models needed)

All AI engines are mocked in the test suite. This verifies the complete
HTTP / auth / storage / job-lifecycle stack.

```bash
# Clone and enter the repo
git clone https://github.com/atlurisatheesh/ai-studio.git
cd ai-studio
git checkout claude/arc-vox-analysis-fpn183

# Set up the backend
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# Run all 23 tests
.venv/bin/python -m pytest tests/ -v
```

**Expected:** `23 passed`. Every test should pass on any machine (no GPU, no
ffmpeg, no Ollama, no Whisper model needed).

**What the tests cover:**
- Auth flow (register, login, JWT, cookie, API key auth)
- TTS generation + voice library
- Transcription
- Voice cloning lifecycle
- Script / translate / voice-agent
- Avatar job lifecycle
- Dubbing pipeline (audio job, video job with mocked ffmpeg, bad-extension rejection)
- Line-aligned caption generation (SRT/VTT)
- Crash-resilient job resume after simulated restart
- API key full lifecycle (create, authenticate, list, revoke, revoked key rejected)
- Asset path traversal blocked (security)
- Upload size limit enforced
- Engine status endpoint reports all 5 engine groups

---

## 4 · Build the frontend (no backend needed)

```bash
cd frontend
yarn install
yarn build
```

**Expected:** `Compiled successfully` with zero errors. There is one pre-existing
ESLint warning in `ProjectsPage.jsx` (`react-hooks/exhaustive-deps`) that
predates all feature work — it is not a regression.

---

## 5 · Run the live backend (development mode)

```bash
cd backend
cp ../.env.example .env
# Edit .env: set JWT_SECRET to any 32+ char string

# Optionally install model dependencies:
# pip install chatterbox-tts          # HD voice + cloning (GPU)
# pip install faster-whisper           # transcription
# pip install git+https://github.com/huggingface/parler-tts.git  # Indian languages

.venv/bin/python -m uvicorn server:app --port 8001 --reload
```

Then in another terminal:
```bash
cd frontend
REACT_APP_BACKEND_URL=http://localhost:8001 yarn start
```

Open `http://localhost:3000`. First boot creates an admin account using
`ADMIN_EMAIL` from `.env`; if `ADMIN_PASSWORD` is unset, a random one is
printed once in the backend logs.

### Key API endpoints to exercise

| Endpoint | Method | Auth | Purpose |
|---|---|---|---|
| `/api/` | GET | No | Health check (`self_hosted: true`) |
| `/api/engines/status` | GET | No | All engine statuses (stt, tts, llm, avatar, dub) |
| `/api/auth/register` | POST | No | `{email, password, name}` → JWT |
| `/api/auth/login` | POST | No | `{email, password}` → JWT |
| `/api/auth/me` | GET | Yes | Current user info |
| `/api/voice/tts` | POST | Yes | `{text, voice, speed}` → WAV |
| `/api/voice/tts/stream` | POST | Yes | Streaming TTS (WAV per sentence) |
| `/api/voice/library` | GET | Yes | System voices + user's cloned voices |
| `/api/voice/clone` | POST | Yes | Upload sample → start clone |
| `/api/transcribe` | POST | Yes | Upload audio → `{text, language, segments}` |
| `/api/ai/script` | POST | Yes | `{prompt, tone, length}` → script text |
| `/api/ai/translate` | POST | Yes | `{text, target_language, tone}` → translated |
| `/api/agent/chat` | POST | Yes | `{session_id, message}` → voice-agent reply |
| `/api/avatar/generate` | POST | Yes | Upload photo + script → avatar job |
| `/api/avatar/jobs/{id}` | GET | Yes | Avatar job status/result |
| `/api/dub/languages` | GET | No | Available dubbing target languages (26+) |
| `/api/dub/generate` | POST | Yes | Upload clip + target language → dub job |
| `/api/dub/jobs/{id}` | GET | Yes | Dub job status/result (incl. caption URLs) |
| `/api/dub/jobs` | GET | Yes | List user's dub jobs |
| `/api/keys` | POST | Yes | `{name}` → API key (shown once) |
| `/api/keys` | GET | Yes | List user's API keys |
| `/api/keys/{id}` | DELETE | Yes | Revoke an API key |
| `/api/projects` | GET | Yes | Project library |
| `/api/assets/{name}` | GET | No | Download generated files (WAV, MP4, SRT, VTT) |

**Auth:** send `Authorization: Bearer <jwt_or_api_key>` header, or the
`access_token` httpOnly cookie is set automatically by login/register.

---

## 6 · GPU engine verification on Kaggle

This is the critical step. The backend tests mock all AI engines, so they
prove the *plumbing* works. This section proves the *AI engines themselves*
produce commercial-grade output on real hardware.

### 6a · Quick Listen (5 minutes, zero setup)

**What it proves:** Chatterbox voice quality (English + Hindi) and Whisper
transcription accuracy.

**Requirements:** Kaggle account with GPU enabled (free tier is fine — uses
a T4 16GB).

```
1. Go to https://www.kaggle.com → New Notebook
2. Upload notebooks/arcvox_quicklisten.ipynb
3. Settings → Accelerator → GPU T4 x2 (or any GPU option)
4. Settings → Internet → ON
5. Click "Run All"
6. Wait ~5-8 minutes (first-time model download)
7. Listen to the English and Hindi audio players
8. Check the Whisper transcription output matches what was said
```

**Cells in order and what each does:**

| Cell | Action | Expected output |
|---|---|---|
| 1 | `!nvidia-smi` | Shows T4 GPU info |
| 2 | `!pip install -q chatterbox-tts` | Installs Chatterbox (~1-2 min) |
| 3 | Generates English + Hindi voice | Two audio players appear; press play |
| 4 | Frees GPU memory | "ok" |
| 5 | `!pip install -q faster-whisper` | Installs Whisper |
| 6 | Transcribes both clips | English text + Hindi text printed correctly |

**Pass criteria:**
- English voice is clear, natural, studio-grade (not robotic)
- Hindi voice pronounces Devanagari text correctly
- Whisper transcription matches the generated text closely
- No CUDA out-of-memory errors

### 6b · Full Verification (20-30 minutes, tests everything)

**What it proves:** Voice quality, zero-shot voice cloning, Indian-language TTS
(Tamil/Telugu/Hindi via AI4Bharat), Whisper transcription of Indian languages,
and SadTalker talking-head avatar generation.

**Extra requirements:**
- A Hugging Face token (free) with access to `ai4bharat/indic-parler-tts`
  (accept terms at https://hf.co/ai4bharat/indic-parler-tts first)
- A 10-30 second voice sample (WAV/MP3) for cloning test
- A clear, front-facing portrait photo for avatar test

```
1. Go to https://www.kaggle.com → New Notebook
2. Upload notebooks/arcvox_gpu_verify.ipynb
3. Settings → Accelerator → GPU T4 x2
4. Settings → Internet → ON
5. Run cells top to bottom (some require file upload prompts)
```

**Cells in order:**

| Section | Cells | What it does | Expected output |
|---|---|---|---|
| 0 · GPU check | 1-2 | `nvidia-smi` + env detect | T4 GPU, "Kaggle" or "Colab" |
| 1 · Chatterbox | 3-6 | Install, English TTS, Hindi TTS, voice clone | 3 audio files play correctly; `arcvox_clone.wav` sounds like your uploaded sample |
| 1b · Indic Parler | 7-9 | Install, HF login, Tamil + Telugu + Hindi TTS | 3 audio files in native languages |
| 2 · Whisper | 10-12 | Install, transcribe all 5 clips | Correct text + language detection for each |
| 3 · SadTalker | 13-17 | Clone repo, install, download models, generate video | An `.mp4` where the portrait's mouth moves to the audio |

**Pass criteria for each engine:**

| Engine | Pass | Fail |
|---|---|---|
| **Chatterbox English** | Clear, natural voice; not robotic | Garbled, static, silence |
| **Chatterbox Hindi** | Correct Hindi pronunciation from Devanagari | Wrong language or gibberish |
| **Voice clone** | Recognizably the same person as the sample | Completely different voice |
| **Indic Parler Tamil** | Correct Tamil from Tamil script | Wrong language |
| **Indic Parler Telugu** | Correct Telugu from Telugu script | Wrong language |
| **Indic Parler Hindi** | Correct Hindi (compare with Chatterbox Hindi) | Wrong language |
| **Whisper English** | Text matches generated text ≥90% | Major misses |
| **Whisper Hindi** | Detects Hindi, text roughly matches | Wrong language detection |
| **Whisper Tamil** | Detects Tamil, text roughly matches | Wrong language detection |
| **SadTalker** | Mouth moves in sync with audio; face looks natural | No video / face distorted / no lip sync |

### 6c · Kaggle-specific notes

- Kaggle's file upload works differently from Colab. For voice cloning and
  avatar cells, you may need to upload files via the "Add Data" sidebar or
  set file paths manually in the cell:
  ```python
  ref = "/kaggle/input/my-voice/sample.wav"      # voice clone sample
  photo = "/kaggle/input/my-photo/portrait.jpg"   # avatar photo
  ```
- Kaggle sessions have a 12-hour limit and 30 hours/week of GPU quota.
- If a cell OOMs, re-run the "Free memory" cell above it and try again.
  The notebook is designed to unload each model before loading the next.
- SadTalker is the most fragile install (specific dependency pins). If it
  fails, the voice + transcription verification above still stands — avatar
  is the weakest module vs HeyGen anyway.

---

## 7 · End-to-end API test script (for programmatic verification)

After the backend is running (`uvicorn server:app --port 8001`), this script
exercises the full flow including the new features (dubbing, captions, API keys):

```bash
#!/usr/bin/env bash
# End-to-end API smoke test. Requires: curl, jq, a running backend on :8001
set -euo pipefail
BASE="http://localhost:8001/api"

echo "=== 1. Health check ==="
curl -s "$BASE/" | jq .

echo "=== 2. Engine status ==="
curl -s "$BASE/engines/status" | jq .

echo "=== 3. Register ==="
TOKEN=$(curl -s -X POST "$BASE/auth/register" \
  -H 'Content-Type: application/json' \
  -d '{"email":"test@example.com","password":"testpass123","name":"Tester"}' \
  | jq -r .access_token)
echo "JWT: ${TOKEN:0:20}..."
AUTH="Authorization: Bearer $TOKEN"

echo "=== 4. Who am I ==="
curl -s -H "$AUTH" "$BASE/auth/me" | jq .

echo "=== 5. Dubbing languages ==="
curl -s "$BASE/dub/languages" | jq '.[0:5]'

echo "=== 6. TTS (if engine installed) ==="
curl -s -X POST -H "$AUTH" \
  -F 'text=Hello from ArcVox' -F 'voice=studio' \
  "$BASE/voice/tts" -o /tmp/arcvox_test.wav \
  && echo "Saved /tmp/arcvox_test.wav ($(stat -c%s /tmp/arcvox_test.wav 2>/dev/null || stat -f%z /tmp/arcvox_test.wav) bytes)" \
  || echo "(TTS engine not installed — expected on CPU-only boxes)"

echo "=== 7. Create an API key ==="
KEY_JSON=$(curl -s -X POST -H "$AUTH" \
  -H 'Content-Type: application/json' \
  -d '{"name":"e2e-test-key"}' \
  "$BASE/keys")
echo "$KEY_JSON" | jq '{id,name,prefix}'
API_KEY=$(echo "$KEY_JSON" | jq -r .key)

echo "=== 8. Auth with API key ==="
curl -s -H "Authorization: Bearer $API_KEY" "$BASE/auth/me" | jq .email

echo "=== 9. Revoke API key ==="
KEY_ID=$(echo "$KEY_JSON" | jq -r .id)
curl -s -X DELETE -H "$AUTH" "$BASE/keys/$KEY_ID" | jq .

echo "=== 10. Revoked key fails ==="
HTTP_CODE=$(curl -s -o /dev/null -w '%{http_code}' \
  -H "Authorization: Bearer $API_KEY" "$BASE/auth/me")
echo "Expected 401, got: $HTTP_CODE"

echo "=== DONE ==="
```

---

## 8 · Environment variables reference

Copy `.env.example` to `.env` and set at minimum `JWT_SECRET`. Full reference:

| Variable | Default | Purpose |
|---|---|---|
| `JWT_SECRET` | **(required)** | Auth signing key. Generate: `python3 -c "import secrets; print(secrets.token_hex(32))"` |
| `ADMIN_EMAIL` | `admin@arcvox.ai` | Seeded admin account email |
| `ADMIN_PASSWORD` | (auto-generated) | Seeded admin password (printed in logs if unset) |
| `WHISPER_MODEL` | `small` | STT accuracy: `tiny < base < small < medium < large-v3` |
| `WHISPER_DEVICE` | `auto` | `auto` / `cpu` / `cuda` |
| `TTS_ENGINE` | `auto` | `auto` / `chatterbox` / `indic_parler` / `multi` / `piper` |
| `HF_TOKEN` | (empty) | Hugging Face token — only needed for gated Indic Parler-TTS |
| `LLM_PROVIDER` | `ollama` | `ollama` (local) or `grok` (cloud, opt-in) |
| `OLLAMA_MODEL` | `llama3.1:8b` | Which Ollama model for scripts/translate/agent |
| `GROK_API_KEY` | (empty) | xAI API key — only used when `LLM_PROVIDER=grok` |
| `GROK_MODEL` | `grok-3-mini` | `grok-3-mini` / `grok-3` / `grok-beta` |
| `AVATAR_ENGINE` | `none` | `none` / `sadtalker` / `musetalk` / `echomimic` / `liveportrait` |
| `SADTALKER_DIR` | (empty) | Path to SadTalker checkout |
| `MUSETALK_DIR` | (empty) | Path to MuseTalk checkout |
| `ECHOMIMIC_DIR` | (empty) | Path to EchoMimic checkout |
| `LIVEPORTRAIT_DIR` | (empty) | Path to LivePortrait checkout |
| `AVATAR_PYTHON` | `python3` | Python interpreter for the avatar engine's venv |
| `MAX_UPLOAD_MB` | `50` | Max single file upload size |
| `OUTPUT_TTL_HOURS` | `48` | Auto-purge outputs older than this (0 = off) |
| `RATE_LIMIT_PER_MINUTE` | `120` | Per-IP request cap (0 = off) |
| `CORS_ORIGINS` | `http://localhost:3000` | Comma-separated allowed origins |

---

## 9 · Feature inventory (what's built, with commit SHAs)

| # | Feature | Key files | Commit |
|---|---|---|---|
| 1 | Full backend + frontend (Phase 1+2) | everything | `59e0d47` |
| 2 | Streaming TTS + EchoMimic + LivePortrait | engines/tts.py, avatar.py | `741740c` |
| 3 | LLM streaming + word timestamps UI | engines/llm.py | `8866c1d` |
| 4 | Grok/xAI cloud LLM backend | engines/llm.py, config.py | `26390a7` |
| 5 | Privacy hardening + production features | security.py, ratelimit.py | `bc0aee0` |
| 6 | GPU verification notebook | notebooks/ | `f0f4faa` |
| 7 | Indian-language TTS (21 languages) | engines/tts.py | `5faaf5c` |
| 8 | Multi-engine auto-routing by script | engines/tts.py | `058a488` |
| 9 | Quick-listen notebook | notebooks/ | `41c2485` |
| 10 | Project handoff doc | PROJECT_HANDOFF.md | `896d7fa` |
| 11 | Integrated dubbing pipeline | engines/dub.py, routers/dub.py, DubbingStudio.jsx | `0a29e86` |
| 12 | Timed SRT/VTT captions | engines/subtitles.py, dub.py | `024f8d2` |
| 13 | Crash-resilient jobs (auto-resume) | dub.py, avatar.py, server.py | `7e1cf97` |
| 14 | Programmatic API keys | security.py, routers/api_keys.py, ApiKeysPage.jsx | `ed0c155` |

---

## 10 · Known gaps (honest)

1. **GPU engines never verified on real hardware.** Every engine is wired up,
   tested with mocks, and the notebooks are ready — but no human has run
   them yet. This is the #1 blocker. Section 6 above is the fix.

2. **Avatars are behind HeyGen.** SadTalker/MuseTalk are solid open-source
   but not photoreal. EchoMimic is closest. This is a known open-vs-commercial
   gap; we win on privacy and cost instead.

3. **Voice latency.** Chatterbox generates a full sentence at once (~1s first
   audio) vs ElevenLabs Flash (~75ms). Not yet addressed.

4. **Dubbing is single-speaker.** No diarization — multi-speaker clips get
   merged into one voice. Needs `pyannote-audio` (GPU + HF token).

5. **No caption burn-in to video.** SRT/VTT sidecar files are generated but
   not burned into the video frame. Needs `ffmpeg` subtitle filter.

6. **SQLite single-writer.** Fine for single-box self-hosted (the design
   target). Won't scale past one process without switching to Postgres.

7. **No TLS docs.** Production deployments need a reverse proxy (nginx/Caddy)
   for HTTPS — not documented yet.

---

## 11 · Security notes

- `backend/.env` is gitignored and must **never** be committed. It contains
  `JWT_SECRET`, optionally `GROK_API_KEY`, `HF_TOKEN`.
- API keys are stored as SHA-256 hashes only — the plaintext is returned once
  at creation and never retrievable again.
- Path traversal on `/api/assets/{name}` is blocked (tested).
- Upload size is capped (`MAX_UPLOAD_MB`).
- Per-IP rate limiting is enabled by default (120/min).
- File extension allowlisting on dub uploads (audio/video only).
- All passwords are bcrypt-hashed.

---

## 12 · Comparing against an older/local copy of the project

If you (or another agent) have a pre-existing local copy of this project —
e.g. `D:\ARC_VOX-main` (the `-main` suffix is the standard name Windows/GitHub
gives a folder when you "Download ZIP" a repo's default branch) — and want to
know exactly what differs from this branch, don't eyeball it. Run a real diff.

**This sandbox cannot read your local filesystem** (`D:\...` paths don't
exist outside your machine), so this has to run wherever the local copy
lives — your machine, or an agent with filesystem access to it (Antigravity).

```bash
# 1. Clone a FRESH copy of this exact branch next to the old one.
#    (Git Bash on Windows: D:\ maps to /d/)
cd /d/
git clone --branch claude/arc-vox-analysis-fpn183 --single-branch \
  https://github.com/atlurisatheesh/ai-studio.git ai-studio-github

# 2. List every file that's new, removed, or changed (names only — fast).
diff -rq \
  --exclude=.git --exclude=node_modules --exclude=__pycache__ \
  --exclude=.venv --exclude=build --exclude=data --exclude=.pytest_cache \
  /d/ARC_VOX-main /d/ai-studio-github | sort

# 3. Full line-by-line diff for everything that changed (slower, saved to a file).
diff -ru \
  --exclude=.git --exclude=node_modules --exclude=__pycache__ \
  --exclude=.venv --exclude=build --exclude=data --exclude=.pytest_cache \
  /d/ARC_VOX-main /d/ai-studio-github > /d/arcvox_diff_full.txt
```

Reading the output of step 2:
- `Only in /d/ARC_VOX-main: <path>` → exists in your old copy but not here (either you built something locally that never made it into this branch, or it was intentionally removed/renamed).
- `Only in /d/ai-studio-github: <path>` → added on this branch since your local copy was made (cross-check against the commit list in §9 above).
- `Files ... differ` → same file, different content — see the matching block in `arcvox_diff_full.txt` for the exact lines.

No Git Bash available? PowerShell-only equivalent:

```powershell
cd D:\
git clone --branch claude/arc-vox-analysis-fpn183 --single-branch https://github.com/atlurisatheesh/ai-studio.git ai-studio-github

function Get-RelFiles($root) {
  Get-ChildItem -Recurse -File $root |
    Where-Object { $_.FullName -notmatch '\\(\.git|node_modules|__pycache__|\.venv|build|data|\.pytest_cache)\\' } |
    ForEach-Object { $_.FullName.Substring($root.Length).TrimStart('\') }
}
Compare-Object (Get-RelFiles "D:\ARC_VOX-main") (Get-RelFiles "D:\ai-studio-github") | Sort-Object SideIndicator
# <=  → only in ARC_VOX-main      =>  → only in ai-studio-github (added since)
```

The current branch's full feature/commit inventory is in §9 above — use it
to tell intentional, documented changes apart from anything unexpected the
diff turns up.

---

## 13 · For the agent running this

**Your checklist:**

- [ ] Clone `atlurisatheesh/ai-studio`, branch `claude/arc-vox-analysis-fpn183`
- [ ] Run `cd backend && pip install -r requirements.txt && python -m pytest tests/ -v` → 23 passed
- [ ] Run `cd frontend && yarn install && yarn build` → compiled successfully
- [ ] On Kaggle with GPU: run `notebooks/arcvox_quicklisten.ipynb` → listen to English + Hindi voice, check Whisper transcription
- [ ] On Kaggle with GPU + HF token: run `notebooks/arcvox_gpu_verify.ipynb` → test cloning, Indian languages, avatar
- [ ] Report: which engines passed, which failed, subjective voice quality rating (1-10 vs ElevenLabs), any errors encountered
- [ ] If all pass: the product thesis is validated. If voice quality is bad: the thesis fails regardless of code quality.

---

*Generated from commit `ed0c155` on branch `claude/arc-vox-analysis-fpn183`.*
