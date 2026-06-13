"""AI helper router: scripts, translation, voice agent — local LLM only."""
import base64
import json
from typing import Optional
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from core.config import logger
from core.db import get_db
from core.security import CurrentUser, save_project, now_iso
from engines import llm, tts

router = APIRouter(tags=["ai"])


class TranslateRequest(BaseModel):
    text: str = Field(min_length=1, max_length=8000)
    target_language: str
    preserve_tone: bool = True


class ScriptRequest(BaseModel):
    topic: str = Field(min_length=1, max_length=500)
    style: str = "professional"
    length: str = "short"


class AgentChatRequest(BaseModel):
    session_id: str
    message: str = Field(min_length=1, max_length=4000)
    voice: Optional[str] = None


@router.post("/ai/translate")
async def ai_translate(req: TranslateRequest, user: CurrentUser):
    sys_msg = (
        "You are an expert translator. Translate the given text faithfully into the target "
        "language, preserving tone, register, idiomatic flavor, and intent. "
        "Output ONLY the translated text, no commentary."
    )
    prompt = (f"Target language: {req.target_language}\n"
              f"Preserve tone: {req.preserve_tone}\n\nText:\n{req.text}")
    try:
        translated = await llm.complete(sys_msg, prompt, temperature=0.3)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    project = await save_project(user["id"], "translation", req.text[:60],
                                 {"source": req.text, "target_language": req.target_language,
                                  "translated": translated})
    return {"translated": translated, "project": project}


@router.post("/ai/script")
async def ai_script(req: ScriptRequest, user: CurrentUser):
    length_map = {
        "short": "30-60 seconds (about 80 words)",
        "medium": "1-2 minutes (about 200 words)",
        "long": "3-5 minutes (about 500 words)",
    }
    sys_msg = (
        "You are a top-tier scriptwriter for AI video creators. Output a clean spoken-word "
        "script. Use a vivid hook in the first sentence, end on a strong CTA. "
        "No stage directions, no headings — pure narration."
    )
    prompt = (f"Topic: {req.topic}\nStyle: {req.style}\n"
              f"Target length: {length_map.get(req.length, length_map['short'])}")
    try:
        text = await llm.complete(sys_msg, prompt)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    project = await save_project(user["id"], "script", req.topic[:60],
                                 {"topic": req.topic, "style": req.style,
                                  "length": req.length, "script": text})
    return {"script": text, "project": project}


@router.post("/agent/chat")
async def agent_chat(req: AgentChatRequest, user: CurrentUser):
    db = await get_db()
    await db.execute(
        "INSERT INTO agent_messages (session_id, user_id, role, text, ts) VALUES (?,?,?,?,?)",
        (req.session_id, user["id"], "user", req.message, now_iso()),
    )
    await db.commit()

    cur = await db.execute(
        "SELECT role, text FROM agent_messages WHERE session_id = ? AND user_id = ? "
        "ORDER BY id DESC LIMIT 20", (req.session_id, user["id"]),
    )
    history = [{"role": r["role"], "content": r["text"]} for r in reversed(await cur.fetchall())]

    sys_msg = (
        "You are ArcVox Agent — a witty, sharp, helpful voice agent running fully on the "
        "user's own hardware. Keep replies natural and conversational, 2-4 sentences. "
        "Be specific and warm. Avoid robotic phrasing."
    )
    try:
        reply = await llm.chat(sys_msg, history)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    await db.execute(
        "INSERT INTO agent_messages (session_id, user_id, role, text, ts) VALUES (?,?,?,?,?)",
        (req.session_id, user["id"], "assistant", reply, now_iso()),
    )
    await db.commit()

    audio_b64 = None
    if req.voice:
        try:
            audio = await tts.synthesize(reply, voice=req.voice)
            audio_b64 = base64.b64encode(audio).decode()
        except Exception:
            logger.warning("Agent TTS failed; returning text only")
    return {"reply": reply, "audio_base64": audio_b64}


@router.post("/agent/chat/stream")
async def agent_chat_stream(req: AgentChatRequest, user: CurrentUser):
    """SSE: streams LLM tokens as they arrive so text appears word-by-word.

    Events: data:{"token":"…"} per token, data:{"done":true,"text":"full reply"} at end.
    The caller should follow up with /voice/tts/stream for audio if needed.
    """
    db = await get_db()
    await db.execute(
        "INSERT INTO agent_messages (session_id, user_id, role, text, ts) VALUES (?,?,?,?,?)",
        (req.session_id, user["id"], "user", req.message, now_iso()),
    )
    await db.commit()

    cur = await db.execute(
        "SELECT role, text FROM agent_messages WHERE session_id = ? AND user_id = ? "
        "ORDER BY id DESC LIMIT 20", (req.session_id, user["id"]),
    )
    history = [{"role": r["role"], "content": r["text"]} for r in reversed(await cur.fetchall())]

    sys_msg = (
        "You are ArcVox Agent — a witty, sharp, helpful voice agent running fully on the "
        "user's own hardware. Keep replies natural and conversational, 2-4 sentences. "
        "Be specific and warm. Avoid robotic phrasing."
    )

    async def event_gen():
        tokens: list[str] = []
        try:
            async for token in llm.chat_stream(sys_msg, history):
                tokens.append(token)
                yield f"data: {json.dumps({'token': token})}\n\n"
            full_reply = "".join(tokens).strip()
            db2 = await get_db()
            await db2.execute(
                "INSERT INTO agent_messages (session_id, user_id, role, text, ts) VALUES (?,?,?,?,?)",
                (req.session_id, user["id"], "assistant", full_reply, now_iso()),
            )
            await db2.commit()
            yield f"data: {json.dumps({'done': True, 'text': full_reply})}\n\n"
        except RuntimeError as e:
            yield f"data: {json.dumps({'error': str(e), 'done': True})}\n\n"
        except Exception as e:
            logger.exception("Agent stream error")
            yield f"data: {json.dumps({'error': f'Agent error: {e}', 'done': True})}\n\n"

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/agent/session/{session_id}")
async def agent_session(session_id: str, user: CurrentUser):
    db = await get_db()
    cur = await db.execute(
        "SELECT role, text, ts FROM agent_messages WHERE session_id = ? AND user_id = ? ORDER BY id",
        (session_id, user["id"]),
    )
    messages = [dict(r) for r in await cur.fetchall()]
    return {"id": session_id, "messages": messages}
