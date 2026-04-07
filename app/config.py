"""Configuración cargada desde .env"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ollama_base_url: str = "https://ollama.com"
    ollama_model: str = "qwen3.5:cloud"
    ollama_api_key: str = "42f62d7ad6e04c8db2dec179ca37b6d6.N8S8UE_HUoWn95exkc2aCnIb"
    ollama_timeout: int = 600
    ollama_temperature: float = 0.1
    ollama_num_ctx: int = 8192

    # Batch / Paralelismo
    batch_max_items: int = 50          # Máximo de contratos por request batch
    batch_max_parallel: int = 3        # Requests simultáneos a Ollama
    preprocess_max_chars: int = 10000  # Truncar texto a N caracteres

    # Auth – lista de API Keys separadas por coma (vacío = sin auth / dev mode)
    api_keys_raw: str = ""

    @property
    def api_keys(self) -> set[str]:
        """Devuelve el set de API Keys válidas."""
        if not self.api_keys_raw.strip():
            return set()
        return {k.strip() for k in self.api_keys_raw.split(",") if k.strip()}

    class Config:
        env_file = ".env"


settings = Settings()
