"""
Test de extracción con datos REALES de OCR — pages.txt
Expediente contractual de la Gobernación del Valle del Cauca.

El documento contiene 11 contratos distintos:
  - 1 contrato principal (2019): minuta completa + SECOP + actas
  - 10 contratos históricos (2010-2018): en la sección de certificaciones

Estrategia:
  1. Extraer la sección de certificaciones y dividirla por cada contrato histórico
  2. Extraer la minuta/SECOP del contrato principal 2019
  3. Enviar cada fragmento al endpoint de extracción
  4. Comparar con ground truth conocido
"""

import asyncio
import json
import re
import time
from pathlib import Path

import httpx

# ─── Configuración ───────────────────────────────────────────────
API_URL = "http://localhost:8000"
API_KEY = "sk-iaocr-dev-001"
HEADERS = {"X-API-Key": API_KEY, "Content-Type": "application/json"}
TIMEOUT = httpx.Timeout(700.0)
PAGES_FILE = Path(__file__).parent / "pages.txt"

# ─── Ground truth de TODOS los contratos ─────────────────────────
GROUND_TRUTH = {
    "0205": {
        "numero_contrato": "0205",
        "nombre_contratista": "ERIKA MARIA PALOMINO BOLIVAR",
        "tipo_persona": "Natural",
        "tipo_contrato": "Prestación de servicios",
        "objeto_contractual": "prestar los servicios profesionales como Administradora Empresarial",
        "valor": 17748000,
        "anio_contrato": 2010,
        "fecha_inicial": "2010-01-29",
        "vigencia": "22 de julio de 2010",
    },
    "0409": {
        "numero_contrato": "0409",
        "nombre_contratista": "ERIKA MARIA PALOMINO BOLIVAR",
        "tipo_persona": "Natural",
        "tipo_contrato": "Prestación de servicios",
        "objeto_contractual": "prestación de servicios profesionales como Administradora de Empresas",
        "valor": 30000000,
        "anio_contrato": 2011,
        "fecha_inicial": "2011-03-18",
        "vigencia": "31 de diciembre de 2011",
    },
    "0269": {
        "numero_contrato": "0269",
        "nombre_contratista": "ERIKA MARIA PALOMINO BOLIVAR",
        "tipo_persona": "Natural",
        "tipo_contrato": "Prestación de servicios",
        "objeto_contractual": "prestación de servicios profesionales como Administradora de Empresas",
        "valor": 31119000,
        "anio_contrato": 2012,
        "fecha_inicial": "2012-03-29",
        "vigencia": "31 de diciembre de 2012",
    },
    "0340": {
        "numero_contrato": "0340",
        "nombre_contratista": "ERIKA MARIA PALOMINO BOLIVAR",
        "tipo_persona": "Natural",
        "tipo_contrato": "Prestación de servicios",
        "objeto_contractual": "prestación de servicios profesionales como Administradora de Empresas",
        "valor": 35000000,
        "anio_contrato": 2013,
        "fecha_inicial": "2013-04-16",
        "vigencia": "31 de diciembre de 2013",
    },
    "1203": {
        "numero_contrato": "1203",
        "nombre_contratista": "ERIKA MARIA PALOMINO BOLIVAR",
        "tipo_persona": "Natural",
        "tipo_contrato": "Prestación de servicios",
        "objeto_contractual": "prestación de servicios profesionales como Administradora de Empresas",
        "valor": 39655000,
        "anio_contrato": 2013,
        "fecha_inicial": "2013-12-05",
        "vigencia": "31 de octubre de 2014",
    },
    "1257": {
        "numero_contrato": "1257",
        "nombre_contratista": "ERIKA MARIA PALOMINO BOLIVAR",
        "tipo_persona": "Natural",
        "tipo_contrato": "Prestación de servicios",
        "objeto_contractual": "prestación de Servicios Profesionales como Administradora de Empresas",
        "valor": 48162800,
        "anio_contrato": 2014,
        "fecha_inicial": "2014-12-05",
        "vigencia": "31 de diciembre de 2015",
    },
    "090-18-11-0584": {
        "numero_contrato": "090-18-11-0584",
        "nombre_contratista": "ERIKA MARIA PALOMINO BOLIVAR",
        "tipo_persona": "Natural",
        "tipo_contrato": "Prestación de servicios",
        "objeto_contractual": "Prestar los Servicios Profesionales como Administradora de Empresas",
        "valor": 31787560,
        "anio_contrato": 2016,
        "fecha_inicial": "2016-04-11",
        "vigencia": "30 de noviembre de 2016",
    },
    "090-18-11-0316": {
        "numero_contrato": "090-18-11-0316",
        "nombre_contratista": "ERIKA MARIA PALOMINO BOLIVAR",
        "tipo_persona": "Natural",
        "tipo_contrato": "Prestación de servicios",
        "objeto_contractual": "servicios profesionales como Administradora de Empresas",
        "valor": 24794280,
        "anio_contrato": 2017,
        "fecha_inicial": "2017-01-19",
        "vigencia": "31 de julio de 2017",
    },
    "090-18-11-4196": {
        "numero_contrato": "090-18-11-4196",
        "nombre_contratista": "ERIKA MARIA PALOMINO BOLIVAR",
        "tipo_persona": "Natural",
        "tipo_contrato": "Prestación de servicios",
        "objeto_contractual": "servicios profesionales como Administradora de Empresas",
        "valor": 8264760,
        "anio_contrato": 2017,
        "fecha_inicial": "2017-11-02",
        "vigencia": "29 de diciembre de 2017",
    },
    "090-18-11-0332": {
        "numero_contrato": "090-18-11-0332",
        "nombre_contratista": "ERIKA MARIA PALOMINO BOLIVAR",
        "tipo_persona": "Natural",
        "tipo_contrato": "Prestación de servicios",
        "objeto_contractual": "servicios profesionales como Administradora de Empresas",
        "valor": 49588560,
        "anio_contrato": 2018,
        "fecha_inicial": "2018-01-05",
        "vigencia": "31 de diciembre de 2018",
    },
    "1.220.02-59.2-0006": {
        "numero_contrato": "1.220.02-59.2-0006",
        "nombre_contratista": "ERIKA MARIA PALOMINO BOLIVAR",
        "tipo_persona": "Natural",
        "tipo_contrato": "Prestación de servicios",
        "objeto_contractual": "servicios profesionales como Administradora de Empresas",
        "valor": 49588560,
        "anio_contrato": 2019,
        "fecha_inicial": "2019-01-04",
        "vigencia": "12 meses",
    },
}


