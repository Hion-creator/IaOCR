"""
Test de 50 contratos – Genera contratos variados, envía en batch y muestra resultados.
Guarda los resultados completos en results_50.json
"""

import httpx
import json
import time
import random
import sys

BASE = "http://localhost:8000"
HEADERS = {"X-API-Key": "sk-iaocr-dev-001"}
TIMEOUT = 7200  # 2h max

# ─── Datos para generar contratos variados ───

TIPOS_CONTRATO = [
    "PRESTACION DE SERVICIOS",
    "OBRA",
    "SUMINISTRO",
    "CONSULTORIA",
    "COMPRAVENTA",
    "ARRENDAMIENTO",
    "INTERADMINISTRATIVO",
    "CONVENIO",
]

ENTIDADES = [
    ("ALCALDIA MUNICIPAL DE BUCARAMANGA", "890.201.222-1"),
    ("GOBERNACION DE SANTANDER", "890.201.576-3"),
    ("MUNICIPIO DE FLORIDABLANCA", "890.208.390-2"),
    ("MUNICIPIO DE GIRON", "890.204.895-6"),
    ("UNIVERSIDAD INDUSTRIAL DE SANTANDER", "890.201.213-4"),
    ("EMPRESA DE ACUEDUCTO DE BUCARAMANGA", "800.154.719-5"),
    ("HOSPITAL UNIVERSITARIO DE SANTANDER", "890.203.222-8"),
    ("SECRETARIA DE EDUCACION DEPARTAMENTAL", "890.201.576-3"),
    ("ALCALDIA MUNICIPAL DE PIEDECUESTA", "890.210.222-7"),
    ("EMPRESA DE ASEO DE BUCARAMANGA", "800.098.456-1"),
]

CONTRATISTAS_NATURAL = [
    ("MARIA FERNANDA RODRIGUEZ SILVA", "63.456.789", "Bucaramanga"),
    ("CARLOS ANDRES MARTINEZ LOPEZ", "91.234.567", "Floridablanca"),
    ("ANDREA PATRICIA GOMEZ RUIZ", "37.890.123", "Giron"),
    ("JUAN DAVID PEREZ CASTRO", "13.567.890", "Piedecuesta"),
    ("LAURA VALENTINA DIAZ MORENO", "63.789.012", "Bucaramanga"),
    ("DIEGO ALEJANDRO TORRES VARGAS", "91.345.678", "Lebrija"),
    ("CAMILA ANDREA SANCHEZ LEON", "37.012.345", "Bucaramanga"),
    ("SANTIAGO ANDRES HERRERA PINTO", "13.678.901", "Floridablanca"),
    ("ANA MARIA CASTILLO DUARTE", "63.234.567", "Barrancabermeja"),
    ("PEDRO LUIS RAMIREZ ORTIZ", "91.890.123", "San Gil"),
]

CONTRATISTAS_JURIDICA = [
    ("CONSTRUCCIONES Y DISEÑOS S.A.S.", "900.345.678-1", "Bucaramanga"),
    ("INGENIERIA CIVIL DEL ORIENTE LTDA", "800.234.567-9", "Floridablanca"),
    ("SUMINISTROS INDUSTRIALES ANDINOS S.A.", "900.567.890-3", "Bogota"),
    ("CONSULTORES ASOCIADOS DEL NORORIENTE S.A.S.", "900.678.901-5", "Bucaramanga"),
    ("GRUPO EMPRESARIAL SANTANDER LTDA", "800.901.234-7", "Giron"),
    ("TECNOLOGIA Y SERVICIOS INTEGRADOS S.A.S.", "900.123.456-2", "Medellin"),
    ("INVERSIONES PIEDECUESTA S.A.", "800.345.678-4", "Piedecuesta"),
    ("SOLUCIONES AMBIENTALES DEL ORIENTE S.A.S.", "900.432.109-6", "Bucaramanga"),
    ("ALIMENTOS Y PROVISIONES COLOMBIA LTDA", "800.765.432-8", "Bogota"),
    ("SERVICIOS LOGISTICOS NACIONALES S.A.S.", "900.876.543-0", "Cali"),
]

