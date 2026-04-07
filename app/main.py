"""MVP Backend – Extracción de datos contractuales con Ollama."""

from fastapi import FastAPI, File, Form, HTTPException, Depends, UploadFile

from app.auth import verify_api_key
from app.cache import cache
from app.config import settings
from app.extractor import extract_document
from app.ollama_client import ollama_health, ollama_models
from app.schemas import DocumentRequest, DocumentResponse

app = FastAPI(
    title="IaOCR – Extracción de Contratos",
    description=(
        "Backend con IA (Ollama local o cloud) para extraer datos de contratos colombianos.\n\n"
        "**Concepto:** Cada documento OCR = UN solo contrato. El sistema filtra ruido \n"
        "(hojas de vida, experiencia, cuotas mensuales) y extrae los 9 campos del contrato principal.\n\n"
        "**Autenticación:** Envía el header `X-API-Key` con tu clave.\n\n"
        "**Endpoints:**\n"
        "- `POST /api/v1/extract` — **Subir archivo .txt** con el OCR del contrato\n"
        "- `GET /health` — Estado del sistema\n"
        "- `GET /cache/stats` — Estadísticas del cache"
    ),
    version="5.0.0",
)


# ─── Health (público) ───

@app.get("/health", tags=["Sistema"])
async def health():
    """Estado del sistema y conexión con Ollama."""
    alive = await ollama_health()
    models = []
    if alive:
        try:
            raw = await ollama_models()
            models = [m["name"] for m in raw]
        except Exception:
            pass

    auth_mode = "api_key" if settings.api_keys else "none (dev mode)"

    return {
        "status": "ok" if alive else "ollama_offline",
        "ollama_url": settings.ollama_base_url,
        "ollama_cloud_api": settings.ollama_base_url.rstrip("/").startswith("https://ollama.com"),
        "default_model": settings.ollama_model,
        "models": models,
        "auth_mode": auth_mode,
        "batch_config": {
            "max_items": settings.batch_max_items,
            "max_parallel": settings.batch_max_parallel,
            "preprocess_max_chars": settings.preprocess_max_chars,
        },
    }


# ─── Cache (público) ───

@app.get("/cache/stats", tags=["Sistema"])
async def cache_stats():
    """Estadísticas del cache de extracción."""
    return cache.stats()


@app.delete("/cache", tags=["Sistema"])
async def cache_clear(api_key: str = Depends(verify_api_key)):
    """Vacía el cache de extracción. Requiere API Key."""
    cache.clear()
    return {"message": "Cache vaciado"}


# ─── API v1: Extracción desde archivo .txt ───

@app.post(
    "/api/v1/extract",
    response_model=DocumentResponse,
    tags=["Extracción"],
    summary="Subir archivo .txt y extraer datos del contrato",
    description=(
        "Sube un **archivo de texto** (.txt) con el OCR completo del documento.\n\n"
        "El sistema automáticamente:\n"
        "1. **Filtra ruido** (hojas de vida, experiencia laboral, cuotas mensuales)\n"
        "2. **Extrae secciones prioritarias** (contrato, estudios previos, acta de inicio, SECOP, CDP)\n"
        "3. **Extrae los 9 campos** del contrato principal con IA (Ollama)\n\n"
        "**9 campos:** numero_contrato, objeto_contractual, nombre_contratista, vigencia, "
        "anio_contrato, fecha_inicial, valor, tipo_persona, tipo_contrato\n\n"
        "**En Postman:** Body → form-data → Key: `file` (tipo File) → seleccionar el .txt"
    ),
)
async def extract(
    file: UploadFile = File(..., description="Archivo .txt con el texto OCR del documento"),
    fields: str | None = Form(default=None, description="Campos a extraer separados por coma (opcional). Ej: numero_contrato,valor,nombre_contratista"),
    model: str | None = Form(default=None, description="Modelo Ollama a usar (opcional, usa el default de .env)"),
    api_key: str = Depends(verify_api_key),
):
    alive = await ollama_health()
    if not alive:
        raise HTTPException(
            503,
            "No se pudo conectar con Ollama. Verifica OLLAMA_BASE_URL y, si usas cloud, define OLLAMA_API_KEY.",
        )

    # Validar extensión
    if file.filename and not file.filename.lower().endswith(".txt"):
        raise HTTPException(400, "Solo se aceptan archivos .txt")

    # Leer contenido
    try:
        content = await file.read()
        try:
            raw_text = content.decode("utf-8")
        except UnicodeDecodeError:
            raw_text = content.decode("latin-1")
    except Exception as e:
        raise HTTPException(400, f"Error leyendo el archivo: {e}")

    if len(raw_text) < 50:
        raise HTTPException(400, "El archivo es demasiado corto (mínimo 50 caracteres)")
    if len(raw_text) > 2_000_000:
        raise HTTPException(400, f"El archivo es demasiado grande ({len(raw_text):,} chars, máximo 2,000,000)")

    # Parsear campos opcionales
    fields_list = None
    if fields:
        fields_list = [f.strip() for f in fields.split(",") if f.strip()]

    req = DocumentRequest(
        raw_text=raw_text,
        fields=fields_list,
        model=model,
    )
    return await extract_document(req)


