# Template Python Azure Functions - Document Intelligence

Template de Azure Functions en Python con Clean Architecture para procesamiento automático de documentos PDF con Azure Document Intelligence. Detecta PDFs en blob storage, extrae campos y valores, envía datos a API externa y archiva documentos.

## 🎯 Características

- ✅ Azure Functions Programming Model v2
- ✅ **Blob Trigger** - procesamiento automático al detectar PDFs
- ✅ Azure Document Intelligence para análisis de facturas
- ✅ Extracción de campos y valores (key-value pairs)
- ✅ Envío automático de datos a API externa
- ✅ Movimiento automático de PDFs entre containers (temporal → archivo)
- ✅ Manejo de errores con container de fallidos
- ✅ Integración con Azure Key Vault para gestión de secretos
- ✅ Logging estructurado con structlog
- ✅ Validación de datos con Pydantic v2
- ✅ Autenticación JWT opcional
- ✅ Manejo centralizado de excepciones
- ✅ Tests unitarios con pytest
- ✅ Sin dependencias de base de datos - procesamiento directo

## 🔄 Flujo de Procesamiento

1. **PDF llega** → Se agrega archivo a container `incoming-pdfs`
2. **Blob Trigger activa** → Azure Function detecta nuevo archivo
3. **Análisis** → Document Intelligence extrae datos (modelo: facturas)
4. **Envío** → Datos extraídos se envían a API externa (JSON)
5. **Archivo** → PDF se mueve a container `archived-pdfs`
6. **Si falla** → PDF se mueve a container `pdf-failed` con metadata de error

## 📋 Requisitos Previos

- Python 3.11 o superior
- Azure Functions Core Tools v4
- Cuenta de Azure con:
  - Azure Functions
  - Azure Key Vault
  - Azure Document Intelligence
  - Azure Storage Account con 3 containers:
    - `incoming-pdfs` (temporal, donde se suben PDFs)
    - `archived-pdfs` (permanente, PDFs procesados)
    - `pdf-failed` (errores, PDFs que fallaron)
  - API externa que acepte JSON con datos extraídos

## 🚀 Inicio Rápido

### 1. Clonar el Proyecto

```bash
git clone <repository-url>
cd template.python-function.back
```

### 2. Configurar Entorno Virtual

```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

### 3. Instalar Dependencias

```bash
python scripts/setup_dev.py
```

O manualmente:

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 4. Configurar Variables de Entorno

**IMPORTANTE**: Este proyecto usa Azure Key Vault para TODAS las variables sensibles.

#### Desarrollo Local

Editar `local.settings.json` con las credenciales de Key Vault:

```json
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "UseDevelopmentStorage=true",
    "FUNCTIONS_WORKER_RUNTIME": "python",
    
    "ENVIRONMENT": "development",
    "LOG_LEVEL": "INFO",
    
    "AZURE_KEY_VAULT_URL": "https://tu-keyvault.vault.azure.net/",
    "AZURE_TENANT_ID": "tu-tenant-id",
    "AZURE_CLIENT_ID": "tu-client-id",
    "AZURE_CLIENT_SECRET": "tu-client-secret"
  }
}
```

#### Configurar Secretos en Key Vault

Los secretos necesarios en Azure Key Vault:

```bash
# Document Intelligence
az keyvault secret set --vault-name tu-keyvault --name document-intelligence-endpoint --value "https://..."
az keyvault secret set --vault-name tu-keyvault --name document-intelligence-key --value "tu-api-key"

# API Externa
az keyvault secret set --vault-name tu-keyvault --name external-api-url --value "https://api.documentos.com/api/documents"
az keyvault secret set --vault-name tu-keyvault --name external-api-key --value "tu-api-key-externa"

# Azure Storage
az keyvault secret set --vault-name tu-keyvault --name storage-connection-string --value "DefaultEndpointsProtocol=https;AccountName=..."

# JWT (opcional - si usas autenticación)
az keyvault secret set --vault-name tu-keyvault --name jwt-secret --value "tu-secreto-jwt"

# Ver docs/KEY_VAULT_SETUP.md para lista completa
```

Ver [docs/KEY_VAULT_SETUP.md](docs/KEY_VAULT_SETUP.md) para configuración completa.

### 5. Validar Configuración

```bash
python scripts/validate.py
```

### 6. Ejecutar Localmente

```bash
func start
```

La aplicación estará disponible en `http://localhost:7071`

