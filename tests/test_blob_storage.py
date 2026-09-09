"""
Tests para BlobStorageService enfocados en movimiento por nombre.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from azure.core.exceptions import AzureError, ResourceNotFoundError

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

    with patch(
        "src.integrations.azure.blob_storage_service.BlobServiceClient"
    ) as MockClient, patch(
        "src.integrations.azure.blob_storage_service.generate_blob_sas",
        return_value="sv=2023&sig=fake",
    ):
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

    with patch(
        "src.integrations.azure.blob_storage_service.BlobServiceClient"
    ) as MockClient, patch(
        "src.integrations.azure.blob_storage_service.generate_blob_sas",
        return_value="sv=2023&sig=fake",
    ):
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

    with patch(
        "src.integrations.azure.blob_storage_service.BlobServiceClient"
    ) as MockClient, patch(
        "src.integrations.azure.blob_storage_service.generate_blob_sas",
        return_value="sv=2023&sig=fake",
    ):
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
async def test_copy_blob_with_normalized_name_azure_error(mock_settings):
    service = BlobStorageService()

    with patch(
        "src.integrations.azure.blob_storage_service.BlobServiceClient"
    ) as MockClient, patch(
        "src.integrations.azure.blob_storage_service.generate_blob_sas",
        return_value="sv=2023&sig=fake",
    ):
        blob_service = MagicMock()
        MockClient.from_connection_string.return_value = blob_service
        blob_service.__aenter__ = AsyncMock(return_value=blob_service)
        blob_service.__aexit__ = AsyncMock(return_value=None)

        source_blob = MagicMock()
        source_blob.delete_blob = AsyncMock()

        dest_blob = MagicMock()
        dest_blob.exists = AsyncMock(return_value=False)
        dest_blob.start_copy_from_url = AsyncMock(side_effect=AzureError("azure boom"))

        blob_service.get_blob_client.side_effect = [source_blob, dest_blob, dest_blob]

        with pytest.raises(StorageError) as exc:
            await service.copy_blob_with_normalized_name(
                original_name="f.pdf",
                normalized_name="f.pdf",
            )

        assert "azure boom" in str(exc.value)
        source_blob.delete_blob.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_copy_blob_with_normalized_name_unexpected_error(mock_settings):
    service = BlobStorageService()

    with patch(
        "src.integrations.azure.blob_storage_service.BlobServiceClient"
    ) as MockClient, patch(
        "src.integrations.azure.blob_storage_service.generate_blob_sas",
        return_value="sv=2023&sig=fake",
    ):
        blob_service = MagicMock()
        MockClient.from_connection_string.return_value = blob_service
        blob_service.__aenter__ = AsyncMock(return_value=blob_service)
        blob_service.__aexit__ = AsyncMock(return_value=None)

        source_blob = MagicMock()
        source_blob.delete_blob = AsyncMock()

        dest_blob = MagicMock()
        dest_blob.exists = AsyncMock(return_value=False)
        dest_blob.start_copy_from_url = AsyncMock(side_effect=ValueError("unexpected"))

        blob_service.get_blob_client.side_effect = [source_blob, dest_blob, dest_blob]

        with pytest.raises(StorageError) as exc:
            await service.copy_blob_with_normalized_name(
                original_name="f.pdf",
                normalized_name="f.pdf",
            )

        assert "unexpected" in str(exc.value)
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


@pytest.mark.unit
def test_split_filename_variants(mock_settings):
    service = BlobStorageService()

    assert service._split_filename("factura.pdf") == ("factura", ".pdf")
    assert service._split_filename("archivo_sin_extension") == (
        "archivo_sin_extension",
        "",
    )
    assert service._split_filename(".hidden") == (".hidden", "")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_resolve_available_destination_name_exhausted(mock_settings):
    service = BlobStorageService()

    blob_service = MagicMock()
    always_exists = MagicMock()
    always_exists.exists = AsyncMock(return_value=True)
    blob_service.get_blob_client.return_value = always_exists

    with pytest.raises(StorageError):
        await service._resolve_available_destination_name(
            blob_service=blob_service,
            destination_container="normalized-invoices",
            normalized_name="factura.pdf",
        )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_wait_for_copy_success_timeout(mock_settings):
    service = BlobStorageService()

    dest_blob = MagicMock()
    props = MagicMock()
    props.copy.status = "pending"
    dest_blob.get_blob_properties = AsyncMock(return_value=props)

    with pytest.raises(StorageError):
        await service._wait_for_copy_success(
            dest_blob, "factura.pdf", max_attempts=2, delay=0
        )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_move_blob_to_archive_success(mock_settings):
    service = BlobStorageService()

    with patch.object(
        service,
        "copy_blob_with_normalized_name",
        new=AsyncMock(
            return_value="https://acct.blob.core.windows.net/normalized-invoices/factura.pdf"
        ),
    ) as mock_copy:
        result = await service.move_blob_to_archive("factura.pdf")

        mock_copy.assert_called_once_with(
            original_name="factura.pdf",
            normalized_name="factura.pdf",
            source_container="incoming-invoices",
            destination_container="normalized-invoices",
        )
        assert result.endswith("factura.pdf")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_move_blob_to_failed_success_with_metadata(mock_settings):
    service = BlobStorageService()

    with patch(
        "src.integrations.azure.blob_storage_service.BlobServiceClient"
    ) as MockClient, patch(
        "src.integrations.azure.blob_storage_service.generate_blob_sas",
        return_value="sv=2023&sig=fake",
    ):
        blob_service = MagicMock()
        MockClient.from_connection_string.return_value = blob_service
        blob_service.__aenter__ = AsyncMock(return_value=blob_service)
        blob_service.__aexit__ = AsyncMock(return_value=None)

        source_blob = MagicMock()
        source_blob.delete_blob = AsyncMock()

        dest_blob = MagicMock()
        dest_blob.url = "https://acct.blob.core.windows.net/invoices-failed/factura.pdf"
        dest_blob.start_copy_from_url = AsyncMock(return_value={"copy_id": "abc"})
        dest_blob.set_blob_metadata = AsyncMock()
        props = MagicMock()
        props.copy.status = "success"
        dest_blob.get_blob_properties = AsyncMock(return_value=props)

        blob_service.get_blob_client.side_effect = [source_blob, dest_blob]

        result = await service.move_blob_to_failed(
            blob_name="factura.pdf",
            error_message="Algo falló durante la copia",
        )

        assert result == dest_blob.url
        dest_blob.set_blob_metadata.assert_called_once_with(
            {"error_message": "Algo falló durante la copia"}
        )
        source_blob.delete_blob.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_move_blob_to_failed_error(mock_settings):
    service = BlobStorageService()

    with patch("src.integrations.azure.blob_storage_service.BlobServiceClient") as MockClient:
        MockClient.from_connection_string.side_effect = RuntimeError("boom")

        with pytest.raises(StorageError):
            await service.move_blob_to_failed(blob_name="factura.pdf")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_read_blob_success(mock_settings):
    service = BlobStorageService()

    with patch("src.integrations.azure.blob_storage_service.BlobServiceClient") as MockClient:
        blob_service = MagicMock()
        MockClient.from_connection_string.return_value = blob_service
        blob_service.__aenter__ = AsyncMock(return_value=blob_service)
        blob_service.__aexit__ = AsyncMock(return_value=None)

        blob_data = MagicMock()
        blob_data.readall = AsyncMock(return_value=b"contenido")

        blob_client = MagicMock()
        blob_client.download_blob = AsyncMock(return_value=blob_data)
        blob_service.get_blob_client.return_value = blob_client

        result = await service.read_blob("factura.pdf")

        assert result == b"contenido"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_read_blob_not_found(mock_settings):
    service = BlobStorageService()

    with patch("src.integrations.azure.blob_storage_service.BlobServiceClient") as MockClient:
        blob_service = MagicMock()
        MockClient.from_connection_string.return_value = blob_service
        blob_service.__aenter__ = AsyncMock(return_value=blob_service)
        blob_service.__aexit__ = AsyncMock(return_value=None)

        blob_service.get_blob_client.side_effect = ResourceNotFoundError("not found")

        with pytest.raises(StorageError) as exc:
            await service.read_blob("missing.pdf", container_name="incoming-invoices")

        assert "no encontrado" in str(exc.value).lower()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_read_blob_unexpected_error(mock_settings):
    service = BlobStorageService()

    with patch("src.integrations.azure.blob_storage_service.BlobServiceClient") as MockClient:
        MockClient.from_connection_string.side_effect = RuntimeError("boom")

        with pytest.raises(StorageError):
            await service.read_blob("factura.pdf")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_blob_url(mock_settings):
    service = BlobStorageService()

    with patch("src.integrations.azure.blob_storage_service.BlobServiceClient") as MockClient:
        blob_service = MagicMock()
        MockClient.from_connection_string.return_value = blob_service
        blob_service.__aenter__ = AsyncMock(return_value=blob_service)
        blob_service.__aexit__ = AsyncMock(return_value=None)

        blob_client = MagicMock()
        blob_client.url = "https://acct.blob.core.windows.net/incoming-invoices/factura.pdf"
        blob_service.get_blob_client.return_value = blob_client

        result = await service.get_blob_url("factura.pdf", "incoming-invoices")

        assert result == blob_client.url