OBJETOS = {
    "PRESTACION DE SERVICIOS": [
        "PRESTAR SERVICIOS PROFESIONALES COMO ABOGADO PARA APOYAR LA GESTION JURIDICA EN EL AREA DE CONTRATACION",
        "PRESTAR SERVICIOS DE APOYO A LA GESTION EN ACTIVIDADES ADMINISTRATIVAS DE LA SECRETARIA DE HACIENDA",
        "PRESTAR SERVICIOS PROFESIONALES COMO INGENIERO DE SISTEMAS PARA EL SOPORTE TECNICO DE LA PLATAFORMA TECNOLOGICA",
        "PRESTAR SERVICIOS PROFESIONALES COMO CONTADOR PUBLICO PARA APOYAR LOS PROCESOS CONTABLES Y FINANCIEROS",
        "PRESTAR SERVICIOS PROFESIONALES EN PSICOLOGIA PARA ATENCION DE POBLACION VULNERABLE",
    ],
    "OBRA": [
        "CONSTRUCCION DE PAVIMENTO RIGIDO EN LA CARRERA 15 ENTRE CALLES 30 Y 45 DEL BARRIO ALARCON",
        "MEJORAMIENTO Y REHABILITACION DE LA VIA QUE CONDUCE AL CORREGIMIENTO DE CAFE MADRID",
        "CONSTRUCCION DEL PUENTE VEHICULAR SOBRE LA QUEBRADA SURATA EN EL SECTOR LOS ANGELES",
        "ADECUACION Y REMODELACION DE LAS INSTALACIONES DE LA SEDE ADMINISTRATIVA MUNICIPAL",
        "CONSTRUCCION DE PLACA POLIDEPORTIVA EN LA COMUNA 7 DEL MUNICIPIO",
    ],
    "SUMINISTRO": [
        "SUMINISTRO DE RACIONES ALIMENTARIAS PARA EL PROGRAMA DE ALIMENTACION ESCOLAR PAE",
        "SUMINISTRO DE MATERIALES DE CONSTRUCCION PARA EL MANTENIMIENTO DE VIAS TERCIARIAS",
        "SUMINISTRO DE EQUIPOS DE COMPUTO Y PERIFERICOS PARA LAS DEPENDENCIAS DE LA ALCALDIA",
        "SUMINISTRO DE ELEMENTOS DE BIOSEGURIDAD PARA EL PERSONAL DE LA SECRETARIA DE SALUD",
        "SUMINISTRO DE COMBUSTIBLE PARA EL PARQUE AUTOMOTOR DE LA ADMINISTRACION MUNICIPAL",
    ],
    "CONSULTORIA": [
        "REALIZAR LA CONSULTORIA PARA LA ELABORACION DE LOS ESTUDIOS Y DISEÑOS DE LA RED DE ALCANTARILLADO",
        "CONSULTORIA PARA LA ACTUALIZACION DEL PLAN DE ORDENAMIENTO TERRITORIAL DEL MUNICIPIO",
        "INTERVENTORIA TECNICA, ADMINISTRATIVA, FINANCIERA Y AMBIENTAL DEL CONTRATO DE OBRA No. 045-2024",
        "CONSULTORIA PARA EL ESTUDIO DE IMPACTO AMBIENTAL DEL PROYECTO VIAL ANILLO DE BUCARAMANGA",
        "CONSULTORIA PARA LA FORMULACION DEL PLAN DE GESTION INTEGRAL DE RESIDUOS SOLIDOS",
    ],
    "COMPRAVENTA": [
        "COMPRAVENTA DE VEHICULO TIPO CAMIONETA DOBLE CABINA 4X4 PARA USO INSTITUCIONAL",
        "COMPRAVENTA DE MOBILIARIO Y DOTACION PARA LAS INSTITUCIONES EDUCATIVAS DEL MUNICIPIO",
        "COMPRAVENTA DE EQUIPOS MEDICOS PARA LOS CENTROS DE SALUD DE LA RED PUBLICA MUNICIPAL",
        "COMPRAVENTA DE MAQUINARIA PESADA PARA EL MANTENIMIENTO DE LAS VIAS DEL MUNICIPIO",
        "COMPRAVENTA DE EQUIPOS DE COMUNICACION PARA LA RED DE SEGURIDAD CIUDADANA",
    ],
    "ARRENDAMIENTO": [
        "ARRENDAMIENTO DE INMUEBLE UBICADO EN LA CALLE 36 No. 18-20 PARA FUNCIONAMIENTO DE LA SECRETARIA DE GOBIERNO",
        "ARRENDAMIENTO DE BODEGA PARA ALMACENAMIENTO DE MATERIALES DEL PROGRAMA DE INFRAESTRUCTURA",
        "ARRENDAMIENTO DE VEHICULOS PARA EL TRANSPORTE ESCOLAR DE LAS VEREDAS DEL MUNICIPIO",
        "ARRENDAMIENTO DE EQUIPOS DE IMPRESION Y FOTOCOPIADO PARA LAS DEPENDENCIAS MUNICIPALES",
        "ARRENDAMIENTO DE SALON PARA EVENTOS INSTITUCIONALES Y CAPACITACIONES",
    ],
    "INTERADMINISTRATIVO": [
        "AUNAR ESFUERZOS TECNICOS, ADMINISTRATIVOS Y FINANCIEROS PARA LA IMPLEMENTACION DEL PROGRAMA DE VIVIENDA GRATUITA",
        "COOPERACION PARA EL FORTALECIMIENTO DEL SISTEMA DE CIENCIA Y TECNOLOGIA DEL DEPARTAMENTO",
        "ARTICULACION INTERINSTITUCIONAL PARA LA EJECUCION DEL PLAN DE CONVIVENCIA Y SEGURIDAD CIUDADANA",
        "AUNAR ESFUERZOS PARA LA OPERACION Y MANTENIMIENTO DEL SISTEMA DE TRANSPORTE MASIVO METROLINEA",
        "COOPERACION PARA EL DESARROLLO DEL PROGRAMA DE ATENCION INTEGRAL A PRIMERA INFANCIA",
    ],
    "CONVENIO": [
        "CONVENIO DE ASOCIACION PARA EL FORTALECIMIENTO DE ORGANIZACIONES COMUNITARIAS EN ZONA RURAL",
        "CONVENIO INTERADMINISTRATIVO PARA LA GESTION DEL RIESGO Y ATENCION DE EMERGENCIAS",
        "CONVENIO DE COOPERACION PARA EL DESARROLLO DE PROGRAMAS DE INCLUSION SOCIAL",
        "CONVENIO PARA LA IMPLEMENTACION DE ESTRATEGIAS DE REACTIVACION ECONOMICA POST-PANDEMIA",
        "CONVENIO DE ASOCIACION PARA ACTIVIDADES DE CULTURA, RECREACION Y DEPORTE COMUNITARIO",
    ],
}

