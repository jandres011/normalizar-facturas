"""
Servicio para gestión de blobs en Azure Storage.
Maneja operaciones de mover/copiar blobs entre containers.
"""

import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple

from azure.storage.blob.aio import BlobServiceClient
from azure.storage.blob import generate_blob_sas, BlobSasPermissions
from azure.core.exceptions import ResourceNotFoundError, AzureError
import structlog

from src.core.config.settings import get_settings
from src.core.exceptions import StorageError

logger = structlog.get_logger()


class BlobStorageService:
    """Servicio para operaciones con Azure Blob Storage."""

    def __init__(self):
        """Inicializar servicio con configuración."""
        self.settings = get_settings()
        self.connection_string = self.settings.storage_connection_string

        # Nombres de containers
        self.incoming_container = self.settings.source_container_name
        self.archived_container = self.settings.destination_container_name
        self.failed_container = self.settings.failed_container_name

    def _get_blob_service_client(self) -> BlobServiceClient:
        """
        Crear cliente de Blob Service.

        Returns:
            BlobServiceClient configurado
        """
        return BlobServiceClient.from_connection_string(self.connection_string)

    def _split_filename(self, name: str) -> Tuple[str, str]:
        """Divide nombre en stem y extensión preservando la extensión."""
        dot_index = name.rfind(".")
        if dot_index <= 0:
            return name, ""
        return name[:dot_index], name[dot_index:]

    def _generate_sas_url(
        self,
        blob_service: BlobServiceClient,
        container_name: str,
        blob_name: str,
        expiry_minutes: int = 10,
    ) -> str:
        """
        Genera una SAS URL con permisos de lectura para un blob privado.

        Necesario para server-side copy entre containers privados,
        ya que start_copy_from_url requiere una URL autenticada.

        Args:
            blob_service: Cliente del Blob Service (para obtener account_name y key)
            container_name: Nombre del container origen
            blob_name: Nombre del blob
            expiry_minutes: Minutos de validez del SAS token (default: 10)

        Returns:
            URL completa con SAS token
        """
        account_name = blob_service.account_name
        account_key = blob_service.credential.account_key

        sas_token = generate_blob_sas(
            account_name=account_name,
            container_name=container_name,
            blob_name=blob_name,
            account_key=account_key,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.now(timezone.utc) + timedelta(minutes=expiry_minutes),
        )

        return (
            f"https://{account_name}.blob.core.windows.net"
            f"/{container_name}/{blob_name}?{sas_token}"
        )

    async def _resolve_available_destination_name(
        self,
        blob_service: BlobServiceClient,
        destination_container: str,
        normalized_name: str,
    ) -> str:
        """Resuelve conflictos de nombre agregando sufijo incremental."""
        candidate = normalized_name
        candidate_blob = blob_service.get_blob_client(
            container=destination_container,
            blob=candidate,
        )

        if not await candidate_blob.exists():
            return candidate

        stem, extension = self._split_filename(normalized_name)
        for index in range(1, 1001):
            candidate = f"{stem}_{index}{extension}"
            candidate_blob = blob_service.get_blob_client(
                container=destination_container,
                blob=candidate,
            )
            if not await candidate_blob.exists():
                logger.warning(
                    "Conflicto de nombre resuelto con sufijo",
                    original_normalized_name=normalized_name,
                    resolved_name=candidate,
                    attempt=index,
                    destination_container=destination_container,
                )
                return candidate

        raise StorageError(
            f"No se pudo resolver nombre disponible para '{normalized_name}'"
        )

    async def _wait_for_copy_success(
        self,
        dest_blob,
        blob_name: str,
        max_attempts: int = 60,
        delay: float = 1.0,
    ) -> None:
        for attempt in range(max_attempts):
            properties = await dest_blob.get_blob_properties()
            status = properties.copy.status

            if status == "success":
                return

            if status in {"failed", "aborted"}:
                raise StorageError(
                    f"La copia del blob '{blob_name}' falló con estado: {status}"
                )

            await asyncio.sleep(delay)

        raise StorageError(
            f"La copia del blob '{blob_name}' no finalizó tras {max_attempts * delay}s"
        )

    async def copy_blob_with_normalized_name(
        self,
        original_name: str,
        normalized_name: str,
        source_container: Optional[str] = None,
        destination_container: Optional[str] = None,
    ) -> str:
        """
        Copiar blob por nombre al contenedor destino y eliminar origen tras éxito.

        Implementa el patrón estricto: copy -> validar copy -> delete origen.
        Genera un SAS token para el blob origen porque los containers son privados
        y start_copy_from_url requiere una URL autenticada.
        No descarga ni inspecciona el contenido del archivo.
        """
        source_container = source_container or self.incoming_container
        destination_container = destination_container or self.archived_container

        if not original_name or not original_name.strip():
            raise StorageError("El nombre original del blob es inválido o vacío")
        if not normalized_name or not normalized_name.strip():
            raise StorageError("El nombre normalizado del blob es inválido o vacío")

        try:
            async with self._get_blob_service_client() as blob_service:
                source_blob = blob_service.get_blob_client(
                    container=source_container,
                    blob=original_name,
                )

                # Generar SAS URL para el blob origen (requerido para containers privados)
                source_url_with_sas = self._generate_sas_url(
                    blob_service=blob_service,
                    container_name=source_container,
                    blob_name=original_name,
                )

                destination_name = await self._resolve_available_destination_name(
                    blob_service=blob_service,
                    destination_container=destination_container,
                    normalized_name=normalized_name,
                )

                dest_blob = blob_service.get_blob_client(
                    container=destination_container,
                    blob=destination_name,
                )

                copy_operation = await dest_blob.start_copy_from_url(source_url_with_sas)
                logger.info(
                    "Copia de blob iniciada",
                    original_name=original_name,
                    destination_name=destination_name,
                    source_container=source_container,
                    destination_container=destination_container,
                    copy_id=copy_operation.get("copy_id"),
                )

                await self._wait_for_copy_success(dest_blob, original_name)
                await source_blob.delete_blob()

                logger.info(
                    "Blob movido exitosamente por nombre",
                    original_name=original_name,
                    normalized_name=destination_name,
                    source_container=source_container,
                    destination_container=destination_container,
                    destination_url=dest_blob.url,
                )

                return dest_blob.url

        except ResourceNotFoundError as e:
            logger.error(
                "Blob no encontrado para copia",
                original_name=original_name,
                source_container=source_container,
                error=str(e),
            )
            raise StorageError(
                f"Blob '{original_name}' no encontrado en '{source_container}'"
            ) from e
        except AzureError as e:
            logger.error(
                "Error Azure durante copia por nombre",
                original_name=original_name,
                normalized_name=normalized_name,
                source_container=source_container,
                destination_container=destination_container,
                error=str(e),
            )
            raise StorageError(f"Error al copiar blob: {str(e)}") from e
        except StorageError:
            raise
        except Exception as e:
            logger.error(
                "Error inesperado durante copia por nombre",
                original_name=original_name,
                normalized_name=normalized_name,
                source_container=source_container,
                destination_container=destination_container,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise StorageError(f"Error inesperado al copiar blob: {str(e)}") from e

    async def move_blob_to_archive(
        self,
        blob_name: str,
        source_container: Optional[str] = None,
    ) -> str:
        """
        Mover blob del container temporal al archivo permanente.

        Args:
            blob_name: Nombre del blob a mover
            source_container: Container origen (por defecto incoming)

        Returns:
            URL del blob en el container de archivo

        Raises:
            StorageError: Si falla la operación
        """
        source_container = source_container or self.incoming_container
        return await self.copy_blob_with_normalized_name(
            original_name=blob_name,
            normalized_name=blob_name,
            source_container=source_container,
            destination_container=self.archived_container,
        )

    async def move_blob_to_failed(
        self,
        blob_name: str,
        source_container: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> str:
        """
        Mover blob al container de errores.

        Genera SAS token para la URL origen porque los containers son privados.

        Args:
            blob_name: Nombre del blob a mover
            source_container: Container origen (por defecto incoming)
            error_message: Mensaje de error para registrar en metadata

        Returns:
            URL del blob en el container de errores

        Raises:
            StorageError: Si falla la operación
        """
        if source_container is None:
            source_container = self.incoming_container

        try:
            logger.warning(
                "Moviendo blob a container de errores",
                blob_name=blob_name,
                source=source_container,
                error=error_message,
            )

            async with self._get_blob_service_client() as blob_service:
                source_blob = blob_service.get_blob_client(
                    container=source_container,
                    blob=blob_name,
                )

                # Generar SAS URL para el blob origen (requerido para containers privados)
                source_url_with_sas = self._generate_sas_url(
                    blob_service=blob_service,
                    container_name=source_container,
                    blob_name=blob_name,
                )

                dest_blob = blob_service.get_blob_client(
                    container=self.failed_container,
                    blob=blob_name,
                )

                await dest_blob.start_copy_from_url(source_url_with_sas)
                await self._wait_for_copy_success(dest_blob, blob_name)

                if error_message:
                    metadata = {"error_message": error_message[:1000]}
                    await dest_blob.set_blob_metadata(metadata)

                await source_blob.delete_blob()

                logger.info(
                    "Blob movido a errores exitosamente",
                    blob_name=blob_name,
                    destination_url=dest_blob.url,
                )

                return dest_blob.url

        except Exception as e:
            logger.error(
                "Error al mover blob a container de errores",
                blob_name=blob_name,
                error=str(e),
            )
            raise StorageError(
                f"Error al mover blob a errores: {str(e)}"
            ) from e

    async def read_blob(
        self,
        blob_name: str,
        container_name: Optional[str] = None,
    ) -> bytes:
        """
        Leer contenido de un blob.

        Args:
            blob_name: Nombre del blob a leer
            container_name: Nombre del container (por defecto incoming)

        Returns:
            Contenido del blob en bytes

        Raises:
            StorageError: Si falla la lectura
        """
        if container_name is None:
            container_name = self.incoming_container

        try:
            logger.debug(
                "Leyendo blob",
                blob_name=blob_name,
                container=container_name,
            )

            async with self._get_blob_service_client() as blob_service:
                blob_client = blob_service.get_blob_client(
                    container=container_name,
                    blob=blob_name,
                )

                blob_data = await blob_client.download_blob()
                content = await blob_data.readall()

                logger.debug(
                    "Blob leído exitosamente",
                    blob_name=blob_name,
                    size_bytes=len(content),
                )

                return content

        except ResourceNotFoundError as e:
            logger.error(
                "Blob no encontrado",
                blob_name=blob_name,
                container=container_name,
            )
            raise StorageError(f"Blob '{blob_name}' no encontrado") from e

        except Exception as e:
            logger.error(
                "Error al leer blob",
                blob_name=blob_name,
                error=str(e),
            )
            raise StorageError(f"Error al leer blob: {str(e)}") from e

    async def get_blob_url(
        self,
        blob_name: str,
        container_name: str,
    ) -> str:
        """
        Obtener URL de un blob.

        Args:
            blob_name: Nombre del blob
            container_name: Nombre del container

        Returns:
            URL completa del blob
        """
        async with self._get_blob_service_client() as blob_service:
            blob_client = blob_service.get_blob_client(
                container=container_name,
                blob=blob_name,
            )
            return blob_client.url