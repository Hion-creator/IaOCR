"""Cliente async para Ollama con structured outputs."""

import json
from typing import Any

import httpx
from ollama import AsyncClient

from app.config import settings


def _build_headers() -> dict[str, str]:
    """Headers requeridos para Ollama Cloud API."""
    base_url = settings.ollama_base_url.rstrip("/").lower()
    uses_cloud_api = base_url.startswith("https://ollama.com") or base_url.startswith("http://ollama.com")

    if not uses_cloud_api:
        return {}

    api_key = settings.ollama_api_key.strip()
    if not api_key:
        raise ValueError("OLLAMA_API_KEY es obligatorio cuando OLLAMA_BASE_URL apunta a https://ollama.com")

    return {"Authorization": f"Bearer {api_key}"}


async def ollama_health() -> bool:
    """Verifica si Ollama está corriendo."""
    try:
        headers = _build_headers()
        async with httpx.AsyncClient(timeout=5, headers=headers or None) as client:
            r = await client.get(f"{settings.ollama_base_url}/api/tags")
            return r.status_code == 200
    except Exception:
        return False


async def ollama_models() -> list[dict[str, Any]]:
    """Lista modelos instalados."""
    headers = _build_headers()
    async with httpx.AsyncClient(timeout=10, headers=headers or None) as client:
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
    headers = _build_headers()
    client = AsyncClient(
        host=settings.ollama_base_url,
        headers=headers or None,
        timeout=settings.ollama_timeout,
    )

    result = await client.chat(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_msg},
        ],
        stream=False,
        format=schema,
        options={
            "temperature": temperature,
            "num_ctx": settings.ollama_num_ctx,
        },
        think=False,
    )

    content = ""
    if getattr(result, "message", None) is not None:
        content = getattr(result.message, "content", "") or ""

    result_dict = result.model_dump() if hasattr(result, "model_dump") else dict(result)
    if not content:
        message = result_dict.get("message", {})
        if isinstance(message, dict):
            content = message.get("content", "")

    if not content:
        raise ValueError(
            f"Ollama devolvió respuesta vacía. done={result_dict.get('done')}, "
            f"done_reason={result_dict.get('done_reason')}"
        )

    parsed = json.loads(content) if isinstance(content, str) else content
    total_duration = getattr(result, "total_duration", result_dict.get("total_duration", 0)) or 0
    eval_count = getattr(result, "eval_count", result_dict.get("eval_count", 0)) or 0

    return {
        "data": parsed,
        "duration_ms": total_duration / 1e6,
        "tokens": eval_count,
    }
