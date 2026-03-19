"""Cliente async para Ollama con structured outputs."""

import json
from typing import Any

import httpx

from app.config import settings


async def ollama_health() -> bool:
    """Verifica si Ollama está corriendo."""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"{settings.ollama_base_url}/api/version")
            return r.status_code == 200
    except httpx.ConnectError:
        return False


async def ollama_models() -> list[dict[str, Any]]:
    """Lista modelos instalados."""
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(f"{settings.ollama_base_url}/api/tags")
        r.raise_for_status()
        return r.json().get("models", [])


async def ollama_chat(
    *,
    model: str,
    system: str,
    user_msg: str,
    schema: dict[str, Any],
    temperature: float,
) -> dict[str, Any]:
    """
    Envía un chat a Ollama con structured output (JSON Schema).
    Retorna el JSON parseado de la respuesta.
    """
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user_msg},
        ],
        "stream": False,
        "format": schema,
        "options": {
            "temperature": temperature,
            "num_ctx": settings.ollama_num_ctx,
        },
        "think": False,  # Desactiva thinking mode para extracción directa
    }

    async with httpx.AsyncClient(timeout=settings.ollama_timeout) as client:
        r = await client.post(
            f"{settings.ollama_base_url}/api/chat",
            json=payload,
        )
        r.raise_for_status()

    result = r.json()
    content = result.get("message", {}).get("content", "")

    if not content:
        raise ValueError(f"Ollama devolvió respuesta vacía. done={result.get('done')}, done_reason={result.get('done_reason')}")

    parsed = json.loads(content) if isinstance(content, str) else content

    return {
        "data": parsed,
        "duration_ms": result.get("total_duration", 0) / 1e6,
        "tokens": result.get("eval_count", 0),
    }
