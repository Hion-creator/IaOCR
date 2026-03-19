"""Lógica de extracción de datos contractuales."""

import time

from app.cache import cache
from app.config import settings
from app.ollama_client import ollama_chat
from app.preprocessor import preprocess, prepare_single_contract
from app.schemas import (
    CONTRACT_SCHEMA,
    ContractData,
    VALID_FIELDS,
    DocumentRequest,
    DocumentResponse,
)

SYSTEM_PROMPT = """/no_think
Eres un extractor de datos de contratos colombianos. Tu ÚNICA tarea es leer el texto de UN SOLO contrato y extraer los 9 campos requeridos.

IMPORTANTE: El texto puede contener menciones a otros contratos (experiencia laboral, hojas de vida, certificaciones de trabajos anteriores). IGNÓRALOS. Solo extrae la información del CONTRATO PRINCIPAL que se está formalizando.

PRIORIZA la información de estas secciones (en orden de importancia):
1. Cuerpo del contrato (cláusulas, minuta)
2. Condiciones adicionales
3. Acta de Inicio
4. Estudios Previos
5. Datos SECOP

CAMPOS A EXTRAER (TODOS son obligatorios si la información está en el texto):

1. numero_contrato → número o código del contrato principal. Ej: "2024-0456", "LP-001-2024", "0006-2019". Puede aparecer como código TRD (ej: "1.220.02-59.2-0006-2019" → extraer "0006-2019") o como número SECOP.
2. objeto_contractual → copiar TEXTUALMENTE la descripción del objeto del contrato
3. nombre_contratista → nombre completo o razón social del contratista (quien presta el servicio, NO la entidad contratante)
4. vigencia → plazo o periodo de ejecución del contrato TAL COMO aparece en el texto. Puede ser duración ("6 meses", "12 meses"), fecha límite ("31 de diciembre de 2024"), o año fiscal ("2024"). Copiar textualmente lo que diga el texto.
5. anio_contrato → año de vigencia como número entero. Ej: 2024
6. fecha_inicial → fecha de inicio en formato YYYY-MM-DD. Buscar en el Acta de Inicio o en la fecha de firma del contrato. Ej: "2024-02-15"
7. valor → valor numérico SIN formato. Ej: 35000000 (NO "$35.000.000"). Usar el valor total del contrato.
8. tipo_persona → "Natural" si tiene cédula de ciudadanía (CC). "Jurídica" si tiene NIT o es empresa (S.A.S, LTDA, S.A.)
9. tipo_contrato → clasificar: "Prestación de servicios", "Obra", "Suministro", "Consultoría", "Compraventa", "Arrendamiento", "Interadministrativo", "Convenio" o "Otro"

REGLAS:
- Si un dato está en el texto, DEBES extraerlo. NUNCA dejes null un campo cuya información aparece en el texto.
- Solo usa null si el dato realmente NO existe en el texto.
- No inventes datos que no estén en el texto.
- IGNORA contratos mencionados en experiencia laboral u hoja de vida.
- Responde SOLO con el JSON, sin explicaciones."""

USER_TEMPLATE = """Lee este contrato y extrae TODOS los 9 campos:

---
{text}
---

Extrae: numero_contrato, objeto_contractual, nombre_contratista, vigencia, anio_contrato, fecha_inicial, valor, tipo_persona, tipo_contrato."""


def _filter_fields(data: ContractData, fields: list[str] | None) -> ContractData | dict:
    """Filtra los campos del resultado si se especificaron."""
    if fields is None:
        return data
    return {f: getattr(data, f) for f in fields if f in VALID_FIELDS}


async def _extract_single(
    raw_text: str,
    model: str,
    temperature: float,
) -> dict:
    """
    Extrae datos de un texto de contrato individual.
    Usa cache con locks y preprocessor internamente.
    Si otro request paralelo ya está procesando el mismo texto, espera el resultado.
    Retorna dict con {data: ContractData, tokens: int, cached: bool}.
    """
    # Pre-procesar texto OCR
    cleaned = preprocess(raw_text, max_chars=settings.preprocess_max_chars)

    # Obtener lock para este texto específico
    key = cache.hash_text(cleaned)
    lock = cache.get_lock(key)

    async with lock:
        # Buscar en cache (puede haber sido guardado por otro request paralelo)
        cached_data = cache.get(cleaned)
        if cached_data is not None:
            return {"data": ContractData(**cached_data), "tokens": 0, "cached": True}

        # Llamar a Ollama
        result = await ollama_chat(
            model=model,
            system=SYSTEM_PROMPT,
            user_msg=USER_TEMPLATE.format(text=cleaned),
            schema=CONTRACT_SCHEMA,
            temperature=temperature,
        )

        data = ContractData(**result["data"])

        # Guardar en cache
        cache.put(cleaned, result["data"])

        return {"data": data, "tokens": result.get("tokens", 0), "cached": False}


# ─── Documento completo → UN solo contrato ───

async def extract_document(request: DocumentRequest) -> DocumentResponse:
    """
    Recibe un documento OCR completo de UN contrato.
    Extrae las secciones prioritarias, descarta ruido (CV, experiencia, cuotas)
    y retorna UN solo JSON con los 9 campos.
    """
    model = request.model or settings.ollama_model
    temp = request.temperature if request.temperature is not None else settings.ollama_temperature

    # Validar campos si se enviaron
    if request.fields:
        invalid = [f for f in request.fields if f not in VALID_FIELDS]
        if invalid:
            return DocumentResponse(
                success=False,
                model_used=model,
                total_chars=len(request.raw_text),
                processing_time_ms=0,
                error=f"Campos inválidos: {invalid}. Válidos: {sorted(VALID_FIELDS)}",
            )

    start = time.perf_counter()

    try:
        # Preparar texto: limpiar, filtrar ruido, extraer secciones prioritarias
        prepared = prepare_single_contract(
            request.raw_text,
            max_chars=settings.preprocess_max_chars,
        )

        # Extraer datos con Ollama (1 sola llamada)
        result = await _extract_single(prepared, model, temp)
        elapsed = (time.perf_counter() - start) * 1000
        filtered = _filter_fields(result["data"], request.fields)

        return DocumentResponse(
            success=True,
            data=filtered,
            model_used=model,
            total_chars=len(request.raw_text),
            prepared_chars=len(prepared),
            processing_time_ms=round(elapsed, 2),
            cached=result["cached"],
        )

    except Exception as e:
        elapsed = (time.perf_counter() - start) * 1000
        error_msg = f"{type(e).__name__}: {e}" if str(e) else type(e).__name__
        return DocumentResponse(
            success=False,
            model_used=model,
            total_chars=len(request.raw_text),
            processing_time_ms=round(elapsed, 2),
            error=error_msg,
        )
