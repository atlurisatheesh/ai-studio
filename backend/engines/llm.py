"""Local LLM via Ollama — scripts, translation, agent chat.

Ollama runs on the same machine (or the operator's own LAN/server).
No prompt or output ever reaches a third-party API.
"""
import json
import httpx

from core.config import OLLAMA_URL, OLLAMA_MODEL

NOT_RUNNING_HINT = (
    f"Local LLM unreachable at {OLLAMA_URL}. Install Ollama (https://ollama.com) "
    f"and run: ollama pull {OLLAMA_MODEL}"
)


async def is_available() -> bool:
    try:
        async with httpx.AsyncClient(timeout=2) as client:
            r = await client.get(f"{OLLAMA_URL}/api/tags")
            return r.status_code == 200
    except Exception:
        return False


async def status() -> dict:
    up = await is_available()
    return {"engine": "ollama", "url": OLLAMA_URL, "model": OLLAMA_MODEL, "running": up}


async def chat(system: str, messages: list[dict], temperature: float = 0.7) -> str:
    """messages: [{"role": "user"|"assistant", "content": str}, ...]"""
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [{"role": "system", "content": system}, *messages],
        "stream": False,
        "options": {"temperature": temperature},
    }
    try:
        async with httpx.AsyncClient(timeout=300) as client:
            r = await client.post(f"{OLLAMA_URL}/api/chat", json=payload)
            r.raise_for_status()
            return r.json()["message"]["content"].strip()
    except httpx.ConnectError:
        raise RuntimeError(NOT_RUNNING_HINT)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise RuntimeError(f"Model '{OLLAMA_MODEL}' not pulled. Run: ollama pull {OLLAMA_MODEL}")
        raise RuntimeError(f"Local LLM error: {e}")


async def complete(system: str, prompt: str, temperature: float = 0.7) -> str:
    return await chat(system, [{"role": "user", "content": prompt}], temperature)


async def chat_stream(system: str, messages: list[dict], temperature: float = 0.7):
    """Async generator yielding text tokens as Ollama produces them.

    Each yielded value is a string fragment (one or more chars). Callers
    can display tokens live and trigger TTS on sentence boundaries without
    waiting for the full reply.
    """
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [{"role": "system", "content": system}, *messages],
        "stream": True,
        "options": {"temperature": temperature},
    }
    try:
        async with httpx.AsyncClient(timeout=300) as client:
            async with client.stream("POST", f"{OLLAMA_URL}/api/chat", json=payload) as r:
                if r.status_code == 404:
                    raise RuntimeError(f"Model '{OLLAMA_MODEL}' not pulled. Run: ollama pull {OLLAMA_MODEL}")
                r.raise_for_status()
                async for line in r.aiter_lines():
                    if not line:
                        continue
                    data = json.loads(line)
                    token = data.get("message", {}).get("content", "")
                    if token:
                        yield token
                    if data.get("done"):
                        return
    except httpx.ConnectError:
        raise RuntimeError(NOT_RUNNING_HINT)
