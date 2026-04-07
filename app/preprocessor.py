"""Pre-procesador de texto OCR para contratos colombianos.

Enfoque v4: Cada documento OCR = UN solo contrato.
Se extraen las secciones prioritarias y se descarta el ruido
(hojas de vida, experiencia laboral, cuotas mensuales repetitivas, matrices de riesgo).
"""

import re
import unicodedata


# ═══════════════════════════════════════════════════════════════════
# Limpieza básica de texto OCR
# ═══════════════════════════════════════════════════════════════════

def clean_ocr_text(text: str) -> str:
    """
    Limpia texto proveniente de OCR:
    - Normaliza Unicode (tildes, ñ)
    - Colapsa espacios/tabs múltiples
    - Elimina caracteres basura (control chars, artifacts)
    - Normaliza saltos de línea
    """
    text = unicodedata.normalize("NFC", text)
    text = re.sub(r"[^\S\n\r\t]+", " ", text)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", "", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = "\n".join(line.strip() for line in text.split("\n"))
    return text.strip()


def truncate_text(text: str, max_chars: int = 10000) -> str:
    """Trunca texto largo en un punto natural."""
    if len(text) <= max_chars:
        return text
    truncated = text[:max_chars]
    last_period = truncated.rfind(".")
    if last_period > max_chars * 0.7:
        truncated = truncated[: last_period + 1]
    return truncated + "\n\n[... texto truncado ...]"


def preprocess(text: str, max_chars: int = 10000) -> str:
    """Pipeline completo de pre-procesamiento para un contrato individual."""
    text = clean_ocr_text(text)
    text = truncate_text(text, max_chars)
    return text


# ═══════════════════════════════════════════════════════════════════
# Extractor inteligente de secciones prioritarias (1 solo contrato)
# ═══════════════════════════════════════════════════════════════════

def _find_section(lines: list[str], pattern: str, before: int = 2, after: int = 80,
                  flags: int = re.IGNORECASE) -> str | None:
    """Busca una sección por regex en las líneas y extrae contexto alrededor."""
    for i, line in enumerate(lines):
        if re.search(pattern, line, flags):
            start = max(0, i - before)
            end = min(len(lines), i + after)
            return "\n".join(lines[start:end])
    return None


def _find_section_between(lines: list[str], start_pattern: str, end_pattern: str,
                          max_lines: int = 200) -> str | None:
    """Extrae texto entre dos patrones regex."""
    start_idx = None
    for i, line in enumerate(lines):
        if start_idx is None:
            if re.search(start_pattern, line, re.IGNORECASE):
                start_idx = i
        elif re.search(end_pattern, line, re.IGNORECASE) and i > start_idx + 5:
            return "\n".join(lines[start_idx:i])
        elif i - start_idx > max_lines:
            return "\n".join(lines[start_idx:i])
    if start_idx is not None:
        end = min(len(lines), start_idx + max_lines)
        return "\n".join(lines[start_idx:end])
    return None


def _extract_estudios_previos(lines: list[str]) -> str | None:
    """
    Extrae la sección de Estudios Previos.
    Contiene: objeto, valor, plazo, forma de pago, perfil requerido.
    Busca el documento formal (página 1 de N, con fecha de elaboración).
    """
    for i, line in enumerate(lines):
        if re.search(r"ESTUDIOS\s+PREVIOS", line, re.IGNORECASE):
            # Verificar que es el documento formal (tiene Decreto 1082, Página, Fecha)
            context = "\n".join(lines[max(0, i - 2):min(len(lines), i + 10)])
            if re.search(r"DECRETO\s+1082|P[aá]gina\s+1\s+de|Fecha\s+de\s+(?:Elaboraci|Aprobaci)", context, re.IGNORECASE):
                # Verificar además que tiene contenido de contrato cerca
                extended = "\n".join(lines[i:min(len(lines), i + 50)])
                if re.search(r"OBJETO|NECESIDAD|VALOR|PLAZO|contrat", extended, re.IGNORECASE):
                    end = min(len(lines), i + 120)
                    return "\n".join(lines[i:end])
    return None


