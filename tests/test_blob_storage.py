"""
Tests para BlobStorageService enfocados en movimiento por nombre.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from azure.core.exceptions import ResourceNotFoundError

from src.integrations.azure.blob_storage_service import BlobStorageService
from src.core.exceptions import StorageError


@pytest.fixture
def mock_settings():
    with patch("src.integrations.azure.blob_storage_service.get_settings") as mock:
        settings = MagicMock()
        settings.storage_connection_string = (
            "DefaultEndpointsProtocol=https;AccountName=test;AccountKey=key"
        )
        settings.source_container_name = "incoming-invoices"
        settings.destination_container_name = "normalized-invoices"
        settings.failed_container_name = "invoices-failed"
        mock.return_value = settings
        yield settings


@pytest.mark.unit
@pytest.mark.asyncio
async def test_copy_blob_with_normalized_name_success(mock_settings):
    service = BlobStorageService()

    with patch("src.integrations.azure.blob_storage_service.BlobServiceClient") as MockClient:
        blob_service = MagicMock()
        MockClient.from_connection_string.return_value = blob_service
        blob_service.__aenter__ = AsyncMock(return_value=blob_service)
        blob_service.__aexit__ = AsyncMock(return_value=None)

        source_blob = MagicMock()
        source_blob.url = "https://acct.blob.core.windows.net/incoming-invoices/Factura.PDF"
        source_blob.delete_blob = AsyncMock()

        dest_blob = MagicMock()
        dest_blob.url = "https://acct.blob.core.windows.net/normalized-invoices/factura.pdf"
        dest_blob.exists = AsyncMock(return_value=False)
        dest_blob.start_copy_from_url = AsyncMock(return_value={"copy_id": "abc"})
        props = MagicMock()
        props.copy.status = "success"
        dest_blob.get_blob_properties = AsyncMock(return_value=props)

        blob_service.get_blob_client.side_effect = [source_blob, dest_blob, dest_blob]

        result = await service.copy_blob_with_normalized_name(
            original_name="Factura.PDF",
            normalized_name="factura.pdf",
        )

        assert result == dest_blob.url
        source_blob.delete_blob.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_copy_blob_with_normalized_name_duplicate_resolves_suffix(mock_settings):
    service = BlobStorageService()

    with patch("src.integrations.azure.blob_storage_service.BlobServiceClient") as MockClient:
        blob_service = MagicMock()
        MockClient.from_connection_string.return_value = blob_service
        blob_service.__aenter__ = AsyncMock(return_value=blob_service)
        blob_service.__aexit__ = AsyncMock(return_value=None)

        source_blob = MagicMock()
        source_blob.url = "https://acct.blob.core.windows.net/incoming-invoices/Factura.xml"
        source_blob.delete_blob = AsyncMock()

        existing_dest = MagicMock()
        existing_dest.exists = AsyncMock(return_value=True)

        available_dest = MagicMock()
        available_dest.exists = AsyncMock(return_value=False)
        available_dest.url = "https://acct.blob.core.windows.net/normalized-invoices/factura_1.xml"
        available_dest.start_copy_from_url = AsyncMock(return_value={"copy_id": "copy-1"})
        props = MagicMock()
        props.copy.status = "success"
        available_dest.get_blob_properties = AsyncMock(return_value=props)

        blob_service.get_blob_client.side_effect = [
            source_blob,
            existing_dest,
            available_dest,
            available_dest,
        ]

        result = await service.copy_blob_with_normalized_name(
            original_name="Factura.xml",
            normalized_name="factura.xml",
        )

        assert result.endswith("factura_1.xml")
        source_blob.delete_blob.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_copy_blob_with_normalized_name_copy_error(mock_settings):
    service = BlobStorageService()

    with patch("src.integrations.azure.blob_storage_service.BlobServiceClient") as MockClient:
        blob_service = MagicMock()
        MockClient.from_connection_string.return_value = blob_service
        blob_service.__aenter__ = AsyncMock(return_value=blob_service)
        blob_service.__aexit__ = AsyncMock(return_value=None)

        source_blob = MagicMock()
        source_blob.url = "https://acct.blob.core.windows.net/incoming-invoices/f.pdf"
        source_blob.delete_blob = AsyncMock()

        dest_blob = MagicMock()
        dest_blob.exists = AsyncMock(return_value=False)
        dest_blob.start_copy_from_url = AsyncMock(return_value={"copy_id": "abc"})
        props = MagicMock()
        props.copy.status = "failed"
        dest_blob.get_blob_properties = AsyncMock(return_value=props)

        blob_service.get_blob_client.side_effect = [source_blob, dest_blob, dest_blob]

        with pytest.raises(StorageError):
            await service.copy_blob_with_normalized_name(
                original_name="f.pdf",
                normalized_name="f.pdf",
            )

        source_blob.delete_blob.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_copy_blob_with_normalized_name_not_found(mock_settings):
    service = BlobStorageService()

    with patch("src.integrations.azure.blob_storage_service.BlobServiceClient") as MockClient:
        blob_service = MagicMock()
        MockClient.from_connection_string.return_value = blob_service
        blob_service.__aenter__ = AsyncMock(return_value=blob_service)
        blob_service.__aexit__ = AsyncMock(return_value=None)

        blob_service.get_blob_client.side_effect = ResourceNotFoundError("not found")

        with pytest.raises(StorageError) as exc:
            await service.copy_blob_with_normalized_name(
                original_name="missing.pdf",
                normalized_name="missing.pdf",
            )

        assert "no encontrado" in str(exc.value).lower()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_copy_blob_with_normalized_name_invalid_names(mock_settings):
    service = BlobStorageService()

    with pytest.raises(StorageError):
        await service.copy_blob_with_normalized_name(original_name="", normalized_name="ok.pdf")

    with pytest.raises(StorageError):
        await service.copy_blob_with_normalized_name(
            original_name="ok.pdf",
            normalized_name=" ",
        )