## 📁 Estructura del Proyecto

```
template.python-function.back/
├── function_app.py              # Punto de entrada de Azure Functions
├── host.json                    # Configuración de Azure Functions
├── local.settings.json          # Variables de entorno locales
├── requirements.txt             # Dependencias principales
├── requirements-dev.txt         # Dependencias de desarrollo
├── pytest.ini                   # Configuración de pytest
│
├── src/                         # Código fuente (99%+ cobertura)
│   ├── functions/              # Azure Functions handlers
│   │   ├── health/            # Health check endpoint
│   │   ├── document_analysis/ # Análisis manual de PDFs (HTTP)
│   │   └── blob_processor/    # Procesamiento automático de PDFs (Blob Trigger)
│   │
│   ├── core/                   # Componentes core
│   │   ├── config/            # Configuración y settings
│   │   │   ├── settings.py   # Variables de entorno con Pydantic
│   │   │   └── load_secrets.py # Azure Key Vault
│   │   ├── logging.py         # Logging estructurado
│   │   └── exceptions.py      # Excepciones personalizadas
│   │
│   ├── models/                 # Esquemas Pydantic
│   │   └── document.py        # Schemas para documentos
│   │
│   ├── utils/                  # Utilidades
│   │   ├── response.py        # Helpers de respuestas HTTP
│   │   └── security.py        # JWT y seguridad
│   │
│   └── integrations/           # Servicios externos (NO medido en cobertura)
│       ├── azure/             # Servicios Azure
│       │   ├── blob_storage_service.py
│       │   ├── document_intelligence_service.py
│       │   └── key_vault.py
│       ├── api/               # APIs externas
│       │   └── external_api_service.py
│       └── decorators.py      # Decoradores legacy
│
├── scripts/                     # Scripts de automatización
│   ├── process_pdf.py          # Procesamiento batch de PDFs
│   ├── setup_dev.py            # Configuración de desarrollo
│   └── validate.py             # Validación del proyecto
│
├── tests/                       # Tests (173 passing, 16 skipped)
│   ├── conftest.py
│   ├── test_health.py
│   ├── test_items.py
│   └── test_document_intelligence.py
│
└── docs/                        # Documentación
    ├── STRUCTURE.md            # Estructura del proyecto
    ├── BEST_PRACTICES.md
    └── DOCUMENT_INTELLIGENCE.md

NOTA: La estructura fue reorganizada de shared/ y functions/ a src/ para mejor organización
y cobertura de tests (99.26%). Ver STRUCTURE.md para detalles de la migración.
```

## 🔌 Endpoints Disponibles

### Health Check

```http
GET /api/health

Respuesta:
{
  "success": true,
  "data": {
    "status": "healthy",
    "timestamp": "2024-04-08T12:00:00Z",
    "version": "1.0.0"
  }Procesamiento Automático (Blob Trigger)

```
No requiere llamada HTTP - se activa automáticamente cuando se sube un PDF a:
- Container: incoming-pdfs
- Tipo: *.pdf

Flujo:
1. PDF llega a incoming-pdfs
2. Function se activa automáticamente
3. Procesa con Document Intelligence (modelo: prebuilt-invoice)
4. Envía datos a API externa configurada
5. Mueve PDF a archived-pdfs
6. Si falla, mueve a pdf-failed
```

### Análisis Manual de Documentos PDF (HTTP)
}
```

### Análisis de Documentos PDF

```http
# Analizar documento desde URL
POST /api/documents/analyze
{
  "document_url": "https://storage.blob.core.windows.net/docs/factura.pdf",
  "model_id": "prebuilt-invoice",
  "pages": "1-3"
}

Respuesta:
{
  "success": true,
  "message": "Documento analizado exitosamente",
  "data": {
    "model_id": "prebuilt-invoice",
    "content": "Texto completo extraído...",
    "pages_count": 3,
    "tables_count": 2,
    "key_value_pairs": {
      "InvoiceId": "INV-001",
      "InvoiceTotal": "1500.00",
      "InvoiceDate": "2024-04-08",
      "VendorName": "Empresa XYZ"
    },
    "confidence": 0.98,
    "pages": [...],
    "tables": [...]
  }
}

# Modelos disponibles
GET /api/documents/models
```

