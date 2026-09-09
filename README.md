# Normalizador de Nombres de Facturas - Azure Functions

Azure Function en Python (Programming Model v2) que estandariza los nombres de archivos de facturas subidos a Azure Blob Storage. Se activa mediante un Event Grid Trigger cuando se crea un blob, normaliza el nombre (minúsculas, sin espacios ni caracteres especiales) y copia el archivo dentro del mismo container con el nombre normalizado, eliminando el original.

## Flujo de Procesamiento

1. Se sube un archivo `.pdf` o `.xml` al container configurado (`incoming_container`).
2. Event Grid notifica el evento `Microsoft.Storage.BlobCreated` a la función.
3. La función valida el tipo de evento y el formato del `subject` para extraer carpeta y nombre del blob.
4. Se valida que la extensión sea `.pdf` o `.xml`; cualquier otra extensión se ignora.
5. Se calcula el nombre normalizado preservando la subcarpeta de origen. Si el nombre ya está normalizado, el evento se ignora para evitar reprocesamiento.
6. El blob se copia con el nombre normalizado y el original se elimina tras confirmar la copia.
7. Si ocurre un error durante la copia, el blob se mueve al container de errores (`failed_container`) con el mensaje de error en los metadatos.

## Estructura del Proyecto

```
.
├── function_app.py                        # Punto de entrada, registra los blueprints
├── host.json                              # Configuración de Azure Functions
├── pytest.ini                             # Configuración de pytest y cobertura
├── requirements.txt                       # Dependencias
│
├── src/
│   ├── core/
│   │   ├── config/
│   │   │   └── settings.py               # Configuración vía Pydantic Settings
│   │   ├── exceptions.py                 # Excepciones personalizadas de la app
│   │   └── logging.py                    # Configuración de logging estructurado
│   │
│   ├── functions/
│   │   └── blob_processor/
│   │       └── function.py               # Event Grid Trigger: normalize_invoice_name
│   │
│   ├── integrations/
│   │   └── azure/
│   │       └── blob_storage_service.py   # Copiar/mover blobs entre containers
│   │
│   └── utils/
│       └── name_normalizer.py            # Normalización de nombres de blobs
│
└── tests/                                 # Tests unitarios (pytest)
```

## Requisitos Previos

- Python 3.11 o superior
- Azure Functions Core Tools v4
- Cuenta de Azure con:
  - Azure Functions (Event Grid Trigger)
  - Azure Storage Account con los containers configurados en `source_container_name`, `destination_container_name` y `failed_container_name`
  - Una suscripción de Event Grid sobre el Storage Account que notifique eventos `Microsoft.Storage.BlobCreated` a esta función

## Configuración

La configuración se maneja con Pydantic Settings ([src/core/config/settings.py](src/core/config/settings.py)). Variables disponibles (todas con valor por defecto salvo `storage_connection_string`):

| Variable | Descripción | Valor por defecto |
|----------|-------------|--------------------|
| `ENVIRONMENT` | Entorno de ejecución (`development`, `testing`, `production`) | `development` |
| `STORAGE_CONNECTION_STRING` | Connection string de Azure Storage | `None` |
| `SOURCE_CONTAINER_NAME` | Container origen de blobs entrantes | `entrada` |
| `DESTINATION_CONTAINER_NAME` | Container destino de blobs normalizados | `salida` |
| `FAILED_CONTAINER_NAME` | Container para blobs con error | `error` |
| `LOG_LEVEL` | Nivel de logging | `INFO` |
| `LOG_FORMAT` | Formato de logging (`json`, `text`) | `json` |

Para desarrollo local, definir estas variables en `local.settings.json`:

```json
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "UseDevelopmentStorage=true",
    "FUNCTIONS_WORKER_RUNTIME": "python",

    "ENVIRONMENT": "development",
    "LOG_LEVEL": "INFO",
    "STORAGE_CONNECTION_STRING": "DefaultEndpointsProtocol=https;AccountName=...",
    "SOURCE_CONTAINER_NAME": "entrada",
    "DESTINATION_CONTAINER_NAME": "salida",
    "FAILED_CONTAINER_NAME": "error"
  }
}
```

## Inicio Rápido

### 1. Configurar Entorno Virtual

```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

### 2. Instalar Dependencias

```bash
pip install -r requirements.txt
```

### 3. Ejecutar Localmente

```bash
func start
```

## Tests

El proyecto usa pytest con cobertura mínima requerida del 80% sobre `src/functions`, `src/core` y `src/utils` (ver [pytest.ini](pytest.ini)).

```bash
# Todos los tests
pytest

# Solo tests unitarios
pytest -m unit

# Reporte de cobertura en HTML
pytest --cov-report=html
```

## Logging

El proyecto usa logging estructurado con `structlog` (ver [src/core/logging.py](src/core/logging.py)):

```python
import structlog

logger = structlog.get_logger()

logger.info(
    "Normalización completada exitosamente",
    original_blob_path="Factura Enero 2024.PDF",
    normalized_blob_path="factura_enero_2024.pdf",
)
```

## Manejo de Errores

Las excepciones de la aplicación están centralizadas en [src/core/exceptions.py](src/core/exceptions.py). La relevante para este flujo es `StorageError`, usada por `BlobStorageService` para reportar fallas al copiar, mover o leer blobs. Cuando ocurre un error (esperado o inesperado) durante la normalización, el blob se mueve al container de errores con el detalle del fallo en los metadatos.

## Despliegue

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
    FUNCTIONS_WORKER_RUNTIME="python" \
    FUNCTIONS_EXTENSION_VERSION="~4" \
    WEBSITE_RUN_FROM_PACKAGE="1" \
    STORAGE_CONNECTION_STRING="..." \
    SOURCE_CONTAINER_NAME="entrada" \
    DESTINATION_CONTAINER_NAME="salida" \
    FAILED_CONTAINER_NAME="error"

# Desplegar
func azure functionapp publish mi-function-app
```

La Function App debe ser Linux y usar la misma versión mayor de Python que el
pipeline (actualmente 3.12). En Azure se puede comprobar con:

```bash
az functionapp config show \
  --name mi-function-app \
  --resource-group mi-resource-group \
  --query "{linuxFxVersion:linuxFxVersion,alwaysOn:alwaysOn}"

az functionapp config appsettings list \
  --name mi-function-app \
  --resource-group mi-resource-group \
  --query "[?name=='FUNCTIONS_WORKER_RUNTIME' || name=='FUNCTIONS_EXTENSION_VERSION' || name=='WEBSITE_RUN_FROM_PACKAGE']"
```

El paquete debe contener `function_app.py`, `host.json`, `requirements.txt` y
`src/` en la raíz. No se debe subir un ZIP dentro de otro ZIP ni el entorno
virtual local. El error `Offset to Central Directory cannot be held in an
Int64` indica un artefacto ZIP inválido; en el pipeline, publica un paquete
limpio aplicando `.funcignore` y evita comprimir `$(System.DefaultWorkingDirectory)`
después de haber generado otro archivo ZIP dentro de ese directorio.

Tras el despliegue, configurar la suscripción de Event Grid en el Storage Account apuntando al endpoint de la función para el evento `Microsoft.Storage.BlobCreated`.
