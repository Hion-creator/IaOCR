# IaOCR — Extracción Inteligente de Contratos

Backend con **IA** (Ollama local o cloud) que extrae datos estructurados de contratos públicos colombianos a partir de texto OCR.

**Concepto:** Cada documento OCR = **UN solo contrato**. El sistema filtra automáticamente el ruido (hojas de vida, experiencia laboral, cuotas mensuales repetitivas) y extrae los 9 campos del contrato principal.

**Procesamiento configurable**: local en tu servidor o cloud con Ollama API.

---

## Requisitos Previos

| Componente | Versión mínima |
|---|---|
| **Python** | 3.12+ |
| **Ollama** | 0.16+ |
| **RAM** | 16 GB (recomendado 32 GB) |
| **GPU** *(opcional)* | NVIDIA con ≥8 GB VRAM para aceleración |

### Instalar Ollama

```bash
# Windows — descargar desde:
https://ollama.com/download

# Linux
curl -fsSL https://ollama.com/install.sh | sh
```

Verificar instalación:

```bash
ollama --version
```

### Descargar el modelo de IA

```bash
ollama pull qwen3:14b
```

> El modelo pesa ~9.3 GB. Si tienes menos de 16 GB de RAM, usa `qwen3:8b` en su lugar.

---

## Instalación

### 1. Clonar el repositorio

```bash
git clone <URL_DEL_REPO>
cd IaOCR
```

### 2. Crear entorno virtual

```bash
python -m venv .venv
```

Activar:

```powershell
# Windows (PowerShell)
.\.venv\Scripts\Activate.ps1

# Linux / macOS
source .venv/bin/activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno

Crear un archivo `.env` en la raíz del proyecto:

```env
OLLAMA_BASE_URL=https://ollama.com
OLLAMA_MODEL=qwen3.5:cloud
OLLAMA_API_KEY=tu-api-key-ollama-cloud
OLLAMA_TIMEOUT=600
OLLAMA_TEMPERATURE=0.1
OLLAMA_NUM_CTX=4096
PREPROCESS_MAX_CHARS=10000
API_KEYS_RAW=sk-tu-clave-aqui-001,sk-tu-clave-aqui-002
```

| Variable | Descripción | Default |
|---|---|---|
| `OLLAMA_BASE_URL` | URL de Ollama (local o cloud) | `https://ollama.com` |
| `OLLAMA_MODEL` | Modelo a utilizar | `qwen3.5:cloud` |
| `OLLAMA_API_KEY` | API key para Ollama Cloud (Bearer) | *(vacío)* |
| `OLLAMA_TIMEOUT` | Timeout por request (segundos) | `600` |
| `OLLAMA_TEMPERATURE` | Creatividad del modelo (0.0–1.0) | `0.1` |
| `OLLAMA_NUM_CTX` | Ventana de contexto (tokens) | `4096` |
| `PREPROCESS_MAX_CHARS` | Máximo chars del texto preparado | `10000` |
| `API_KEYS_RAW` | Claves API (separadas por coma) | *(sin auth si vacío)* |

---

## Arrancar el Servidor

### 1. Configurar modo de conexión a Ollama

#### Opción A (Cloud API - recomendado para `qwen3.5:cloud`)

No requiere `ollama serve`.

```env
OLLAMA_BASE_URL=https://ollama.com
OLLAMA_MODEL=qwen3.5:cloud
OLLAMA_API_KEY=tu-api-key-ollama-cloud
```

#### Opción B (Ollama local)

```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen3:14b
```

```bash
ollama serve
```

> En Windows, Ollama normalmente corre como servicio al instalarse (solo modo local).

### 2. Iniciar la API

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Verificar que funciona

```bash
curl http://localhost:8000/health
```

Respuesta esperada:

```json
{
  "status": "ok",
  "ollama_url": "https://ollama.com",
  "ollama_cloud_api": true,
  "default_model": "qwen3.5:cloud",
  "models": ["qwen3.5:cloud"],
  "auth_mode": "api_key"
}
```

---

## Uso de la API

### Autenticación

El endpoint de extracción requiere el header:

```
X-API-Key: sk-tu-clave-aqui-001
```

### Extraer datos de un contrato

Sube un archivo `.txt` con el texto OCR del contrato:

```bash
curl -X POST http://localhost:8000/api/v1/extract \
  -H "X-API-Key: sk-tu-clave-aqui-001" \
  -F "file=@pages.txt"
```

Respuesta:

```json
{
  "success": true,
  "data": {
    "numero_contrato": "0006-2019",
    "objeto_contractual": "Prestar servicios profesionales como Administradora de Empresas...",
    "nombre_contratista": "ERIKA MARIA PALOMINO BOLIVAR",
    "vigencia": "hasta el 31 de Diciembre de 2019",
    "anio_contrato": 2019,
    "fecha_inicial": "2019-01-14",
    "valor": 49588560,
    "tipo_persona": "Natural",
    "tipo_contrato": "Prestación de servicios"
  },
  "model_used": "qwen3.5:cloud",
  "total_chars": 629277,
  "prepared_chars": 9650,
  "processing_time_ms": 121000,
  "cached": false,
  "error": null
}
```

### Filtrar campos específicos

Agregar `fields` como campo en el form-data:

```bash
curl -X POST http://localhost:8000/api/v1/extract \
  -H "X-API-Key: sk-tu-clave-aqui-001" \
  -F "file=@pages.txt" \
  -F "fields=numero_contrato,valor,nombre_contratista"
```

### Probar desde Postman

1. **Método:** `POST`
2. **URL:** `http://localhost:8000/api/v1/extract`
3. **Headers:** `X-API-Key: sk-tu-clave-aqui-001`
4. **Body → form-data:**

| Key | Tipo | Valor |
|---|---|---|
| `file` | **File** | *(seleccionar archivo .txt)* |
| `fields` | Text | *(opcional)* `numero_contrato,valor` |

---

## Documentación Interactiva

Con el servidor corriendo, accede desde el navegador:

| URL | Interfaz |
|---|---|
| [http://localhost:8000/docs](http://localhost:8000/docs) | **Swagger UI** — prueba endpoints en vivo |
| [http://localhost:8000/redoc](http://localhost:8000/redoc) | **ReDoc** — documentación detallada |

---

## Endpoints

| Método | Ruta | Auth | Descripción |
|---|---|---|---|
| `POST` | `/api/v1/extract` | Sí | **Subir archivo .txt** → extraer 9 campos del contrato |
| `GET` | `/health` | No | Estado del sistema + conexión Ollama |
| `GET` | `/cache/stats` | No | Estadísticas de caché |
| `DELETE` | `/cache` | Sí | Limpiar caché |

---

## Campos Extraídos

| Campo | Tipo | Ejemplo |
|---|---|---|
| `numero_contrato` | string | `"090-18-11-0584"` |
| `nombre_contratista` | string | `"ERIKA MARIA PALOMINO BOLIVAR"` |
| `tipo_persona` | enum | `"Natural"` / `"Jurídica"` |
| `tipo_contrato` | enum | `"Prestación de servicios"` |
| `objeto_contractual` | string | `"prestar los servicios profesionales..."` |
| `valor` | number | `31787560` |
| `anio_contrato` | integer | `2016` |
| `fecha_inicial` | string | `"2016-04-11"` |
| `vigencia` | string | `"6 meses"` |

---

## Estructura del Proyecto

```
IaOCR/
├── app/
│   ├── __init__.py
│   ├── config.py          # Configuración (Pydantic Settings + .env)
│   ├── auth.py            # Autenticación por API Key
│   ├── schemas.py         # Modelos de request/response + JSON Schema
│   ├── ollama_client.py   # Cliente async para Ollama API
│   ├── preprocessor.py    # Limpieza OCR + extracción secciones prioritarias
│   ├── cache.py           # Caché LRU con TTL y locks async
│   ├── extractor.py       # Lógica de extracción + prompts
│   └── main.py            # FastAPI app + rutas
├── .env                   # Variables de entorno (no incluido en git)
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Notas de Producción

- **GPU recomendada**: Con NVIDIA RTX 3090/4090 o superior, los tiempos bajan de ~120s a ~10-20s por contrato.
- **Sin GPU**: El modelo corre en CPU. Funcional pero más lento (~2 min por contrato).
- **Seguridad**: Cambiar las API Keys del `.env` antes de desplegar. Nunca usar las de desarrollo.
- **Caché**: Se almacena en memoria (se pierde al reiniciar). Para persistencia, considerar Redis.
- **Preprocesamiento**: El sistema extrae 7 secciones prioritarias del OCR (contrato, estudios previos, acta de inicio, SECOP, CDP, certificación, acta final) y descarta ruido automáticamente.

---

## Producción En Ubuntu Con GitHub Actions

Este repositorio incluye una base de CI/CD para desplegar en una VM Linux (Ubuntu):

- CI: `.github/workflows/ci.yml`
- Deploy: `.github/workflows/deploy-production.yml`
- Script de despliegue remoto: `scripts/deploy_production.sh`
- Script de instalación del servicio systemd: `scripts/install_systemd_service.sh`
- Plantilla systemd: `deploy/systemd/iaocr.service`
- Ejemplo de variables de entorno de producción: `.env.production.example`

### 1. Preparar GitHub (si aún no existe repo remoto)

Si tu carpeta local todavía no tiene `.git`, inicializa y publica:

```bash
git init
git add .
git commit -m "chore: setup CI/CD for production"
git branch -M main
git remote add origin <URL_DE_TU_REPO>
git push -u origin main
```

### 2. Preparar La VM Ubuntu

En la VM:

```bash
# 1) Clonar proyecto en ruta estable
sudo mkdir -p /opt
cd /opt
sudo git clone <URL_DE_TU_REPO> iaocr
sudo chown -R $USER:$USER /opt/iaocr
cd /opt/iaocr

# 2) Entorno Python
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3) Crear archivo de entorno de producción
sudo mkdir -p /etc/iaocr
sudo cp .env.production.example /etc/iaocr/iaocr.env
sudo chmod 600 /etc/iaocr/iaocr.env
sudo chown root:root /etc/iaocr/iaocr.env

# 4) Editar valores reales (API key fuerte)
sudo nano /etc/iaocr/iaocr.env

# 5) Crear servicio systemd
chmod +x scripts/install_systemd_service.sh
APP_DIR=/opt/iaocr APP_USER=$USER APP_GROUP=$USER APP_ENV_FILE=/etc/iaocr/iaocr.env \
  ./scripts/install_systemd_service.sh

# 6) Iniciar servicio
sudo systemctl start iaocr
sudo systemctl status iaocr --no-pager

# 7) Validar API
curl http://127.0.0.1:8000/health
```

### 3. Secrets En GitHub Actions

Crea estos secrets en el repositorio (Settings > Secrets and variables > Actions):

- `PROD_HOST`: IP o DNS de la VM
- `PROD_PORT`: normalmente `22`
- `PROD_USER`: usuario SSH de la VM
- `PROD_SSH_KEY`: llave privada para acceso SSH
- `PROD_APP_DIR`: ruta del proyecto en VM (ej: `/opt/iaocr`)
- `PROD_APP_ENV_FILE`: ruta del env file (ej: `/etc/iaocr/iaocr.env`)
- `PROD_SERVICE_NAME`: `iaocr`

Además, crea un Environment llamado `production` para controlar aprobaciones antes de desplegar.

### 3.1 Permiso Sudo Sin Prompt Para Deploy

El workflow reinicia el servicio con `systemctl`, por lo que el usuario SSH necesita `sudo` sin password para comandos de servicio.

```bash
sudo visudo -f /etc/sudoers.d/iaocr-deploy
```

Agregar (cambia `soporte` por tu usuario real):

```bash
soporte ALL=(ALL) NOPASSWD: /bin/systemctl, /usr/bin/systemctl
```

Guardar y validar:

```bash
sudo -l
sudo -n systemctl status iaocr --no-pager
```

### 4. Flujo De Deploy

1. Push o merge a `main`.
2. Corre CI (`ci.yml`).
3. Si CI pasa, corre deploy (`deploy-production.yml`).
4. El workflow entra por SSH, actualiza el código y reinicia `iaocr`.
5. Se valida `http://127.0.0.1:8000/health`.

### 5. Comandos Útiles De Operación

```bash
# Ver logs en vivo
sudo journalctl -u iaocr -f

# Reiniciar app
sudo systemctl restart iaocr

# Estado de Ollama
sudo systemctl status ollama --no-pager

# Modelos instalados
ollama list
```
