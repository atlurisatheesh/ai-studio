"""API tests — AI engines are mocked so these verify the full HTTP/auth/
storage stack on any machine, with or without a GPU."""
import io
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("DATA_DIR", tempfile.mkdtemp(prefix="arcvox_test_"))
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("ADMIN_PASSWORD", "test-admin-pass")
os.environ.setdefault("RATE_LIMIT_PER_MINUTE", "0")   # disable per-IP cap during tests
os.environ.setdefault("MAX_UPLOAD_MB", "5")           # small cap so the size test is cheap
os.environ.setdefault("OUTPUT_TTL_HOURS", "0")        # no cleanup timer in tests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from fastapi.testclient import TestClient

from engines import tts, stt, llm, dub as dub_engine
from server import app

FAKE_WAV = b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00" + b"\x00" * 20


@pytest.fixture(autouse=True)
def mock_engines(monkeypatch):
    async def fake_synthesize(text, voice="studio", speed=1.0, clone_sample=None, language="auto"):
        return FAKE_WAV

    async def fake_synthesize_stream(text, voice="studio", speed=1.0, clone_sample=None, language="auto"):
        # Yield two chunks to simulate sentence streaming
        yield FAKE_WAV
        yield FAKE_WAV

    async def fake_transcribe(path):
        return {"text": "hello world", "language": "en", "language_probability": 0.99,
                "duration": 1.0, "segments": [
                    {"start": 0.0, "end": 0.5, "text": "hello"},
                    {"start": 0.5, "end": 1.0, "text": "world"},
                ]}

    async def fake_chat(system, messages, temperature=0.7):
        return "mocked reply"

    async def fake_complete(system, prompt, temperature=0.7):
        return "mocked output"

    async def fake_chat_stream(system, messages, temperature=0.7):
        yield "mocked "
        yield "reply."

    monkeypatch.setattr(tts, "synthesize", fake_synthesize)
    monkeypatch.setattr(tts, "synthesize_stream", fake_synthesize_stream)
    monkeypatch.setattr(stt, "transcribe", fake_transcribe)
    monkeypatch.setattr(llm, "chat", fake_chat)
    monkeypatch.setattr(llm, "complete", fake_complete)
    monkeypatch.setattr(llm, "chat_stream", fake_chat_stream)


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def auth_headers(client):
    r = client.post("/api/auth/register", json={
        "email": "creator@example.com", "password": "password123", "name": "Creator"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_root_and_engine_status(client):
    assert client.get("/api/").json()["self_hosted"] is True
    s = client.get("/api/engines/status").json()
    assert {"stt", "tts", "llm", "avatar", "dub"} <= set(s)
    # privacy must be reported honestly
    assert "cloud_llm_active" in s and "llm_provider" in s and "privacy" in s
    # default test env uses local Ollama → not cloud
    assert s["cloud_llm_active"] is False
    assert "No external AI APIs" in s["privacy"]


def test_upload_size_limit(client, auth_headers):
    # MAX_UPLOAD_MB=5 in test env → a 6 MB upload must be rejected with 413
    big = io.BytesIO(b"\x00" * (6 * 1024 * 1024))
    r = client.post("/api/voice/transcribe",
                    files={"file": ("big.wav", big, "audio/wav")},
                    headers=auth_headers)
    assert r.status_code == 413, r.status_code
    assert "too large" in r.json()["detail"].lower()


def test_auth_flow(client):
    r = client.post("/api/auth/register", json={
        "email": "user2@example.com", "password": "password123", "name": "U2"})
    assert r.status_code == 200
    token = r.json()["access_token"]
    # duplicate rejected
    assert client.post("/api/auth/register", json={
        "email": "user2@example.com", "password": "password123", "name": "U2"}).status_code == 400
    # login + me
    r = client.post("/api/auth/login", json={"email": "user2@example.com", "password": "password123"})
    assert r.status_code == 200
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.json()["email"] == "user2@example.com"
    # bad password
    assert client.post("/api/auth/login", json={
        "email": "user2@example.com", "password": "wrong"}).status_code == 401
    # admin seeded, never reset
    r = client.post("/api/auth/login", json={"email": "admin@arcvox.ai", "password": "test-admin-pass"})
    assert r.status_code == 200
    assert r.json()["user"]["role"] == "admin"


def test_requires_auth(client):
    client.cookies.clear()  # drop httpOnly cookie set by earlier logins
    assert client.get("/api/projects").status_code == 401
    assert client.post("/api/voice/tts", json={"text": "hi"}).status_code == 401


def test_tts_and_library(client, auth_headers):
    r = client.post("/api/voice/tts", json={"text": "Hello from my own server", "voice": "studio"},
                    headers=auth_headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["format"] == "wav" and body["audio_base64"]
    assert body["project"]["kind"] == "tts"

    lib = client.get("/api/voice/library", headers=auth_headers).json()
    assert "system" in lib and "cloned" in lib and "engine" in lib


def test_transcribe(client, auth_headers):
    r = client.post("/api/voice/transcribe",
                    files={"file": ("clip.wav", io.BytesIO(FAKE_WAV), "audio/wav")},
                    headers=auth_headers)
    assert r.status_code == 200, r.text
    assert r.json()["text"] == "hello world"
    assert r.json()["language"] == "en"


def test_voice_clone_and_use(client, auth_headers):
    r = client.post("/api/voice/clone",
                    data={"name": "My Voice", "description": "test"},
                    files={"sample": ("me.wav", io.BytesIO(FAKE_WAV), "audio/wav")},
                    headers=auth_headers)
    assert r.status_code == 200, r.text
    voice_id = r.json()["id"]
    assert voice_id.startswith("cv_")
    assert "sample_path" not in r.json()  # internal path never exposed

    # cloned voice usable in TTS
    r = client.post("/api/voice/tts", json={"text": "cloned speech", "voice": voice_id},
                    headers=auth_headers)
    assert r.status_code == 200

    # appears in library, then delete
    lib = client.get("/api/voice/library", headers=auth_headers).json()
    assert any(v["id"] == voice_id for v in lib["cloned"])
    assert client.delete(f"/api/voice/clone/{voice_id}", headers=auth_headers).status_code == 200


def test_script_translate_agent(client, auth_headers):
    r = client.post("/api/ai/script", json={"topic": "my product", "style": "casual",
                                            "length": "short"}, headers=auth_headers)
    assert r.status_code == 200 and r.json()["script"] == "mocked output"

    r = client.post("/api/ai/translate", json={"text": "hello", "target_language": "Telugu"},
                    headers=auth_headers)
    assert r.status_code == 200 and r.json()["translated"] == "mocked output"

    r = client.post("/api/agent/chat", json={"session_id": "s1", "message": "hi"},
                    headers=auth_headers)
    assert r.status_code == 200 and r.json()["reply"] == "mocked reply"
    sess = client.get("/api/agent/session/s1", headers=auth_headers).json()
    assert len(sess["messages"]) == 2


def test_avatar_job(client, auth_headers):
    png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
    r = client.post("/api/avatar/generate",
                    data={"script": "Welcome to my channel", "voice": "studio"},
                    files={"portrait": ("me.png", io.BytesIO(png), "image/png")},
                    headers=auth_headers)
    assert r.status_code == 200, r.text
    job_id = r.json()["id"]
    assert r.json()["status"] in ("queued", "processing")

    # poll until background task finishes (mocked TTS → preview mode)
    import time
    for _ in range(50):
        j = client.get(f"/api/avatar/jobs/{job_id}", headers=auth_headers).json()
        if j["status"] not in ("queued", "processing"):
            break
        time.sleep(0.1)
    assert j["status"] == "completed_preview", j
    assert j["url"]

    jobs = client.get("/api/avatar/jobs", headers=auth_headers).json()
    assert any(x["id"] == job_id for x in jobs)

    # wrong-extension portrait rejected
    r = client.post("/api/avatar/generate",
                    data={"script": "x", "voice": "studio"},
                    files={"portrait": ("evil.exe", io.BytesIO(b"MZ"), "application/x-msdownload")},
                    headers=auth_headers)
    assert r.status_code == 400


def test_projects_crud(client, auth_headers):
    items = client.get("/api/projects", headers=auth_headers).json()
    assert len(items) >= 4  # tts, transcription, script, translation, avatar…
    pid = items[0]["id"]
    one = client.get(f"/api/projects/{pid}", headers=auth_headers).json()
    assert one["id"] == pid and isinstance(one["payload"], dict)
    assert client.delete(f"/api/projects/{pid}", headers=auth_headers).status_code == 200
    assert client.get(f"/api/projects/{pid}", headers=auth_headers).status_code == 404

    only_tts = client.get("/api/projects?kind=tts", headers=auth_headers).json()
    assert all(p["kind"] == "tts" for p in only_tts)


def test_agent_chat_stream(client, auth_headers):
    r = client.post("/api/agent/chat/stream",
                    json={"session_id": "stream_s1", "message": "hello"},
                    headers=auth_headers)
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("text/event-stream")
    import json as _json
    events = []
    for line in r.text.split("\n\n"):
        line = line.strip()
        if line.startswith("data: "):
            events.append(_json.loads(line[6:]))
    tokens = [e["token"] for e in events if "token" in e]
    done_ev = next((e for e in events if e.get("done")), None)
    assert tokens, "No token events received"
    assert done_ev, "No done event received"
    assert done_ev["text"] == "mocked reply."
    # History should be persisted
    sess = client.get("/api/agent/session/stream_s1", headers=auth_headers).json()
    assert any(m["role"] == "assistant" and "mocked" in m["text"] for m in sess["messages"])


def test_tts_stream(client, auth_headers):
    r = client.post("/api/voice/tts/stream",
                    json={"text": "Hello world. This is a streaming test.", "voice": "studio"},
                    headers=auth_headers)
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("text/event-stream")
    # Parse SSE events from the response body
    import base64, json as _json
    events = []
    for line in r.text.split("\n\n"):
        line = line.strip()
        if line.startswith("data: "):
            events.append(_json.loads(line[6:]))
    chunks = [e for e in events if "chunk" in e]
    done_events = [e for e in events if e.get("done")]
    assert len(chunks) == 2, f"Expected 2 chunks, got {chunks}"
    assert done_events, "No done event received"
    # Each chunk must be valid base64-encoded WAV
    for ev in chunks:
        decoded = base64.b64decode(ev["chunk"])
        assert decoded[:4] == b"RIFF"


def test_script_detection_and_routing():
    """Pure-function test of the multi-engine script router (no GPU needed)."""
    from engines import tts
    # Indic script detection
    assert tts.text_is_indic("வணக்கம் இது தமிழ் மொழி") is True      # Tamil
    assert tts.text_is_indic("నమస్తే ఇది తెలుగు భాష") is True       # Telugu
    assert tts.text_is_indic("नमस्ते यह हिन्दी है") is True          # Hindi
    assert tts.text_is_indic("Hello, this is plain English.") is False
    # Per-request routing used in TTS_ENGINE=multi mode
    assert tts._route_backend("வணக்கம்", None, "auto") == "indic_parler"      # Tamil script
    assert tts._route_backend("Hello world", None, "ta") == "indic_parler"    # explicit lang forces it
    assert tts._route_backend("வணக்கம்", "/tmp/s.wav", "auto") == "chatterbox"  # cloning forces Chatterbox
    assert tts._route_backend("Hello world", None, "auto") in ("chatterbox", "piper")


def test_asset_path_traversal_blocked(client):
    assert client.get("/api/assets/..%2F..%2Fetc%2Fpasswd").status_code == 404
    assert client.get("/api/assets/nonexistent.mp4").status_code == 404


def _poll_dub_job(client, job_id, headers):
    import time
    job = None
    for _ in range(50):
        job = client.get(f"/api/dub/jobs/{job_id}", headers=headers).json()
        if job["status"] not in ("queued", "processing"):
            break
        time.sleep(0.1)
    return job


def test_dub_languages(client):
    langs = client.get("/api/dub/languages").json()
    codes = {l["code"] for l in langs}
    assert {"hi", "ta", "te", "en", "es", "fr"} <= codes
    # no duplicates between Indic + global lists
    assert len(codes) == len(langs)


def test_dub_audio_job(client, auth_headers):
    """Translate + re-voice pipeline on a plain audio upload — no ffmpeg needed."""
    r = client.post(
        "/api/dub/generate",
        data={"target_language": "Hindi", "target_language_code": "hi", "voice": "studio"},
        files={"source": ("clip.wav", io.BytesIO(FAKE_WAV), "audio/wav")},
        headers=auth_headers,
    )
    assert r.status_code == 200, r.text
    job_id = r.json()["id"]
    assert r.json()["status"] in ("queued", "processing")

    job = _poll_dub_job(client, job_id, auth_headers)
    assert job["status"] == "completed", job
    assert job["mode"] == "audio"
    assert job["url"]
    assert job["transcript"] == "hello world"          # from mocked stt.transcribe
    assert job["translated_text"] == "mocked output"   # from mocked llm.complete

    # source captions are always produced from Whisper's timed segments
    assert job["source_srt_url"], job
    srt = client.get("/api" + job["source_srt_url"].removeprefix("/api"), headers=auth_headers)
    assert srt.status_code == 200
    assert "00:00:00,000 --> 00:00:00,500" in srt.text
    assert "hello" in srt.text

    jobs = client.get("/api/dub/jobs", headers=auth_headers).json()
    assert any(j["id"] == job_id for j in jobs)


def test_dub_aligned_captions(client, auth_headers, monkeypatch):
    """When the LLM returns one line per segment, timed target captions are emitted."""
    async def fake_aligned(system, prompt, temperature=0.7):
        # Mimic a translator that preserved the [n] markers
        return "[1] hola\n[2] mundo"
    monkeypatch.setattr(llm, "complete", fake_aligned)

    r = client.post(
        "/api/dub/generate",
        data={"target_language": "Spanish", "target_language_code": "es", "voice": "studio"},
        files={"source": ("clip.wav", io.BytesIO(FAKE_WAV), "audio/wav")},
        headers=auth_headers,
    )
    assert r.status_code == 200, r.text
    job = _poll_dub_job(client, r.json()["id"], auth_headers)
    assert job["status"] == "completed", job
    assert job["translated_text"] == "hola mundo"
    assert job["target_srt_url"] and job["target_vtt_url"], job

    vtt = client.get("/api" + job["target_vtt_url"].removeprefix("/api"), headers=auth_headers)
    assert vtt.status_code == 200
    assert vtt.text.startswith("WEBVTT")
    assert "hola" in vtt.text and "mundo" in vtt.text


def test_dub_resume_after_restart(client, auth_headers, monkeypatch):
    """A dub job left 'interrupted' by a crash is re-dispatched and finishes on boot.

    Uses an isolated SQLite connection on its own loop so it doesn't disturb the
    module-scoped TestClient's shared connection.
    """
    import asyncio
    import aiosqlite
    from core import db as dbmod
    from core.config import DB_PATH

    # Create + finish a real dub job through the app first.
    r = client.post(
        "/api/dub/generate",
        data={"target_language": "Hindi", "target_language_code": "hi", "voice": "studio"},
        files={"source": ("clip.wav", io.BytesIO(FAKE_WAV), "audio/wav")},
        headers=auth_headers,
    )
    job_id = r.json()["id"]
    assert _poll_dub_job(client, job_id, auth_headers)["status"] == "completed"

    async def crash_and_resume():
        conn = await aiosqlite.connect(DB_PATH)
        conn.row_factory = aiosqlite.Row

        async def fake_get_db():
            return conn
        monkeypatch.setattr(dbmod, "get_db", fake_get_db)

        # Simulate a crash mid-flight.
        await conn.execute("UPDATE dub_jobs SET status='interrupted' WHERE id=?", (job_id,))
        await conn.commit()

        n = await dub_engine.resume_incomplete()
        final = "interrupted"
        for _ in range(50):
            cur = await conn.execute("SELECT status FROM dub_jobs WHERE id=?", (job_id,))
            final = (await cur.fetchone())[0]
            if final not in ("queued", "processing"):
                break
            await asyncio.sleep(0.1)
        await conn.close()
        return n, final

    n, final = asyncio.run(crash_and_resume())
    assert n == 1
    assert final == "completed"


def test_subtitles_formatting():
    from engines import subtitles
    segs = [
        {"start": 0.0, "end": 1.25, "text": "first"},
        {"start": 1.25, "end": 3.0, "text": "second"},
    ]
    srt = subtitles.to_srt(segs)
    assert "1\n00:00:00,000 --> 00:00:01,250\nfirst" in srt
    assert "2\n00:00:01,250 --> 00:00:03,000\nsecond" in srt

    vtt = subtitles.to_vtt(segs)
    assert vtt.startswith("WEBVTT")
    assert "00:00:00.000 --> 00:00:01.250" in vtt

    # aligned-translation parsing round-trips, and rejects a count mismatch
    assert subtitles.parse_aligned_translation("[1] a\n[2] b", 2) == ["a", "b"]
    assert subtitles.parse_aligned_translation("[1] a", 2) is None


def test_diarize_pure():
    """Speaker reconciliation is pure logic — no model, no GPU needed to verify."""
    from engines import diarize
    segs = [
        {"start": 0.0, "end": 0.5, "text": "hello"},
        {"start": 0.5, "end": 1.0, "text": "world"},
    ]
    turns = [
        {"start": 0.0, "end": 0.5, "speaker": "SPEAKER_00"},
        {"start": 0.5, "end": 1.0, "speaker": "SPEAKER_01"},
    ]
    tagged = diarize.assign_speakers(segs, turns)
    assert [s["speaker"] for s in tagged] == ["SPEAKER_00", "SPEAKER_01"]
    assert diarize.speaker_count(turns) == 2

    labelled = diarize.label_segments_for_caption(tagged)
    assert labelled[0]["text"] == "[Speaker 1] hello"
    assert labelled[1]["text"] == "[Speaker 2] world"

    # No turns → untouched, untagged (preserves single-speaker behaviour).
    assert diarize.assign_speakers(segs, []) == segs
    # A single speaker gets no labels (labels would be noise).
    one = diarize.assign_speakers(segs, [{"start": 0.0, "end": 1.0, "speaker": "SPEAKER_00"}])
    assert diarize.label_segments_for_caption(one) == one


def test_dub_with_diarization(client, auth_headers, monkeypatch):
    """When diarization is available, captions get speaker labels and the job
    records the speaker count. The pyannote model is mocked — this verifies the
    wiring, not the ML."""
    from engines import diarize as diarize_engine

    async def fake_diarize(audio_path):
        return [
            {"start": 0.0, "end": 0.5, "speaker": "SPEAKER_00"},
            {"start": 0.5, "end": 1.0, "speaker": "SPEAKER_01"},
        ]
    monkeypatch.setattr(diarize_engine, "diarize", fake_diarize)

    r = client.post(
        "/api/dub/generate",
        data={"target_language": "Hindi", "target_language_code": "hi", "voice": "studio"},
        files={"source": ("clip.wav", io.BytesIO(FAKE_WAV), "audio/wav")},
        headers=auth_headers,
    )
    assert r.status_code == 200, r.text
    job = _poll_dub_job(client, r.json()["id"], auth_headers)
    assert job["status"] == "completed", job
    assert job["speaker_count"] == 2, job

    srt = client.get("/api" + job["source_srt_url"].removeprefix("/api"), headers=auth_headers)
    assert srt.status_code == 200
    assert "[Speaker 1] hello" in srt.text
    assert "[Speaker 2] world" in srt.text


def test_dub_video_job(client, auth_headers, monkeypatch):
    """Video dubbing falls back to a plain audio mux when no lipsync engine is configured.

    ffmpeg isn't installed in the test sandbox, so the ffmpeg-calling helpers
    are mocked here — the rest of the pipeline (STT/LLM/TTS) uses the same
    autouse mocks as every other test.
    """
    def fake_extract_audio(video_path, audio_out):
        Path(audio_out).write_bytes(FAKE_WAV)

    def fake_mux_audio(video_path, audio_path, video_out):
        Path(video_out).write_bytes(b"FAKEMP4")

    monkeypatch.setattr(dub_engine, "ffmpeg_available", lambda: True)
    monkeypatch.setattr(dub_engine, "_extract_audio", fake_extract_audio)
    monkeypatch.setattr(dub_engine, "_mux_audio", fake_mux_audio)

    r = client.post(
        "/api/dub/generate",
        data={"target_language": "Tamil", "target_language_code": "ta", "voice": "studio"},
        files={"source": ("clip.mp4", io.BytesIO(b"FAKE-VIDEO-BYTES"), "video/mp4")},
        headers=auth_headers,
    )
    assert r.status_code == 200, r.text
    job_id = r.json()["id"]

    job = _poll_dub_job(client, job_id, auth_headers)
    assert job["status"] == "completed", job
    assert job["mode"] == "video_dub"  # no AVATAR_ENGINE=musetalk configured → mux fallback
    assert job["file"].endswith(".mp4")
    assert job["url"]


def test_dub_rejects_bad_extension(client, auth_headers):
    r = client.post(
        "/api/dub/generate",
        data={"target_language": "French", "voice": "studio"},
        files={"source": ("evil.exe", io.BytesIO(b"MZ"), "application/x-msdownload")},
        headers=auth_headers,
    )
    assert r.status_code == 400


def test_api_key_lifecycle(client, auth_headers):
    """API keys let programmatic/bulk clients call authenticated endpoints
    without a browser session — the missing piece for catalog-scale dubbing."""
    r = client.post("/api/keys", json={"name": "bulk-dub-worker"}, headers=auth_headers)
    assert r.status_code == 200, r.text
    created = r.json()
    plaintext_key = created["key"]
    assert plaintext_key.startswith("ak_live_")
    assert created["prefix"] in plaintext_key

    key_headers = {"Authorization": f"Bearer {plaintext_key}"}

    # the key authenticates exactly like a JWT bearer token, no extra plumbing
    me = client.get("/api/auth/me", headers=key_headers)
    assert me.status_code == 200
    assert me.json()["email"] == "creator@example.com"

    langs = client.get("/api/dub/languages", headers=key_headers)
    assert langs.status_code == 200

    listed = client.get("/api/keys", headers=auth_headers).json()
    match = next(k for k in listed if k["id"] == created["id"])
    assert match["revoked_at"] is None
    assert "key" not in match and "key_hash" not in match  # plaintext/hash never re-exposed

    revoke = client.delete(f"/api/keys/{created['id']}", headers=auth_headers)
    assert revoke.status_code == 200

    # a revoked key stops authenticating immediately
    after_revoke = client.get("/api/auth/me", headers=key_headers)
    assert after_revoke.status_code == 401

    # revoking the same key twice is a clean 404, not a crash
    again = client.delete(f"/api/keys/{created['id']}", headers=auth_headers)
    assert again.status_code == 404


def test_api_key_garbage_rejected(client):
    r = client.get("/api/auth/me", headers={"Authorization": "Bearer ak_live_not_a_real_key"})
    assert r.status_code == 401