PLAZOS = [
    ("dos (2) meses", "2024-03-15", "2024-05-14"),
    ("tres (3) meses", "2024-01-20", "2024-04-19"),
    ("cuatro (4) meses", "2024-02-01", "2024-05-31"),
    ("cinco (5) meses", "2024-04-01", "2024-08-31"),
    ("seis (6) meses", "2024-01-15", "2024-07-14"),
    ("ocho (8) meses", "2024-03-01", "2024-10-31"),
    ("diez (10) meses", "2024-02-15", "2024-12-14"),
    ("doce (12) meses", "2024-01-01", "2024-12-31"),
    ("un (1) mes", "2024-06-01", "2024-06-30"),
    ("nueve (9) meses", "2024-03-10", "2024-12-09"),
]

VIGENCIAS = ["2024", "2025", "2023"]

VALORES_TEXTO = [
    ("DOCE MILLONES DE PESOS", "$12,000,000"),
    ("VEINTICINCO MILLONES TRESCIENTOS MIL PESOS", "$25,300,000"),
    ("CUARENTA Y DOS MILLONES SEISCIENTOS MIL PESOS", "$42,600,000"),
    ("OCHENTA Y SIETE MILLONES QUINIENTOS MIL PESOS", "$87,500,000"),
    ("CIENTO VEINTE MILLONES DE PESOS", "$120,000,000"),
    ("DOSCIENTOS CUARENTA Y CINCO MILLONES DE PESOS", "$245,000,000"),
    ("TRESCIENTOS SESENTA MILLONES OCHOCIENTOS MIL PESOS", "$360,800,000"),
    ("QUINIENTOS MILLONES DE PESOS", "$500,000,000"),
    ("SETECIENTOS CINCUENTA MILLONES DE PESOS", "$750,000,000"),
    ("MIL DOSCIENTOS MILLONES DE PESOS", "$1,200,000,000"),
    ("QUINCE MILLONES SETECIENTOS MIL PESOS", "$15,700,000"),
    ("TREINTA Y OCHO MILLONES CUATROCIENTOS MIL PESOS", "$38,400,000"),
    ("SESENTA Y TRES MILLONES NOVECIENTOS MIL PESOS", "$63,900,000"),
    ("NOVENTA Y UN MILLONES DOSCIENTOS MIL PESOS", "$91,200,000"),
    ("CIENTO SETENTA Y CINCO MILLONES DE PESOS", "$175,000,000"),
]

