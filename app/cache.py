"""Cache en memoria para resultados de extracción."""

import asyncio
import hashlib
import time
from typing import Any


class ExtractionCache:
    """
    Cache LRU en memoria con TTL y locks por clave.
    Usa SHA256 del texto como clave para evitar reprocesar contratos idénticos.
    Cuando múltiples requests paralelos piden el mismo texto, solo el primero
    llama a Ollama; los demás esperan el resultado del cache.
    """

    def __init__(self, max_size: int = 500, ttl_seconds: int = 3600):
        self._cache: dict[str, dict[str, Any]] = {}
        self._access_order: list[str] = []
        self._locks: dict[str, asyncio.Lock] = {}
        self._max_size = max_size
        self._ttl = ttl_seconds
        self.hits = 0
        self.misses = 0

    @staticmethod
    def hash_text(text: str) -> str:
        """Genera hash SHA256 del texto."""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def get_lock(self, key: str) -> asyncio.Lock:
        """Obtiene (o crea) un lock para una clave específica."""
        if key not in self._locks:
            self._locks[key] = asyncio.Lock()
        return self._locks[key]

    def get(self, text: str) -> dict[str, Any] | None:
        """Busca en cache. Retorna None si no existe o expiró."""
        key = self.hash_text(text)
        entry = self._cache.get(key)

        if entry is None:
            self.misses += 1
            return None

        # Verificar TTL
        if time.time() - entry["timestamp"] > self._ttl:
            del self._cache[key]
            if key in self._access_order:
                self._access_order.remove(key)
            self.misses += 1
            return None

        # Mover al final (más reciente)
        if key in self._access_order:
            self._access_order.remove(key)
        self._access_order.append(key)
        self.hits += 1
        return entry["data"]

    def put(self, text: str, data: dict[str, Any]) -> None:
        """Guarda resultado en cache."""
        key = self.hash_text(text)

        # Si ya existe, actualizar
        if key in self._cache:
            if key in self._access_order:
                self._access_order.remove(key)
        elif len(self._cache) >= self._max_size:
            # Evictar el más antiguo
            oldest = self._access_order.pop(0)
            del self._cache[oldest]
            self._locks.pop(oldest, None)

        self._cache[key] = {
            "data": data,
            "timestamp": time.time(),
        }
        self._access_order.append(key)

    def stats(self) -> dict[str, Any]:
        """Estadísticas del cache."""
        total = self.hits + self.misses
        return {
            "size": len(self._cache),
            "max_size": self._max_size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": f"{(self.hits / total * 100):.1f}%" if total > 0 else "0%",
            "ttl_seconds": self._ttl,
        }

    def clear(self) -> None:
        """Vacía el cache."""
        self._cache.clear()
        self._access_order.clear()
        self._locks.clear()
        self.hits = 0
        self.misses = 0


# Instancia global
cache = ExtractionCache(max_size=500, ttl_seconds=3600)