# ─── Splitting inteligente del documento ─────────────────────────

def split_certified_contracts(text: str) -> list[tuple[str, str]]:
    """
    Encuentra la sección de certificaciones y divide cada contrato histórico.
    Prepend el header de certificación (nombre + cédula) a cada fragmento.
    Retorna lista de (contract_id, texto_del_contrato).
    """
    # ── Extraer header de la certificación (contiene nombre y cédula)
    cert_header = ""
    header_match = re.search(
        r"(CERTIFICA:\s*\n.*?(?:cédula de ciudadanía|C\.C\.|CC).*?\n.*?contratos.*?:\s*\n?)",
        text, re.IGNORECASE | re.DOTALL
    )
    if header_match:
        cert_header = header_match.group(1).strip() + "\n\n"
    else:
        # Fallback: buscar línea "Que NOMBRE identificado"
        name_match = re.search(
            r"(Que\s+[A-ZÁÉÍÓÚÑ\s]+identificado.*?(?:contratos|contrato).*?:\s*\n?)",
            text, re.IGNORECASE | re.DOTALL
        )
        if name_match:
            cert_header = name_match.group(1).strip() + "\n\n"

    contract_pattern = re.compile(
        r"Contrato:\s*No\.?\s*([\w\.\-]+)\s+del\s+(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})",
        re.IGNORECASE
    )

    matches = list(contract_pattern.finditer(text))
    contracts = []

    for i, match in enumerate(matches):
        contract_id = match.group(1)
        start = match.start()

        # El texto termina donde empieza el siguiente contrato certificado
        if i + 1 < len(matches):
            end = matches[i + 1].start()
        else:
            # Último: tomar hasta "Se expide" o +4000 chars
            end = min(start + 4000, len(text))
            end_marker = text.find("Se expide para efectos", start)
            if end_marker > start:
                end = end_marker + 200

        chunk = text[start:end].strip()

        # Filtrar otrosíes (Contrato Principal No...) y chunks muy pequeños
        if len(chunk) >= 100:
            first_line = chunk[:120]
            if "Contrato Principal" not in first_line and "Modificatorio" not in first_line[:50]:
                # Prepend header con nombre y cédula para contexto
                contracts.append((contract_id, cert_header + chunk))

    return contracts


