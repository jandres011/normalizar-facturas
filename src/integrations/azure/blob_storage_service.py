import asyncio
from typing import Optional

from azure.storage.blob.aio import BlobServiceClient
from azure.core.exceptions import AzureError
import structlog

from src.core.config.settings import get_settings
from src.core.exceptions import StorageError

logger = structlog.get_logger()


class BlobStorageService:
    def __init__(self):
        self.settings = get_settings()
        self.connection_string = self.settings.storage_connection_string

        self.incoming_container = self.settings.source_container_name
        self.archived_container = self.settings.destination_container_name
        self.failed_container = self.settings.failed_container_name

        # ✔ Cliente persistente (mejor performance)
        self.blob_service = BlobServiceClient.from_connection_string(
            self.connection_string
        )

    async def copy_blob_with_normalized_name(
        self,
        original_name: str,
        normalized_name: str,
        source_container: Optional[str] = None,
        destination_container: Optional[str] = None,
    ) -> str:

        source_container = source_container or self.incoming_container
        destination_container = destination_container or self.archived_container

        try:
            source_blob = self.blob_service.get_blob_client(
                container=source_container,
                blob=original_name,
            )

            dest_blob = self.blob_service.get_blob_client(
                container=destination_container,
                blob=normalized_name,
            )

            logger.info("Iniciando copia", original=original_name)

            # ✅ SIN SAS (misma cuenta)
            copy = await dest_blob.start_copy_from_url(source_blob.url)

            copy_id = copy["copy_id"]

            # ✅ Espera robusta
            for _ in range(60):  # hasta ~60s
                props = await dest_blob.get_blob_properties()
                status = props.copy.status

                if status == "success":
                    break

                if status in ("failed", "aborted"):
                    raise StorageError(f"Copy falló: {status}")

                await asyncio.sleep(1)
            else:
                raise StorageError("Copy timeout")

            # ✅ Delete solo después de éxito
            await source_blob.delete_blob()

            logger.info("Blob movido correctamente", name=normalized_name)

            return dest_blob.url

        except AzureError as e:
            logger.error("Error Azure", error=str(e))
            raise StorageError(str(e))

        except Exception as e:
            logger.error("Error inesperado", error=str(e))
            raise StorageError(str(e))