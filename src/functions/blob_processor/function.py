"""
Azure Function con Blob Trigger para estandarización de nombres de facturas.

Esta función se activa cuando un archivo es agregado al container 'incoming-invoices'.
Normaliza el nombre (minúsculas, sin espacios, sin caracteres especiales) y copia
el archivo al container 'normalized-invoices' con el nombre estandarizado.

El archivo original en 'incoming-invoices' se elimina tras la copia exitosa.
Si la operación falla, el archivo se mueve a 'invoices-failed' con metadata del error.
"""

import azure.functions as func
from azure.functions import Blueprint
import structlog

from src.integrations.azure.blob_storage_service import BlobStorageService
from src.utils.name_normalizer import normalize_blob_name
from src.core.exceptions import StorageError

logger = structlog.get_logger()
bp = Blueprint()

logger.info("Módulo blob_processor cargado")

@bp.blob_trigger(
    arg_name="blob",
    path="entrada/{name}",
    connection="AzureWebJobsStorage",
    source="EventGrid"
)
async def normalize_invoice_name(blob: func.InputStream) -> None:
    """
    Normalizar nombre de factura cuando es agregada al container incoming-invoices.

    Flujo:
    1. Obtener solo el nombre del blob
    2. Validar extensión permitida (.pdf/.xml)
    3. Calcular nombre normalizado
    4. Copiar al container destino y validar copia
    5. Eliminar blob original tras copia exitosa

    Args:
        blob: Stream del blob que activó la función
    """
    original_name = blob.name.split("/")[-1]

    logger.info(
        "Blob trigger activado",
        original_name=original_name,
        blob_size=blob.length,
        blob_uri=blob.uri,
    )

    extension = ""
    if "." in original_name:
        extension = "." + original_name.split(".")[-1].lower()

    if extension not in {".pdf", ".xml"}:
        logger.warning(
            "Archivo ignorado por extensión no permitida",
            original_name=original_name,
            extension=extension,
            allowed_extensions=[".pdf", ".xml"],
        )
        return

    # Calcular nombre normalizado en base al string del nombre
    try:
        normalized_name = normalize_blob_name(original_name)
    except ValueError as e:
        logger.error(
            "Nombre de blob no normalizable",
            original_name=original_name,
            error=str(e),
        )
        return  # No hay contenido que mover; el blob queda en incoming para revisión manual

    logger.info(
        "Nombre normalizado calculado",
        original_name=original_name,
        normalized_name=normalized_name,
        changed=original_name != normalized_name,
    )

    storage_service = BlobStorageService()

    try:
        # Mover sin leer/parsear contenido: copy -> validar -> delete
        destination_url = await storage_service.copy_blob_with_normalized_name(
            original_name=original_name,
            normalized_name=normalized_name,
            source_container=storage_service.incoming_container,
            destination_container=storage_service.incoming_container,  # Copia dentro del mismo container para renombrar sin mover entre containers
        )

        logger.info(
            "Normalización completada exitosamente",
            original_name=original_name,
            normalized_name=normalized_name,
            source_container=storage_service.incoming_container,
            destination_container=storage_service.incoming_container,  # Copia dentro del mismo container para renombrar sin mover entre containers
            destination_url=destination_url,
        )

    except StorageError as e:
        logger.error(
            "Error de storage durante normalización",
            original_name=original_name,
            normalized_name=normalized_name,
            error=str(e),
        )

        try:
            await storage_service.move_blob_to_failed(
                blob_name=original_name,
                source_container=storage_service.incoming_container,
                error_message=f"StorageError durante normalización: {str(e)}",
            )
        except Exception as move_error:
            logger.critical(
                "No se pudo mover blob a container de errores",
                original_name=original_name,
                error=str(move_error),
            )

    except Exception as e:
        logger.critical(
            "Error inesperado durante normalización",
            original_name=original_name,
            normalized_name=normalized_name,
            error=str(e),
            error_type=type(e).__name__,
        )

        try:
            await storage_service.move_blob_to_failed(
                blob_name=original_name,
                source_container=storage_service.incoming_container,
                error_message=f"Error inesperado: {type(e).__name__}: {str(e)}",
            )
        except Exception as move_error:
            logger.critical(
                "No se pudo mover blob a container de errores",
                original_name=original_name,
                error=str(move_error),
            )