PREFIJOS = {
    "PRESTACION DE SERVICIOS": "PS",
    "OBRA": "OBR",
    "SUMINISTRO": "SUM",
    "CONSULTORIA": "CON",
    "COMPRAVENTA": "CV",
    "ARRENDAMIENTO": "ARR",
    "INTERADMINISTRATIVO": "INT",
    "CONVENIO": "CONV",
}


def generar_contrato(idx: int) -> dict:
    """Genera un contrato aleatorio con datos coherentes."""
    random.seed(idx * 31 + 7)  # reproducible

    tipo = TIPOS_CONTRATO[idx % len(TIPOS_CONTRATO)]
    prefijo = PREFIJOS[tipo]
    numero = f"{prefijo}-2024-{idx+1:03d}"

    entidad, nit_ent = random.choice(ENTIDADES)

    # 60% persona jurídica, 40% natural
    if random.random() < 0.4:
        persona = "Natural"
        nombre, cedula, ciudad = random.choice(CONTRATISTAS_NATURAL)
        id_text = f"identificada con cedula de ciudadania No. {cedula} expedida en {ciudad}"
    else:
        persona = "Jurídica"
        nombre, nit, ciudad = random.choice(CONTRATISTAS_JURIDICA)
        id_text = f"con NIT {nit}, domiciliada en {ciudad}"

    objeto = random.choice(OBJETOS[tipo])
    plazo_texto, fecha_inicio, fecha_fin = random.choice(PLAZOS)
    vigencia = random.choice(VIGENCIAS)
    valor_texto, valor_num = random.choice(VALORES_TEXTO)

    # Simular variación en formato OCR
    variaciones = [
        # Formato estándar
        lambda: f"""
        CONTRATO DE {tipo} No. {numero}
        FECHA: {ciudad}, {random.randint(1,28)} de {random.choice(['enero','febrero','marzo','abril','mayo','junio'])} de {vigencia}
        
        Entre los suscritos, de una parte {entidad}, NIT {nit_ent}, representada 
        legalmente por su representante legal, y de otra parte {nombre}, {id_text}, 
        quien para efectos del presente contrato se denominara EL CONTRATISTA.
        
        CLAUSULA PRIMERA - OBJETO: {objeto}.
        
        CLAUSULA SEGUNDA - VALOR: El valor total del presente contrato es de 
        {valor_texto} ({valor_num}) M/CTE, incluidos todos los impuestos.
        
        CLAUSULA TERCERA - PLAZO: El plazo de ejecucion sera de {plazo_texto}, 
        contados a partir del {fecha_inicio}.
        
        CLAUSULA CUARTA - VIGENCIA: La vigencia del presente contrato 
        corresponde a la vigencia fiscal del año {vigencia}.
        """,
        # Formato con ruido OCR
        lambda: f"""
        C0NTRAT0 DE {tipo} N°. {numero}
        
        {entidad} - NIT: {nit_ent}
        
        CONTRATISTA: {nombre}
        {id_text}
        
        0BJETO: {objeto}
        
        VAL0R TOTAL: {valor_texto} ({valor_num}) MCTE
        impuestos incluidos
        
        PLAZ0: {plazo_texto} a partir del {fecha_inicio}
        VIGENCIA FISCAL: {vigencia}
        TIPO PERSONA: {persona}
        """,
        # Formato tabla (como a veces sale del OCR)
        lambda: f"""
        ═══════════════════════════════════════════════
        CONTRATO No.: {numero}
        TIPO: {tipo}
        ═══════════════════════════════════════════════
        
        ENTIDAD CONTRATANTE: {entidad}
        NIT ENTIDAD: {nit_ent}
        
        DATOS DEL CONTRATISTA:
        Nombre/Razón Social: {nombre}
        {id_text}
        Tipo de Persona: {persona}
        
        ───────────────────────────────────────────────
        OBJETO DEL CONTRATO:
        {objeto}
        ───────────────────────────────────────────────
        
        CONDICIONES FINANCIERAS:
        Valor Total: {valor_num}
        Valor en letras: {valor_texto} M/CTE
        
        CONDICIONES DE EJECUCIÓN:
        Fecha de inicio: {fecha_inicio}
        Plazo: {plazo_texto}
        Vigencia Fiscal: {vigencia}
        ═══════════════════════════════════════════════
        """,
    ]

    text = random.choice(variaciones)()

    return {
        "id": f"C{idx+1:03d}-{prefijo}",
        "raw_text": text.strip(),
        # Datos esperados para comparación
        "_expected": {
            "numero_contrato": numero,
            "tipo_contrato": tipo.title() if tipo != "PRESTACION DE SERVICIOS" else "Prestación de servicios",
            "nombre_contratista": nombre.title(),
            "tipo_persona": persona,
            "vigencia": vigencia,
            "valor": valor_num,
        }
    }


