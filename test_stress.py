"""
Test de estrés – Fuerza al máximo la aplicación.

Envía 15 contratos en batch:
- 10 contratos únicos (diversos tipos, textos largos tipo OCR)
- 5 duplicados (para validar cache)

Mide: tiempo total, por contrato, cache hits, paralelismo efectivo.
"""

import httpx
import json
import time
import sys

BASE = "http://localhost:8000"
HEADERS = {"X-API-Key": "sk-iaocr-dev-001"}
TIMEOUT = 2400  # 40 min max

# ─── 10 contratos únicos (simula texto OCR real con ruido) ───

CONTRATOS = [
    {
        "id": "PS-001",
        "raw_text": """
        CONTRATO DE PRESTACION DE SERVICIOS No. PS-2024-001
        FECHA: Bucaramanga, 15 de enero de 2024
        
        Entre los suscritos, de una parte la ALCALDIA MUNICIPAL DE BUCARAMANGA, 
        NIT 890.201.222-1, representada legalmente por el Alcalde Municipal, 
        doctor JAIME ANDRES BELTRAN PEREZ, y de otra parte MARIA FERNANDA 
        RODRIGUEZ SILVA, mayor de edad, identificada con cedula de ciudadania 
        No. 63.456.789 expedida en Bucaramanga, quien para efectos del presente 
        contrato se denominara EL CONTRATISTA, se ha convenido celebrar el 
        presente contrato de PRESTACION DE SERVICIOS, previas las siguientes 
        consideraciones y clausulas:
        
        CLAUSULA PRIMERA - OBJETO: EL CONTRATISTA se obliga para con EL MUNICIPIO 
        a prestar sus servicios profesionales como ABOGADA ESPECIALISTA para 
        APOYAR LA GESTION JURIDICA EN EL AREA DE CONTRATACION DE LA SECRETARIA 
        GENERAL DEL MUNICIPIO DE BUCARAMANGA.
        
        CLAUSULA SEGUNDA - VALOR: El valor total del presente contrato es de 
        CUARENTA Y DOS MILLONES SEISCIENTOS MIL PESOS ($42,600,000) M/CTE, 
        incluidos todos los impuestos, tasas y contribuciones.
        
        CLAUSULA TERCERA - PLAZO: El plazo de ejecucion del contrato sera de 
        seis (6) meses, contados a partir del acta de inicio.
        
        CLAUSULA CUARTA - VIGENCIA: La vigencia del presente contrato corresponde 
        al ano fiscal 2024.
        """
    },
    {
        "id": "OBR-002",
        "raw_text": """
        CONTRATO DE OBRA PUBLICA No. LP-2025-0089
        
        Entre la GOBERNACION DE SANTANDER, identificada con NIT 890.201.001-5, 
        representada por el Gobernador JUVENAL DIAZ MATEUS, y la firma 
        INGENIEROS ASOCIADOS DEL ORIENTE S.A.S., identificada con NIT 
        900.456.789-2, representada legalmente por CARLOS EDUARDO PINZON 
        MENDOZA, se celebra el presente CONTRATO DE OBRA cuyo objeto y 
        condiciones se establecen a continuacion:
        
        OBJETO: CONSTRUCCION, MEJORAMIENTO Y REHABILITACION DE LA VIA QUE 
        COMUNICA LOS MUNICIPIOS DE BARRANCABERMEJA Y SAN VICENTE DE CHUCURI, 
        EN EL DEPARTAMENTO DE SANTANDER, INCLUIDA LA CONSTRUCCION DE 3 PUENTES 
        VEHICULARES.
        
        VALOR DEL CONTRATO: MIL DOSCIENTOS MILLONES DE PESOS ($1,200,000,000) 
        M/CTE, incluido IVA y AIU.
        
        PLAZO DE EJECUCION: Dieciocho (18) meses contados a partir de la 
        suscripcion del acta de inicio. Vigencia fiscal 2025.
        Fecha de inicio: 01 de abril de 2025.
        """
    },
    {
        "id": "SUM-003",
        "raw_text": """
        CONTRATO DE SUMINISTRO No. SA-2024-0234
        
        De una parte, el HOSPITAL UNIVERSITARIO DE SANTANDER E.S.E., NIT 
        890.203.222-4, y de otra parte DISTRIBUIDORA MEDICA NACIONAL LTDA, 
        NIT 800.111.222-3, representada por ANGELA PATRICIA DUARTE VARGAS, 
        han acordado celebrar el presente contrato de suministro bajo las 
        siguientes clausulas:
        
        PRIMERO - OBJETO: Suministro de MEDICAMENTOS, DISPOSITIVOS MEDICOS E 
        INSUMOS HOSPITALARIOS para la atencion de pacientes en las areas de 
        urgencias, hospitalizacion y cirugia del Hospital Universitario de 
        Santander, de acuerdo con las especificaciones tecnicas del pliego 
        de condiciones.
        
        SEGUNDO - VALOR: El presente contrato tiene un valor de TRESCIENTOS 
        CINCUENTA MILLONES DE PESOS ($350,000,000) M/CTE.
        
        TERCERO - PLAZO: El plazo de ejecucion es de doce (12) meses. 
        Vigencia 2024. Fecha inicio: 1 de junio de 2024.
        
        La DISTRIBUIDORA MEDICA NACIONAL LTDA se identifica como persona juridica.
        """
    },
    {
        "id": "CON-004",
        "raw_text": """
        CONTRATO DE CONSULTORIA No. CM-2025-0012
        Bucaramanga, 20 de febrero de 2025
        
        La EMPRESA DE ACUEDUCTO METROPOLITANO DE BUCARAMANGA S.A. E.S.P., 
        NIT 890.201.900-1, celebra contrato de consultoria con la firma 
        CONSULTORES AMBIENTALES DEL ORIENTE S.A., NIT 900.789.012-5, 
        representada por el ingeniero ROBERTO ANDRES MANTILLA GARCIA.
        
        OBJETO: ELABORACION DE LOS ESTUDIOS Y DISENOS PARA LA AMPLIACION 
        DEL SISTEMA DE ALCANTARILLADO PLUVIAL EN LA ZONA NORTE DEL AREA 
        METROPOLITANA DE BUCARAMANGA, INCLUYENDO ESTUDIOS TOPOGRAFICOS, 
        GEOTECNICOS, HIDROLOGICOS Y AMBIENTALES.
        
        VALOR: DOSCIENTOS OCHENTA MILLONES DE PESOS ($280,000,000).
        
        PLAZO: Ocho (8) meses. Vigencia 2025. 
        Fecha de inicio: 15 de marzo de 2025.
        """
    },
    {
        "id": "ARR-005",
        "raw_text": """
        CONTRATO DE ARRENDAMIENTO No. CD-2024-0567
        
        Entre el FONDO TERRITORIAL DE PENSIONES DEL MUNICIPIO DE 
        BUCARAMANGA, NIT 890.205.333-7, representado por DIANA MARCELA 
        ORTIZ LEON, y el senor PEDRO ANTONIO GOMEZ CASTILLO, identificado 
        con cedula de ciudadania No. 91.234.567 de Bucaramanga, persona 
        natural, propietario del inmueble ubicado en la Calle 36 No. 15-42, 
        Barrio Cabecera del Llano.
        
        OBJETO: ARRENDAMIENTO DE UN INMUEBLE DE USO COMERCIAL PARA EL 
        FUNCIONAMIENTO DE LAS OFICINAS DE ATENCION AL CIUDADANO DEL FONDO 
        TERRITORIAL DE PENSIONES.
        
        VALOR: VEINTICUATRO MILLONES DE PESOS ($24,000,000) anuales, 
        pagaderos en mensualidades de DOS MILLONES DE PESOS ($2,000,000).
        PLAZO: Un (1) ano. Vigencia 2024. Inicio: 1 de febrero de 2024.
        """
    },
    {
        "id": "INT-006",
        "raw_text": """
        CONVENIO INTERADMINISTRATIVO No. CIA-2025-0003
        
        Celebrado entre la GOBERNACION DE SANTANDER, NIT 890.201.001-5 y 
        la UNIVERSIDAD INDUSTRIAL DE SANTANDER - UIS, NIT 890.201.213-4, 
        representada por el Rector HERNANDO AUGUSTO PARRA NIETO.
        
        OBJETO: AUNAR ESFUERZOS TECNICOS, ADMINISTRATIVOS Y FINANCIEROS 
        PARA LA IMPLEMENTACION DE PROGRAMAS DE FORMACION Y CAPACITACION 
        EN TECNOLOGIAS DE LA INFORMACION DIRIGIDOS A FUNCIONARIOS PUBLICOS 
        DEL DEPARTAMENTO DE SANTANDER.
        
        VALOR: El aporte total del convenio asciende a QUINIENTOS MILLONES 
        DE PESOS ($500,000,000), de los cuales la Gobernacion aporta 
        $300,000,000 y la UIS aporta $200,000,000 en especie.
        
        PLAZO: Diez (10) meses. 2025. Inicio: 1 de mayo de 2025.
        """
    },
    {
        "id": "CV-007",
        "raw_text": """
        CONTRATO DE COMPRAVENTA No. MC-2024-0891
        
        Entre la POLICIA NACIONAL - DEPARTAMENTO DE POLICIA DE SANTANDER, 
        NIT 899.999.011-2, y la empresa TECNOLOGIA Y SEGURIDAD S.A.S., 
        NIT 901.234.567-8, representada por JUAN PABLO HERRERA ACOSTA, 
        se celebra el presente contrato.
        
        OBJETO: ADQUISICION DE EQUIPOS DE COMPUTO, SERVIDORES Y ELEMENTOS 
        TECNOLOGICOS PARA LA MODERNIZACION DE LAS ESTACIONES DE POLICIA 
        DEL AREA METROPOLITANA DE BUCARAMANGA SEGUN FICHA TECNICA ANEXA.
        
        VALOR TOTAL: CIENTO SESENTA Y CINCO MILLONES DE PESOS ($165,000,000).
        
        PLAZO DE ENTREGA: Noventa (90) dias calendario. Vigencia 2024.
        Fecha suscripcion: 10 de agosto de 2024.
        """
    },
    {
        "id": "PS-008-OCR",
        "raw_text": """
        C O N T R A T O  DE  PRESTAC1ON  DE  SERV1CIOS  No.  2024-1234
        
        Bucar amanga,  01  de  Marzo  de 2O24
        
        Entre  la  SECRETAR1A  DE  EDUCACION  DE  BUCARAMANGA,  N1T  890.2O1.222-1,
        y  la  senora  LUZ  MARINA  SANDOVAL  PEREZ,  identificada  con  c.c.
        No.  28.345.678  de  San  Gil,  persona  natural,  se  celebra  el
        presente  contrato  de  prestacion  de  servicios.
        
        OBJ ETO:  PRESTAR  SERVICIOS  DE  APOYO  A  LA  GESTION  COMO  AUXILIAR
        ADMIN1STRATIVA  EN  LA  SECRETARIA  DE  EDUCAC1ON  MUNICIPAL,  EN  EL
        PROGRAMA  DE  AL1MENTACION  ESCOLAR  PAE.
        
        V ALOR:  D1ECIOCHO  MILLONES  DE  PESOS  ($18.000.OO0)  M/CTE.
        
        PLAZO:  Diez  (10)  meses.  V1gencia  2024.
        """
    },
    {
        "id": "OBR-009",
        "raw_text": """
        CONTRATO DE OBRA No. LP-2024-0045
        
        La ALCALDIA MUNICIPAL DE FLORIDABLANCA, NIT 890.205.000-6, 
        representada por el Alcalde MIGUEL ANGEL MORENO PARRA, y la 
        firma CONSTRUCCIONES TITAN S.A., NIT 860.045.678-9, representada 
        por JOSE LUIS RAMIREZ TORRES, celebran contrato de obra.
        
        OBJETO: CONSTRUCCION Y DOTACION DEL CENTRO DE DESARROLLO INFANTIL 
        INTEGRAL EN EL BARRIO LAGOS DEL CACIQUE DEL MUNICIPIO DE 
        FLORIDABLANCA, DE ACUERDO CON LOS PLANOS, ESPECIFICACIONES TECNICAS 
        Y PRESUPUESTO OFICIAL.
        
        VALOR: NOVECIENTOS CINCUENTA MILLONES DE PESOS ($950,000,000) M/CTE.
        
        PLAZO: Catorce (14) meses. Vigencia 2024. 
        Inicio: 15 de abril de 2024.
        """
    },
    {
        "id": "CONV-010",
        "raw_text": """
        CONVENIO DE ASOCIACION No. CA-2025-0007
        
        Entre el MUNICIPIO DE GIRON, NIT 890.204.000-4, representado por 
        la Alcaldesa PAOLA ANDREA CACERES DURAN, y la FUNDACION PARA 
        EL DESARROLLO SOCIAL DEL ORIENTE COLOMBIANO, NIT 900.567.890-1, 
        representada por MARTHA CECILIA RUEDA BLANCO, persona juridica.
        
        OBJETO: IMPLEMENTACION DE ESTRATEGIAS PARA EL FORTALECIMIENTO 
        DE LA PARTICIPACION CIUDADANA Y EL DESARROLLO COMUNITARIO EN 
        LAS COMUNAS 4 Y 5 DEL MUNICIPIO DE GIRON, INCLUYENDO TALLERES 
        DE LIDERAZGO, EMPRENDIMIENTO Y CONVIVENCIA CIUDADANA.
        
        VALOR: SETENTA Y CINCO MILLONES DE PESOS ($75,000,000).
        
        PLAZO: Seis (6) meses. 2025. Inicio: 10 de junio de 2025.
        """
    },
]