def extract_main_contract_2019(text: str) -> str:
    """
    Extrae la información del contrato 2019 combinando SECOP + Acta Inicio + Acta Pago.
    """
    lines = text.split("\n")
    parts = []

    # SECOP (datos perfectamente estructurados)
    for i, line in enumerate(lines):
        if re.search(r"Detalle\s+del\s+Proceso\s+N[uú]mero", line, re.IGNORECASE):
            start = max(0, i - 2)
            end = min(len(lines), i + 70)
            parts.append("\n".join(lines[start:end]))
            break

    # Acta de Inicio
    for i, line in enumerate(lines):
        if re.search(r"^ACTA\s+DE\s+INICIO", line.strip(), re.IGNORECASE):
            context = "\n".join(lines[max(0, i-5):min(len(lines), i+5)])
            if "Santiago de Cali" in context or "prestación" in context.lower():
                start = max(0, i - 5)
                end = min(len(lines), i + 45)
                parts.append("\n".join(lines[start:end]))
                break

    # Acta de Pago Final
    for i, line in enumerate(lines):
        if re.search(r"ACTA\s+DE\s+PAGO\s+FINAL", line, re.IGNORECASE):
            start = max(0, i - 5)
            end = min(len(lines), i + 45)
            parts.append("\n".join(lines[start:end]))
            break

    return "\n\n==========\n\n".join(parts)


# ─── Evaluación ──────────────────────────────────────────────────

def evaluate_result(data: dict, gt: dict) -> dict:
    """Compara resultado extraído vs ground truth."""
    if not data:
        return {"score": 0, "total": 9, "details": {}}

    score = 0
    details = {}

    for field, expected in gt.items():
        extracted = data.get(field)
        if extracted is None:
            details[field] = ("❌", None, expected)
            continue

        ext_s = str(extracted).lower().strip()
        exp_s = str(expected).lower().strip()
        match = False

        if field == "numero_contrato":
            clean_ext = re.sub(r"[^0-9\-]", "", str(extracted))
            clean_exp = re.sub(r"[^0-9\-]", "", str(expected))
            match = clean_exp in clean_ext or clean_ext in clean_exp or exp_s in ext_s
        elif field == "valor":
            try:
                ext_num = int(float(extracted))
                match = ext_num == expected
            except (ValueError, TypeError):
                match = False
        elif field == "anio_contrato":
            try:
                match = int(extracted) == expected
            except (ValueError, TypeError):
                match = False
        elif field == "nombre_contratista":
            match = "palomino" in ext_s and ("erika" in ext_s or "bolivar" in ext_s)
        elif field == "tipo_contrato":
            match = "prestaci" in ext_s and "servicio" in ext_s
        elif field == "tipo_persona":
            match = "natural" in ext_s
        elif field == "objeto_contractual":
            match = "administradora" in ext_s and "empresa" in ext_s
        elif field == "vigencia":
            # Accept date, duration, or year match
            match = (
                exp_s in ext_s or ext_s in exp_s
                or str(expected)[:4] in ext_s
                # Accept if key parts overlap (month, year)
                or any(w in ext_s for w in exp_s.split() if len(w) > 3)
            )
        elif field == "fecha_inicial":
            exp_year = str(expected)[:4]
            match = exp_year in ext_s
        else:
            match = exp_s in ext_s or ext_s in exp_s

        if match:
            score += 1
            details[field] = ("✅", extracted, expected)
        else:
            details[field] = ("⚠️", extracted, expected)

    return {"score": score, "total": 9, "details": details}


