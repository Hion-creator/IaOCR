"""Schemas de request/response y JSON Schema para Ollama Structured Outputs."""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ─── Enums ───

class TipoPersona(str, Enum):
    NATURAL = "Natural"
    JURIDICA = "Jurídica"


class TipoContrato(str, Enum):
    PRESTACION_SERVICIOS = "Prestación de servicios"
    OBRA = "Obra"
    SUMINISTRO = "Suministro"
    CONSULTORIA = "Consultoría"
    COMPRAVENTA = "Compraventa"
    ARRENDAMIENTO = "Arrendamiento"
    INTERADMINISTRATIVO = "Interadministrativo"
    CONVENIO = "Convenio"
    OTRO = "Otro"


# ─── Campos válidos para filtrado ───

VALID_FIELDS = {
    "numero_contrato",
    "objeto_contractual",
    "nombre_contratista",
    "vigencia",
    "anio_contrato",
    "fecha_inicial",
    "valor",
    "tipo_persona",
    "tipo_contrato",
}


# ─── Response ───

class ContractData(BaseModel):
    """Datos extraídos del contrato."""
    numero_contrato: Optional[str] = None
    objeto_contractual: Optional[str] = None
    nombre_contratista: Optional[str] = None
    vigencia: Optional[str] = None
    anio_contrato: Optional[int] = None
    fecha_inicial: Optional[str] = None
    valor: Optional[float] = None
    tipo_persona: Optional[TipoPersona] = None
    tipo_contrato: Optional[TipoContrato] = None


# ─── JSON Schema que Ollama usará para forzar el formato de respuesta ───

CONTRACT_SCHEMA = {
    "type": "object",
    "properties": {
        "numero_contrato": {
            "description": "Número o código del contrato, ej: 2024-0456, LP-001-2024",
            "anyOf": [{"type": "string"}, {"type": "null"}],
        },
        "objeto_contractual": {
            "description": "Descripción completa del objeto del contrato",
            "anyOf": [{"type": "string"}, {"type": "null"}],
        },
        "nombre_contratista": {
            "description": "Nombre completo de la persona o razón social de la empresa contratista",
            "anyOf": [{"type": "string"}, {"type": "null"}],
        },
        "vigencia": {
            "description": "Plazo o duración del contrato, ej: 6 meses, 1 año, 90 días",
            "anyOf": [{"type": "string"}, {"type": "null"}],
        },
        "anio_contrato": {
            "description": "Año de la vigencia del contrato como número entero, ej: 2024",
            "anyOf": [{"type": "integer"}, {"type": "null"}],
        },
        "fecha_inicial": {
            "description": "Fecha de inicio del contrato en formato YYYY-MM-DD",
            "anyOf": [{"type": "string"}, {"type": "null"}],
        },
        "valor": {
            "description": "Valor total del contrato como número sin formato, ej: 35000000",
            "anyOf": [{"type": "number"}, {"type": "null"}],
        },
        "tipo_persona": {
            "description": "Tipo de persona del contratista",
            "anyOf": [
                {"type": "string", "enum": ["Natural", "Jurídica"]},
                {"type": "null"},
            ],
        },
        "tipo_contrato": {
            "description": "Clasificación del tipo de contrato",
            "anyOf": [
                {
                    "type": "string",
                    "enum": [
                        "Prestación de servicios",
                        "Obra",
                        "Suministro",
                        "Consultoría",
                        "Compraventa",
                        "Arrendamiento",
                        "Interadministrativo",
                        "Convenio",
                        "Otro",
                    ],
                },
                {"type": "null"},
            ],
        },
    },
    "required": [
        "numero_contrato",
        "objeto_contractual",
        "nombre_contratista",
        "vigencia",
        "anio_contrato",
        "fecha_inicial",
        "valor",
        "tipo_persona",
        "tipo_contrato",
    ],
}


# ─── Document Request/Response ───

class DocumentRequest(BaseModel):
    """Texto OCR completo de un documento (UN solo contrato)."""
    raw_text: str = Field(
        ...,
        min_length=50,
        max_length=2_000_000,
        description="Texto OCR completo del documento. El sistema filtra ruido "
                    "(hojas de vida, experiencia, cuotas) y extrae UN solo contrato.",
    )
    fields: Optional[list[str]] = Field(
        default=None,
        description="Campos a retornar del contrato.",
    )
    model: Optional[str] = Field(default=None)
    temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0)


class DocumentResponse(BaseModel):
    """Respuesta del endpoint de documento — UN solo contrato extraído."""
    success: bool
    data: Optional[ContractData | dict] = None
    model_used: str
    total_chars: int = 0
    prepared_chars: int = 0
    processing_time_ms: float = 0
    cached: bool = False
    error: Optional[str] = None
