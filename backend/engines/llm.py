"""LLM backend — Ollama (local) or Grok/xAI (cloud).

Both implement the same interface: chat(), complete(), chat_stream().
Voice, TTS, transcription, and avatar engines always run locally.
Only text prompts and replies cross the wire when using Grok.

Set LLM_PROVIDER=grok + GROK_API_KEY in .env to enable Grok.
Default is LLM_PROVIDER=ollama (fully offline).
"""
import json
import httpx

from core.config import (
    LLM_PROVIDER,
    OLLAMA_URL, OLLAMA_MODEL,
    GROK_API_KEY, GROK_MODEL, GROK_BASE_URL,
    logger,
)

_OLLAMA_HINT = (
    f"Local LLM unreachable at {OLLAMA_URL}. Install Ollama (https://ollama.com) "
    f"and run: ollama pull {OLLAMA_MODEL}"
)
_GROK_HINT = "GROK_API_KEY is not set. Add it to your .env file."


# ── Ollama (local) ─────────────────────────────────────────────────────────


async def _ollama_is_available() -> bool:
    try:
        async with httpx.AsyncClient(timeout=2) as client:
            r = await client.get(f"{OLLAMA_URL}/api/tags")
            return r.status_code == 200
    except Exception:
        return False


async def _ollama_chat(system: str, messages: list[dict], temperature: float) -> str:
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
        raise RuntimeError(_OLLAMA_HINT)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise RuntimeError(f"Model '{OLLAMA_MODEL}' not pulled. Run: ollama pull {OLLAMA_MODEL}")
        raise RuntimeError(f"Ollama error: {e}")


async def _ollama_chat_stream(system: str, messages: list[dict], temperature: float):
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
        raise RuntimeError(_OLLAMA_HINT)


# ── Grok / xAI (OpenAI-compatible) ────────────────────────────────────────


async def _grok_chat(system: str, messages: list[dict], temperature: float) -> str:
    if not GROK_API_KEY:
        raise RuntimeError(_GROK_HINT)
    payload = {
        "model": GROK_MODEL,
        "messages": [{"role": "system", "content": system}, *messages],
        "temperature": temperature,
        "stream": False,
    }
    headers = {
        "Authorization": f"Bearer {GROK_API_KEY}",
        "Content-Type": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(f"{GROK_BASE_URL}/chat/completions", json=payload, headers=headers)
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"].strip()
    except httpx.ConnectError:
        raise RuntimeError("Cannot reach api.x.ai — check your network connection.")
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            raise RuntimeError("Grok API key rejected (401). Check GROK_API_KEY in .env.")
        raise RuntimeError(f"Grok API error {e.response.status_code}: {e.response.text[:200]}")


async def _grok_chat_stream(system: str, messages: list[dict], temperature: float):
    if not GROK_API_KEY:
        raise RuntimeError(_GROK_HINT)
    payload = {
        "model": GROK_MODEL,
        "messages": [{"role": "system", "content": system}, *messages],
        "temperature": temperature,
        "stream": True,
    }
    headers = {
        "Authorization": f"Bearer {GROK_API_KEY}",
        "Content-Type": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            async with client.stream(
                "POST", f"{GROK_BASE_URL}/chat/completions",
                json=payload, headers=headers,
            ) as r:
                if r.status_code == 401:
                    raise RuntimeError("Grok API key rejected (401). Check GROK_API_KEY in .env.")
                r.raise_for_status()
                async for line in r.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    chunk = line[6:]
                    if chunk.strip() == "[DONE]":
                        return
                    try:
                        data = json.loads(chunk)
                        token = data["choices"][0].get("delta", {}).get("content", "")
                        if token:
                            yield token
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue
    except httpx.ConnectError:
        raise RuntimeError("Cannot reach api.x.ai — check your network connection.")


# ── Public interface (dispatches by LLM_PROVIDER) ─────────────────────────


async def is_available() -> bool:
    if LLM_PROVIDER == "grok":
        return bool(GROK_API_KEY)
    return await _ollama_is_available()


async def status() -> dict:
    if LLM_PROVIDER == "grok":
        return {
            "engine": "grok",
            "provider": "xAI",
            "model": GROK_MODEL,
            "running": bool(GROK_API_KEY),
            "key_set": bool(GROK_API_KEY),
        }
    up = await _ollama_is_available()
    return {"engine": "ollama", "url": OLLAMA_URL, "model": OLLAMA_MODEL, "running": up}


async def chat(system: str, messages: list[dict], temperature: float = 0.7) -> str:
    """Generate a reply. Dispatches to Ollama or Grok based on LLM_PROVIDER."""
    if LLM_PROVIDER == "grok":
        return await _grok_chat(system, messages, temperature)
    return await _ollama_chat(system, messages, temperature)


async def complete(system: str, prompt: str, temperature: float = 0.7) -> str:
    return await chat(system, [{"role": "user", "content": prompt}], temperature)


async def chat_stream(system: str, messages: list[dict], temperature: float = 0.7):
    """Async generator yielding tokens. Dispatches to Ollama or Grok."""
    if LLM_PROVIDER == "grok":
        async for token in _grok_chat_stream(system, messages, temperature):
            yield token
    else:
        async for token in _ollama_chat_stream(system, messages, temperature):
            yield token