## 📄 Modelos de Document Intelligence

| Modelo | Descripción | Casos de Uso |
|--------|-------------|--------------|
| `prebuilt-read` | Lectura general de texto | Extracción de texto, OCR |
| `prebuilt-layout` | Layout y tablas | Tablas, estructura de documentos |
| `prebuilt-invoice` | Facturas | Procesamiento de facturas |
| `prebuilt-receipt` | Recibos | Tickets de compra |
| `prebuilt-idDocument` | Documentos de identidad | Pasaportes, licencias |
| `prebuilt-businessCard` | Tarjetas de presentación | Información de contacto |

## 🤖 Script de Automatización

Procesar documentos PDF en batch:

```bash
# Procesar un archivo
python scripts/process_pdf.py --file documento.pdf --model prebuilt-read

# Procesar carpeta completa
python scripts/process_pdf.py --folder ./documentos --model prebuilt-invoice --output resultados.json

# Procesar desde URL
python scripts/process_pdf.py --url https://ejemplo.com/doc.pdf --model prebuilt-layout

# Con carga de secretos desde Key Vault
python scripts/process_pdf.py --file doc.pdf --load-secrets
```

## 🧪 Tests

Ejecutar tests:

```bash
# Todos los tests
pytest

# Tests con cobertura
pytest --cov

# Solo tests unitarios
pytest -m unit

# Tests con reporte HTML
pytest --cov --cov-report=html
```

## 🔐 Seguridad

### Azure Key Vault

**TODAS las variables sensibles se almacenan en Azure Key Vault**:

**Base de Datos:**
- `db-host`, `db-port`, `db-name`, `db-user`, `db-password`

**Document Intelligence:**
- `document-intelligence-endpoint`, `document-intelligence-key`

**Seguridad:**
- `jwt-secret`, `jwt-algorithm`, `jwt-expire-minutes`

**Configuración:**
- `rate-limit-requests`, `rate-limit-window`
- `max-multipart-size`
- `appinsights-connection-string`
Secretos almacenados en Azure Key Vault**:

**Document Intelligence:**
- `document-intelligence-endpoint`
- `document-intelligence-key`

**Seguridad (opcional)
## 📊 Logging

El proyecto usa logging estructurado con `structlog`:

```python
import structlog

logger = structlog.get_logger()

logger.info(
    "Documento procesado",
    document_id=123,
    pages=5,
    confidence=0.98
)
```

Los logs incluyen:
- Filtrado automático de información sensible
- IDs de invocación para rastreo
- Formato JSON para análisis

## 🚀 Despliegue

### Despliegue a Azure

```bash
# Login a Azure
az login

# Crear Function App
az functionapp create \
  --name mi-function-app \
  --resource-group mi-resource-group \
  --consumption-plan-location eastus \
  --runtime python \
  --runtime-version 3.11 \
  --os-type linux \
  --storage-account mistorage

# Configurar Application Settings
az functionapp config appsettings set \
  --name mi-function-app \
  --resource-group mi-resource-group \
  --settings \
    DOCUMENT_INTELLIGENCE_ENDPOINT="https://..." \
    AZURE_KEY_VAULT_URL="https://..."

# Desplegar
func azure functionapp publish mi-function-app
```

## 📚 Documentación Adicional

- [Configuración de Azure Key Vault](docs/KEY_VAULT_SETUP.md) - **IMPORTANTE: Leer primero**
- [Procesamiento Automático con Blob Trigger](docs/BLOB_PROCESSING.md) - **Flujo principal del sistema**
- [Testing y Cobertura](docs/TESTING.md) - **Guía completa de tests (80% mínimo)**
- [Mejores Prácticas](docs/BEST_PRACTICES.md)
- [Guía de Document Intelligence](docs/DOCUMENT_INTELLIGENCE.md)
- [Inicio Rápido](docs/QUICKSTART.md)

## 🤝 Contribución

1. Fork el proyecto
2. Crear rama de feature (`git checkout -b feature/AmazingFeature`)
3. Commit cambios (`git commit -m 'Add AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abrir Pull Request


## 👥 Autores

DevOps Team

## 🙏 Agradecimientos

- Template basado en mejores prácticas de Clean Architecture
- Integración con Azure Document Intelligence
- Inspirado en el proyecto template.python.back