def _extract_contract_body(lines: list[str]) -> str | None:
    """
    Extrae el cuerpo del contrato (minuta).
    Busca la minuta formal con 'CONTRATO DE PRESTACIÓN ... No. XXX'
    seguido de CONTRATANTE/CONTRATISTA/CLÁUSULA.
    """
    # Buscar la minuta formal: encabezado con número de contrato
    start_idx = None
    for i, line in enumerate(lines):
        # Detectar encabezado formal del contrato con número
        if re.search(
            r"CONTRATO\s+DE\s+PRESTACI[OÓ]N\s+DE\s+SERVICIOS\s+(?:PROFESIONALES?|DE\s+APOYO)",
            line, re.IGNORECASE
        ):
            # Verificar que es la minuta real (tiene CONTRATANTE, No., o CLÁUSULA cerca)
            context = "\n".join(lines[max(0, i - 2):min(len(lines), i + 15)])
            if re.search(r"CONTRATANTE\s*:|No\.\s*[\d\.]|CL[AÁ]USULA\s+PRIMERA|OBJETO\s*:", context, re.IGNORECASE):
                start_idx = max(0, i - 3)
                break

    if start_idx is None:
        # Fallback: buscar "CLÁUSULA PRIMERA" directamente
        for i, line in enumerate(lines):
            if re.search(r"CL[AÁ]USULA\s+PRIMERA", line, re.IGNORECASE):
                start_idx = max(0, i - 10)
                break

    if start_idx is None:
        return None

    # Tomar hasta 300 líneas (cubre el contrato con todas sus cláusulas)
    end = min(len(lines), start_idx + 300)
    return "\n".join(lines[start_idx:end])


def _extract_certifican(lines: list[str]) -> str | None:
    """
    Extrae la certificación de inexistencia de personal (CERTIFICAN).
    Contiene: nombre contratista, cédula, modalidad, plazo.
    """
    for i, line in enumerate(lines):
        if re.search(r"CERTIFICA[N]?\s*:", line, re.IGNORECASE):
            # Verificar que es la certificación de contratación (no ARL u otra)
            context = "\n".join(lines[max(0, i):min(len(lines), i + 15)])
            if re.search(
                r"contratar|prestaci[oó]n|planta|insuficiencia|autoriza",
                context, re.IGNORECASE,
            ):
                start = max(0, i - 3)
                end = min(len(lines), i + 50)
                return "\n".join(lines[start:end])
    return None


def _extract_secop(lines: list[str]) -> str | None:
    """
    Extrae la sección SECOP (datos estructurados del proceso).
    """
    return _find_section(lines, r"Detalle\s+del\s+Proceso\s+N[uú]mero", before=2, after=80)


def _extract_acta_inicio(lines: list[str]) -> str | None:
    """
    Extrae la sección 'Acta de Inicio' formal del contrato.
    Contiene: fecha de inicio, partes, lugar.
    Busca la cabecera formal del documento (no menciones dentro de certificaciones
    de experiencia ni párrafos de cláusulas).
    """
    for i, line in enumerate(lines):
        stripped = line.strip()
        # Solo "ACTA DE INICIO" como título (corto, sin otros datos en la línea)
        if re.match(r"^ACTA\s+DE\s+INICIO\s*\\?$", stripped, re.IGNORECASE):
            # Confirmar que es un documento formal (tiene Página, Gobernación, ciudad)
            context = "\n".join(lines[max(0, i):min(len(lines), i + 10)])
            if re.search(r"P[aá]gina|GOBERNACION|Santiago\s+de\s+Cali", context, re.IGNORECASE):
                start = max(0, i - 3)
                end = min(len(lines), i + 50)
                return "\n".join(lines[start:end])
    return None


def _extract_acta_cumplimiento(lines: list[str]) -> str | None:
    """
    Extrae el Acta Final de Cumplimiento.
    Contiene: porcentaje de ejecución, valor ejecutado.
    """
    return _find_section(
        lines,
        r"ACTA\s+(?:FINAL\s+)?DE\s+CUMPLIMIENTO|ACTA\s+DE\s+PAGO\s+FINAL",
        before=3, after=50,
    )


def _extract_cdp(lines: list[str]) -> str | None:
    """
    Extrae la sección del Certificado de Disponibilidad Presupuestal (CDP).
    """
    return _find_section(
        lines,
        r"Certificado\s+de\s+Disponibilidad\s+Presupuestal",
        before=2, after=30,
    )