# ─── Envío ───────────────────────────────────────────────────────

async def send_extraction(client: httpx.AsyncClient, text: str, label: str) -> dict:
    """Envía texto al endpoint de extracción."""
    print(f"\n{'─'*65}")
    print(f"📤 {label}  ({len(text):,} chars)")

    payload = {"raw_text": text}
    start = time.perf_counter()

    try:
        resp = await client.post(
            f"{API_URL}/api/v1/extract",
            headers=HEADERS,
            json=payload,
            timeout=TIMEOUT,
        )
        elapsed = time.perf_counter() - start
        result = resp.json()

        if result.get("success"):
            data = result["data"]
            tokens = result.get("meta", {}).get("tokens_used", 0)
            print(f"   ⏱️ {elapsed:.1f}s | tokens: {tokens}")
            return {
                "label": label, "success": True, "data": data,
                "time_s": round(elapsed, 1), "chars": len(text),
            }
        else:
            print(f"   ❌ {result.get('error', '?')[:80]}")
            return {"label": label, "success": False, "error": result.get("error"), "time_s": round(elapsed, 1)}

    except Exception as e:
        print(f"   💥 {e}")
        return {"label": label, "success": False, "error": str(e), "time_s": round(time.perf_counter() - start, 1)}


# ─── Main ────────────────────────────────────────────────────────