def print_resultado(idx, item, expected):
    """Imprime los datos extraídos de un contrato vs esperados."""
    status = "✓" if item["success"] else "✗"
    cached = "CACHE" if item.get("cached") else ""

    print(f"\n  {'─'*66}")
    print(f"  [{idx+1:02d}] {item['id']}  {status}  {cached}  ({item.get('processing_time_ms', 0)/1000:.1f}s)")
    print(f"  {'─'*66}")

    if not item["success"]:
        print(f"       ERROR: {item.get('error', 'desconocido')}")
        return 0

    data = item.get("data", {})
    campos_ok = 0
    campos_total = 9

    fields = [
        ("numero_contrato",      "Nro Contrato"),
        ("objeto_contrato",      "Objeto       "),
        ("nombre_contratista",   "Contratista  "),
        ("vigencia",             "Vigencia     "),
        ("anno",                 "Año          "),
        ("fecha_inicio",         "Fch Inicio   "),
        ("valor",                "Valor        "),
        ("tipo_persona",         "Tipo Persona "),
        ("tipo_contrato",        "Tipo Contrato"),
    ]

    for key, label in fields:
        val = data.get(key)
        display = str(val) if val is not None else "—"
        # Truncar si muy largo
        if len(display) > 55:
            display = display[:52] + "..."
        
        # Marcar si coincide con esperado
        mark = ""
        if key in expected:
            exp = expected[key]
            if val and exp.lower() in str(val).lower():
                mark = " ✓"
                campos_ok += 1
            else:
                mark = f" ≠ (esp: {exp[:30]})"
        elif val is not None:
            campos_ok += 1

        print(f"       {label}: {display}{mark}")

    return campos_ok


