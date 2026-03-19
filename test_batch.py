"""Script de prueba: batch con 3 contratos (2 únicos + 1 duplicado para cache)."""

import httpx
import json
import time

BASE = "http://localhost:8000"
HEADERS = {"X-API-Key": "sk-iaocr-dev-001"}

# ─── Health ───
print("=== HEALTH ===")
r = httpx.get(f"{BASE}/health")
print(json.dumps(r.json(), indent=2, ensure_ascii=False))

# ─── Batch ───
print("\n=== BATCH (3 contratos en paralelo) ===")

contrato_1_texto = (
    "CONTRATO DE PRESTACION DE SERVICIOS No. 2024-0456. "
    "Entre la ALCALDIA MUNICIPAL DE BUCARAMANGA, NIT 890.201.222-1, "
    "y el contratista JUAN CARLOS MARTINEZ LOPEZ, identificado con "
    "cedula de ciudadania No. 1.098.765.432, persona natural, se celebra "
    "el presente contrato cuyo objeto es: PRESTACION DE SERVICIOS "
    "PROFESIONALES PARA EL APOYO EN LA GESTION ADMINISTRATIVA DEL AREA "
    "DE SISTEMAS. El valor del presente contrato es de TREINTA Y CINCO "
    "MILLONES DE PESOS ($35,000,000) M/CTE. La vigencia del contrato "
    "corresponde al ano 2024, con fecha de inicio el 15 de febrero de 2024 "
    "y un plazo de ejecucion de seis (6) meses."
)

contrato_2_texto = (
    "CONTRATO DE OBRA No. LP-003-2025. La GOBERNACION DE SANTANDER, "
    "NIT 890.201.001-5, celebra contrato con la empresa CONSTRUCTORA "
    "ANDINA S.A.S, NIT 900.123.456-7, cuyo objeto es: CONSTRUCCION DE "
    "LA VIA TERCIARIA QUE COMUNICA EL MUNICIPIO DE SAN GIL CON LA VEREDA "
    "EL PORVENIR, POR UN VALOR DE OCHOCIENTOS MILLONES DE PESOS "
    "($800,000,000). Vigencia 2025, fecha de inicio 1 de marzo de 2025, "
    "plazo 12 meses."
)

body = {
    "contracts": [
        {"id": "contrato-1", "raw_text": contrato_1_texto},
        {"id": "contrato-2", "raw_text": contrato_2_texto},
        {"id": "contrato-3-cache", "raw_text": contrato_1_texto},  # Duplicado = cache
    ]
}

print(f"Enviando {len(body['contracts'])} contratos (contrato-1 y contrato-3 son iguales = cache)...")
start = time.time()
r = httpx.post(
    f"{BASE}/api/v1/extract/batch",
    json=body,
    headers=HEADERS,
    timeout=1200,
)
elapsed = time.time() - start
print(f"Respuesta en {elapsed:.1f}s - Status: {r.status_code}")
print(json.dumps(r.json(), indent=2, ensure_ascii=False))

# ─── Cache stats ───
print("\n=== CACHE STATS ===")
r = httpx.get(f"{BASE}/cache/stats")
print(json.dumps(r.json(), indent=2, ensure_ascii=False))