# ─── Main ───

def run_stress_test():
    print("=" * 70)
    print("  TEST DE ESTRÉS — IaOCR Extracción de Contratos")
    print("=" * 70)
    
    # Health check
    try:
        r = httpx.get(f"{BASE}/health", timeout=10)
        health = r.json()
        print(f"\n  Ollama:    {health['status']}")
        print(f"  Modelo:    {health['default_model']}")
        print(f"  Paralelo:  {health['batch_config']['max_parallel']}")
    except Exception as e:
        print(f"\n  ERROR: No se puede conectar al servidor: {e}")
        sys.exit(1)

    # Limpiar cache
    httpx.delete(f"{BASE}/cache", headers=HEADERS, timeout=10)
    print(f"  Cache:     limpiado")

    # ─── FASE 1: Batch de 10 contratos únicos ───
    print("\n" + "─" * 70)
    print("  FASE 1: 10 contratos únicos en paralelo")
    print("─" * 70)
    
    body_10 = {"contracts": CONTRATOS[:10]}
    
    start = time.time()
    r = httpx.post(
        f"{BASE}/api/v1/extract/batch",
        json=body_10,
        headers=HEADERS,
        timeout=TIMEOUT,
    )
    elapsed_fase1 = time.time() - start
    
    result_1 = r.json()
    
    print(f"\n  Status:     {r.status_code}")
    print(f"  Total:      {result_1['total']} contratos")
    print(f"  Exitosos:   {result_1['successful']}")
    print(f"  Fallidos:   {result_1['failed']}")
    print(f"  Cache hits: {result_1['cached']}")
    print(f"  Tiempo:     {elapsed_fase1:.1f}s ({elapsed_fase1/60:.1f} min)")
    
    if result_1["successful"] > 0:
        times = [r["processing_time_ms"] / 1000 for r in result_1["results"] if r["success"]]
        print(f"\n  Tiempo por contrato:")
        print(f"    Mínimo:   {min(times):.1f}s")
        print(f"    Máximo:   {max(times):.1f}s")
        print(f"    Promedio: {sum(times)/len(times):.1f}s")
        
        # Throughput efectivo (contratos procesados / tiempo real)
        throughput = result_1["successful"] / elapsed_fase1
        print(f"\n  Throughput: {throughput:.2f} contratos/seg")
        print(f"              {throughput * 60:.1f} contratos/min")
    
    # Detalle por contrato
    print(f"\n  {'ID':<16} {'Tipo Contrato':<28} {'Tiempo':>8} {'Status':>8}")
    print(f"  {'─'*16} {'─'*28} {'─'*8} {'─'*8}")
    for item in result_1["results"]:
        t = f"{item['processing_time_ms']/1000:.1f}s"
        status = "✓" if item["success"] else "✗"
        tipo = "—"
        if item.get("data") and isinstance(item["data"], dict):
            tipo = item["data"].get("tipo_contrato") or "—"
        elif item.get("data") and hasattr(item["data"], "tipo_contrato"):
            tipo = item["data"].tipo_contrato or "—"
        print(f"  {item['id']:<16} {tipo:<28} {t:>8} {status:>8}")

    # ─── FASE 2: Batch de 5 duplicados (test de cache) ───
    print("\n" + "─" * 70)
    print("  FASE 2: 5 contratos duplicados (deben venir de cache)")
    print("─" * 70)
    
    body_cache = {
        "contracts": [
            {"id": f"cache-{c['id']}", "raw_text": c["raw_text"]}
            for c in CONTRATOS[:5]
        ]
    }
    
    start = time.time()
    r = httpx.post(
        f"{BASE}/api/v1/extract/batch",
        json=body_cache,
        headers=HEADERS,
        timeout=TIMEOUT,
    )
    elapsed_fase2 = time.time() - start
    
    result_2 = r.json()
    
    print(f"\n  Status:     {r.status_code}")
    print(f"  Total:      {result_2['total']}")
    print(f"  Cache hits: {result_2['cached']}")
    print(f"  Tiempo:     {elapsed_fase2:.1f}s")
    
    if result_2["cached"] > 0:
        print(f"  Speedup:    {elapsed_fase1/max(elapsed_fase2, 0.001):.0f}x más rápido con cache")

    # ─── FASE 3: Single request (comparación) ───
    print("\n" + "─" * 70)
    print("  FASE 3: 1 contrato individual (referencia de tiempo)")
    print("─" * 70)
    
    body_single = {"raw_text": CONTRATOS[0]["raw_text"]}
    
    start = time.time()
    r = httpx.post(
        f"{BASE}/api/v1/extract",
        json=body_single,
        headers=HEADERS,
        timeout=TIMEOUT,
    )
    elapsed_fase3 = time.time() - start
    
    result_3 = r.json()
    print(f"\n  Status:  {r.status_code}")
    print(f"  Tiempo:  {elapsed_fase3:.1f}s")
    print(f"  Cache:   {'sí' if elapsed_fase3 < 2 else 'no'}")

    # ─── Cache stats final ───
    print("\n" + "─" * 70)
    print("  ESTADÍSTICAS FINALES")
    print("─" * 70)
    
    r = httpx.get(f"{BASE}/cache/stats", timeout=10)
    stats = r.json()
    
    print(f"\n  Cache size:     {stats['size']} entradas")
    print(f"  Cache hits:     {stats['hits']}")
    print(f"  Cache misses:   {stats['misses']}")
    print(f"  Hit rate:       {stats['hit_rate']}")
    
    total_contratos = result_1["successful"] + result_2["successful"]
    total_time = elapsed_fase1 + elapsed_fase2
    
    print(f"\n  Contratos procesados: {total_contratos}")
    print(f"  Tiempo total:         {total_time:.1f}s ({total_time/60:.1f} min)")
    print(f"  Throughput global:    {total_contratos/total_time:.2f} contratos/seg")
    
    # Proyección para 100 y 400 contratos
    if result_1["successful"] > 0:
        avg_time = elapsed_fase1 / result_1["successful"]
        parallel = health["batch_config"]["max_parallel"]
        
        print(f"\n  ─── PROYECCIONES ───")
        print(f"  Promedio real:        {avg_time:.1f}s por contrato")
        print(f"  Paralelismo:          {parallel} simultáneos")
        
        for n in [50, 100, 200, 400]:
            # Con cache 0%, batches de max_items
            est_time = (n / parallel) * avg_time
            est_min = est_time / 60
            est_hours = est_min / 60
            if est_hours >= 1:
                print(f"  {n:>4} contratos:  ~{est_hours:.1f} horas")
            else:
                print(f"  {n:>4} contratos:  ~{est_min:.0f} min")
    
    print("\n" + "=" * 70)
    print("  TEST COMPLETADO")
    print("=" * 70)


if __name__ == "__main__":
    run_stress_test()