def _is_noise_section(text: str) -> bool:
    """Detecta si un bloque de texto es ruido (CV, experiencia, cuotas repetitivas)."""
    noise_patterns = [
        r"HOJA\s+DE\s+VIDA",
        r"FORMATO\s+[UÚ]NICO.*FUNCI[OÓ]N\s+P[UÚ]BLICA",
        r"EXPERIENCIA\s+LABORAL",
        r"FORMACI[OÓ]N\s+ACAD[EÉ]MICA",
        r"DATOS\s+PERSONALES",
        r"CUOTA\s+No\.?\s*\d",
        r"Documento\s+Equivalente.*R[eé]gimen\s+Simplificado",
        r"Planilla\s+(?:Integrada|de\s+Pago).*Seguridad\s+Social",
        r"MATRIZ\s+DE\s+RIESGO",
        r"ADMINISTRACI[OÓ]N.*MANEJO\s+DEL\s+RIESGO",
    ]
    first_500 = text[:500]
    return any(re.search(p, first_500, re.IGNORECASE) for p in noise_patterns)


def _remove_repetitive_cuotas(text: str) -> str:
    """
    Elimina los ciclos de cuotas mensuales repetitivas (informes, planillas, pagos).
    Estos ocupan ~70% del documento y no aportan datos del contrato.
    """
    lines = text.split("\n")
    result = []
    skip_until_next_section = False
    cuota_count = 0
    removed_lines = 0
    found_section_end = False

    for i, line in enumerate(lines):
        # Detectar inicio de cuota mensual
        if re.search(r"CUOTA\s+No\.?\s*\d+|Documento\s+Equivalente.*Simplificado", line, re.IGNORECASE):
            if cuota_count == 0:
                # Mantener la primera cuota como referencia
                skip_until_next_section = False
            else:
                skip_until_next_section = True
                removed_lines += 1
            cuota_count += 1
            continue

        # Detectar fin de sección de cuotas (nueva sección importante)
        if skip_until_next_section and re.search(
            r"ACTA\s+(?:FINAL|DE\s+PAGO|DE\s+CUMPLIMIENTO|DE\s+LIQUIDACI)",
            line, re.IGNORECASE,
        ):
            skip_until_next_section = False
            found_section_end = True

        if not skip_until_next_section:
            result.append(line)
        else:
            removed_lines += 1

    # Si nunca se encontró una nueva sección importante, no arriesgarse a perder
    # casi todo el OCR por una detección falsa en una tabla índice.
    if skip_until_next_section and not found_section_end:
        return text

    # Salvaguarda adicional: evita recortes excesivos cuando el patrón no aplica.
    if lines and (removed_lines / len(lines)) > 0.70:
        return text

    return "\n".join(result)


def prepare_single_contract(text: str, max_chars: int = 10000) -> str:
    """
    Prepara el texto OCR de un documento para extracción de UN solo contrato.

    Estrategia:
    1. Limpiar OCR
    2. Eliminar cuotas mensuales repetitivas
    3. Extraer secciones prioritarias (contrato, estudios previos, certificación,
       acta de inicio, SECOP, CDP)
    4. Distribuir presupuesto de caracteres entre secciones
    5. Combinar y truncar al límite

    Retorna texto optimizado listo para enviar a Ollama.
    """
    text = clean_ocr_text(text)
    text = _remove_repetitive_cuotas(text)
    lines = text.split("\n")

    # Extraer secciones prioritarias con presupuesto de chars proporcional
    # (label, extractor, peso relativo)
    extractors = [
        ("CUERPO DEL CONTRATO", _extract_contract_body, 4),
        ("ESTUDIOS PREVIOS", _extract_estudios_previos, 2),
        ("CERTIFICACIÓN DE CONTRATACIÓN", _extract_certifican, 1),
        ("ACTA DE INICIO", _extract_acta_inicio, 1),
        ("DATOS SECOP", _extract_secop, 1),
        ("CDP", _extract_cdp, 1),
        ("ACTA FINAL", _extract_acta_cumplimiento, 1),
    ]

    # Extraer todas las secciones primero
    raw_sections: list[tuple[str, str, int]] = []  # (label, text, weight)
    for label, func, weight in extractors:
        result = func(lines)
        if result:
            raw_sections.append((label, result, weight))

    if not raw_sections:
        # Fallback: si no se detectó ninguna sección, usar texto limpio completo
        return truncate_text(text, max_chars)

    # Distribuir presupuesto de caracteres proporcionalmente al peso
    overhead = sum(len(f"=== {label} ===\n") + 2 for label, _, _ in raw_sections)
    available = max_chars - overhead
    total_weight = sum(w for _, _, w in raw_sections)

    parts = []
    for label, content, weight in raw_sections:
        budget = int(available * weight / total_weight)
        trimmed = truncate_text(content, budget)
        parts.append(f"=== {label} ===\n{trimmed}")

    return "\n\n".join(parts)