async def main():
    print("=" * 65)
    print("🔍 TEST: EXTRACCIÓN MULTI-CONTRATO (OCR REAL)")
    print("   Archivo: pages.txt — Gobernación del Valle del Cauca")
    print("=" * 65)

    raw_text = PAGES_FILE.read_text(encoding="utf-8")
    print(f"\n📄 {len(raw_text):,} chars | {len(raw_text.splitlines()):,} líneas")

    # Verificar API
    async with httpx.AsyncClient() as chk:
        try:
            h = await chk.get(f"{API_URL}/health", timeout=10)
            hd = h.json()
            print(f"🏥 API: {hd.get('status')} | modelo: {hd.get('default_model')}")
            if hd.get("status") != "ok":
                print("⛔ Abortando."); return
        except Exception as e:
            print(f"⛔ API inaccesible: {e}"); return

    # ── Dividir contratos
    print("\n📋 Detectando contratos en el documento...")
    certified = split_certified_contracts(raw_text)
    main_2019 = extract_main_contract_2019(raw_text)

    print(f"\n   🏛️  Contratos certificados (históricos): {len(certified)}")
    for cid, txt in certified:
        print(f"      • No.{cid} ({len(txt):,} chars)")
    print(f"   📄 Contrato principal 2019: {len(main_2019):,} chars")

    # Preparar pruebas
    tests: list[tuple[str, str, str]] = []
    for cid, txt in certified:
        tests.append((cid, f"Cert. No.{cid}", txt))
    tests.append(("1.220.02-59.2-0006", "Principal 2019 (No.0006)", main_2019))

    total = len(tests)
    print(f"\n📝 Total: {total} contratos")
    print(f"   ⏱️  Estimado: ~{total * 90 / 60:.0f} min")

    # ── Ejecutar
    results = []
    t0 = time.perf_counter()

    async with httpx.AsyncClient() as client:
        for i, (ckey, label, text) in enumerate(tests, 1):
            print(f"\n[{i}/{total}]", end="")
            result = await send_extraction(client, text, label)

            gt = GROUND_TRUTH.get(ckey)
            if gt and result.get("success"):
                ev = evaluate_result(result["data"], gt)
                result["score"] = ev["score"]
                result["total"] = ev["total"]
                result["evaluation"] = ev["details"]
                print(f"   📊 {ev['score']}/9")
                for f, (st, ext, exp) in ev["details"].items():
                    e_disp = str(ext)[:50] if ext else "null"
                    print(f"      {st} {f}: {e_disp}")
            else:
                result["score"] = None
                result["total"] = 9

            results.append(result)

    total_time = time.perf_counter() - t0

    # ─── Resumen ───────────────────────────────────────────
    print("\n" + "=" * 65)
    print("📊 RESUMEN")
    print("=" * 65)

    ok = [r for r in results if r.get("success")]
    fail = [r for r in results if not r.get("success")]
    scored = [r for r in ok if r.get("score") is not None]

    print(f"\n{'Contrato':<42} {'Score':>6} {'t(s)':>6}")
    print("─" * 58)

    ts = tf = 0
    for r in results:
        lb = r["label"][:40]
        if r.get("success") and r.get("score") is not None:
            ss = f"{r['score']}/{r['total']}"
            ts += r["score"]; tf += r["total"]
        elif r.get("success"):
            ss = "OK"
        else:
            ss = "ERR"
        print(f"  {lb:<40} {ss:>6} {r.get('time_s',0):>5.0f}s")

    print("─" * 58)
    print(f"  ✅ Exitosos: {len(ok)}/{total}  |  ❌ Fallidos: {len(fail)}/{total}")
    if scored:
        pct = ts / tf * 100 if tf else 0
        print(f"  📊 Precisión global: {ts}/{tf} campos ({pct:.1f}%)")
        print(f"  📊 Promedio por contrato: {ts/len(scored):.1f}/9")
    print(f"  ⏱️  Total: {total_time:.0f}s ({total_time/60:.1f} min)")
    print(f"  ⏱️  Promedio: {total_time/total:.0f}s/contrato")

    # ── Precisión por campo
    if scored:
        fsc: dict[str, list[bool]] = {}
        for r in scored:
            if "evaluation" in r:
                for f, (st, _, _) in r["evaluation"].items():
                    fsc.setdefault(f, []).append(st.startswith("✅"))

        print(f"\n📈 PRECISIÓN POR CAMPO ({len(scored)} contratos):")
        print("─" * 50)
        for f, hits in sorted(fsc.items(), key=lambda x: sum(x[1])/len(x[1]), reverse=True):
            c = sum(hits); t = len(hits)
            p = c / t * 100
            bar = "█" * int(p / 5) + "░" * (20 - int(p / 5))
            print(f"  {f:<22} {c:>2}/{t:<2} {bar} {p:.0f}%")

    # ── Guardar
    out = Path(__file__).parent / "results_real_ocr.json"
    ser = []
    for r in results:
        sr = dict(r)
        if "evaluation" in sr:
            sr["evaluation"] = {
                k: {"status": v[0], "extracted": v[1], "expected": v[2]}
                for k, v in sr["evaluation"].items()
            }
        ser.append(sr)

    with open(out, "w", encoding="utf-8") as f:
        json.dump({
            "test": "real_ocr_multi_contract",
            "source": "pages.txt",
            "total_contracts": total,
            "results": ser,
            "summary": {
                "ok": len(ok), "fail": len(fail),
                "score": ts, "fields": tf,
                "accuracy": round(ts / tf * 100, 1) if tf else 0,
                "time_s": round(total_time, 1),
            },
        }, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n💾 {out.name}")


if __name__ == "__main__":
    asyncio.run(main())
