"""Autenticación por API Key."""

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.config import settings

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(
    api_key: str | None = Security(API_KEY_HEADER),
) -> str:
    """
    Valida que el header X-API-Key contenga una clave válida.
    Retorna la clave usada (útil para logging/auditoría).
    """
    if not settings.api_keys:
        # Si no hay claves configuradas, permitir acceso libre (dev mode)
        return "dev-no-auth"

    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Falta el header X-API-Key",
        )

    if api_key not in settings.api_keys:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key inválida",
        )

    return api_key