def run_test_50():
    print("=" * 70)
    print("  TEST 50 CONTRATOS — Resultados Detallados")
    print("=" * 70)

    # Health check
    try:
        r = httpx.get(f"{BASE}/health", timeout=10)
        health = r.json()
        print(f"\n  Ollama:    {health['status']}")
        print(f"  Modelo:    {health['default_model']}")
        print(f"  Paralelo:  {health['batch_config']['max_parallel']}")
    except Exception as e:
        print(f"\n  ERROR: Servidor no disponible - {e}")
        sys.exit(1)

    # Limpiar cache
    httpx.delete(f"{BASE}/cache", headers=HEADERS, timeout=10)
    print(f"  Cache:     limpiado")

    # Generar 50 contratos
    print(f"\n  Generando 50 contratos...")
    contratos = [generar_contrato(i) for i in range(50)]

    # Contar tipos
    tipos_count = {}
    for c in contratos:
        e = c["_expected"]
        t = e.get("tipo_contrato", "?")
        tipos_count[t] = tipos_count.get(t, 0) + 1
    
    print(f"  Distribución por tipo:")
    for t, n in sorted(tipos_count.items()):
        print(f"    {t}: {n}")

    # Preparar batch
    batch_items = [{"id": c["id"], "raw_text": c["raw_text"]} for c in contratos]
    body = {"contracts": batch_items}

    # Enviar
    print(f"\n{'─'*70}")
    print(f"  ENVIANDO BATCH DE 50 CONTRATOS...")
    print(f"  (esto puede tardar 20-40 min con paralelismo=3)")
    print(f"{'─'*70}")

    start = time.time()
    try:
        r = httpx.post(
            f"{BASE}/api/v1/extract/batch",
            json=body,
            headers=HEADERS,
            timeout=TIMEOUT,
        )
    except httpx.ReadTimeout:
        elapsed = time.time() - start
        print(f"\n  TIMEOUT después de {elapsed/60:.1f} min")
        sys.exit(1)

    elapsed = time.time() - start
    result = r.json()

    # Resumen general
    print(f"\n{'='*70}")
    print(f"  RESUMEN GENERAL")
    print(f"{'='*70}")
    print(f"  Status HTTP:    {r.status_code}")
    print(f"  Total:          {result['total']}")
    print(f"  Exitosos:       {result['successful']}")
    print(f"  Fallidos:       {result['failed']}")
    print(f"  Cache hits:     {result['cached']}")
    print(f"  Modelo:         {result['model_used']}")
    print(f"  Tiempo total:   {elapsed:.1f}s ({elapsed/60:.1f} min)")
    
    if result['successful'] > 0:
        avg = elapsed / result['successful']
        print(f"  Promedio:       {avg:.1f}s por contrato")
        print(f"  Throughput:     {result['successful']/elapsed:.3f} contratos/seg")
        print(f"                  {result['successful']/elapsed*60:.1f} contratos/min")

    # Resultados detallados
    print(f"\n{'='*70}")
    print(f"  RESULTADOS POR CONTRATO")
    print(f"{'='*70}")

    total_campos_ok = 0
    resultados = result.get("results", [])

    # Mapear expected por id
    expected_map = {c["id"]: c["_expected"] for c in contratos}

    for i, item in enumerate(resultados):
        expected = expected_map.get(item["id"], {})
        campos_ok = print_resultado(i, item, expected)
        total_campos_ok += campos_ok

    # Tabla resumen tiempos
    print(f"\n{'='*70}")
    print(f"  TABLA DE TIEMPOS")
    print(f"{'='*70}")
    print(f"  {'ID':<16} {'Tipo':<28} {'Tiempo':>8} {'Status':>8}")
    print(f"  {'─'*16} {'─'*28} {'─'*8} {'─'*8}")
    
    tiempos = []
    for item in resultados:
        t = item.get("processing_time_ms", 0) / 1000
        tiempos.append(t)
        tipo = item.get("data", {}).get("tipo_contrato", "—") if item["success"] else "ERROR"
        if tipo and len(tipo) > 27:
            tipo = tipo[:24] + "..."
        status = "✓" if item["success"] else "✗"
        cached = " (C)" if item.get("cached") else ""
        print(f"  {item['id']:<16} {tipo or '—':<28} {t:>7.1f}s {status:>4}{cached}")

    if tiempos:
        tiempos_sin_cache = [t for t, item in zip(tiempos, resultados) if not item.get("cached")]
        print(f"\n  Tiempo mínimo:  {min(tiempos):.1f}s")
        print(f"  Tiempo máximo:  {max(tiempos):.1f}s")
        if tiempos_sin_cache:
            print(f"  Promedio (sin cache): {sum(tiempos_sin_cache)/len(tiempos_sin_cache):.1f}s")

    # Estadísticas de precisión
    print(f"\n{'='*70}")
    print(f"  PRECISIÓN DE EXTRACCIÓN")
    print(f"{'='*70}")
    print(f"  Campos verificables correctos: {total_campos_ok}")
    print(f"  Contratos exitosos: {result['successful']}/50")

    # Cache stats
    try:
        r2 = httpx.get(f"{BASE}/cache/stats", timeout=10)
        stats = r2.json()
        print(f"\n  Cache size:   {stats['size']}")
        print(f"  Cache hits:   {stats['hits']}")
        print(f"  Cache misses: {stats['misses']}")
        print(f"  Hit rate:     {stats['hit_rate']}")
    except:
        pass

    # Guardar JSON completo
    output_file = "results_50.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({
            "summary": {
                "total": result["total"],
                "successful": result["successful"],
                "failed": result["failed"],
                "cached": result["cached"],
                "model": result["model_used"],
                "elapsed_seconds": round(elapsed, 1),
                "avg_seconds_per_contract": round(elapsed / max(result["successful"], 1), 1),
            },
            "results": resultados,
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n  Resultados guardados en: {output_file}")

    # Proyecciones
    if result["successful"] > 0:
        avg_real = elapsed / result["successful"]
        parallel = health["batch_config"]["max_parallel"]
        print(f"\n{'='*70}")
        print(f"  PROYECCIONES (basadas en datos reales)")
        print(f"{'='*70}")
        print(f"  Promedio real:  {avg_real:.1f}s por contrato")
        print(f"  Paralelismo:    {parallel}")
        for n in [100, 200, 400, 1000]:
            est = (n / parallel) * avg_real
            if est >= 3600:
                print(f"  {n:>5} contratos: ~{est/3600:.1f} horas")
            else:
                print(f"  {n:>5} contratos: ~{est/60:.0f} min")

    print(f"\n{'='*70}")
    print(f"  TEST COMPLETADO")
    print(f"{'='*70}")


if __name__ == "__main__":
    run_test_50()
