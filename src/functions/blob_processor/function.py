"""
Azure Function con Event Grid Trigger para estandarización de nombres de facturas.

Esta función se activa mediante un evento de Event Grid cuando un archivo es agregado
al container definido.

Normaliza el nombre (minúsculas, sin espacios, sin caracteres especiales) y copia
el archivo al container 'incoming' con el nombre estandarizado, preservando la subcarpeta
de origen (porvalidar, porgestionar, etc.).

El archivo original se elimina tras la copia exitosa.
Si la operación falla, el archivo se mueve al container de errores con el metadata del error.
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


@bp.event_grid_trigger(arg_name="event")
async def normalize_invoice_name(event: func.EventGridEvent) -> None:
    """
    Normalizar nombre de factura cuando Event Grid notifica un blob creado
    en el container incoming-invoices.

    Flujo:
    1. Validar que sea un evento de creación (Microsoft.Storage.BlobCreated)
    2. Parsear el subject para extraer carpeta y nombre del blob
    3. Validar extensión permitida (.pdf / .xml)
    4. Calcular nombre normalizado preservando la subcarpeta
    5. Copiar al container destino y validar copia
    6. Eliminar blob original tras copia exitosa

    Args:
        event: Evento de Event Grid con metadata del blob creado
    """

    # Ignorar eventos que no sean creación de blob
    event_type = event.event_type
    if event_type != "Microsoft.Storage.BlobCreated":
        logger.info(
            "Evento ignorado por tipo no relevante",
            event_type=event_type,
            event_id=event.id,
        )
        return

    # El subject tiene el formato:
    # /blobServices/default/containers/<container>/blobs/<carpeta>/<archivo>
    subject: str = event.subject
    subject_parts = subject.split("/blobs/", maxsplit=1)

    if len(subject_parts) != 2:
        logger.error(
            "Subject del evento no tiene el formato esperado",
            subject=subject,
            event_id=event.id,
        )
        return

    original_blob_path = subject_parts[1]  # "porvalidar/factura 001.pdf"

    # Separar carpeta y nombre de archivo
    path_parts = original_blob_path.rsplit("/", maxsplit=1)
    if len(path_parts) == 2:
        folder_path, filename = path_parts  # "porvalidar", "factura 001.pdf"
    else:
        folder_path, filename = "", path_parts[0]  # raíz del container

    event_data: dict = event.get_json()

    logger.info(
        "Event Grid trigger activado",
        event_id=event.id,
        event_type=event_type,
        original_blob_path=original_blob_path,
        folder_path=folder_path,
        filename=filename,
        blob_url=event_data.get("url"),
        blob_size=event_data.get("contentLength"),
        content_type=event_data.get("contentType"),
        etag=event_data.get("eTag"),
    )

    # Validar extensión
    extension = ""
    if "." in filename:
        extension = "." + filename.split(".")[-1].lower()

    if extension not in {".pdf", ".xml"}:
        logger.warning(
            "Archivo ignorado por extensión no permitida",
            original_blob_path=original_blob_path,
            extension=extension,
            allowed_extensions=[".pdf", ".xml"],
        )
        return

    # Calcular nombre normalizado solo sobre el filename, preservando la carpeta
    try:
        normalized_filename = normalize_blob_name(filename)
    except ValueError as e:
        logger.error(
            "Nombre de blob no normalizable",
            original_blob_path=original_blob_path,
            error=str(e),
        )
        return

    if filename == normalized_filename:
        logger.info(
            "Nombre ya normalizado, ignorando para evitar re-procesamiento",
            original_blob_path=original_blob_path,
        )
        return

    # Reconstruir ruta completa preservando la subcarpeta
    normalized_blob_path = (
        f"{folder_path}/{normalized_filename}" if folder_path else normalized_filename
    )

    logger.info(
        "Nombre normalizado calculado",
        original_blob_path=original_blob_path,
        normalized_blob_path=normalized_blob_path,
        folder_path=folder_path,
    )

    storage_service = BlobStorageService()

    try:
        destination_url = await storage_service.copy_blob_with_normalized_name(
            original_name=original_blob_path,      # "porvalidar/factura 001.pdf"
            normalized_name=normalized_blob_path,  # "porvalidar/factura001.pdf"
            source_container=storage_service.incoming_container,
            destination_container=storage_service.incoming_container,
        )

        logger.info(
            "Normalización completada exitosamente",
            original_blob_path=original_blob_path,
            normalized_blob_path=normalized_blob_path,
            source_container=storage_service.incoming_container,
            destination_container=storage_service.incoming_container,
            destination_url=destination_url,
        )

    except StorageError as e:
        logger.error(
            "Error de storage durante normalización",
            original_blob_path=original_blob_path,
            normalized_blob_path=normalized_blob_path,
            error=str(e),
        )

        try:
            await storage_service.move_blob_to_failed(
                blob_name=original_blob_path,
                source_container=storage_service.incoming_container,
                error_message=f"StorageError durante normalización: {str(e)}",
            )
        except Exception as move_error:
            logger.critical(
                "No se pudo mover blob a container de errores",
                original_blob_path=original_blob_path,
                error=str(move_error),
            )

    except Exception as e:
        logger.critical(
            "Error inesperado durante normalización",
            original_blob_path=original_blob_path,
            normalized_blob_path=normalized_blob_path,
            error=str(e),
            error_type=type(e).__name__,
        )

        try:
            await storage_service.move_blob_to_failed(
                blob_name=original_blob_path,
                source_container=storage_service.incoming_container,
                error_message=f"Error inesperado: {type(e).__name__}: {str(e)}",
            )
        except Exception as move_error:
            logger.critical(
                "No se pudo mover blob a container de errores",
                original_blob_path=original_blob_path,
                error=str(move_error),
            )