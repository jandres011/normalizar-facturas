"""
Tests para blob_processor (Event Grid trigger) enfocados en normalización por nombre.
No se accede al contenido del archivo (solo metadata del evento).
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
import azure.functions as func

from src.core.exceptions import StorageError


@pytest.fixture
def make_event():
    """Factory para construir un EventGridEvent con subject/tipo configurable."""

    def _build(
        subject: str,
        event_type: str = "Microsoft.Storage.BlobCreated",
        data: dict | None = None,
    ) -> func.EventGridEvent:
        return func.EventGridEvent(
            id="test-event-id",
            data=data
            if data is not None
            else {
                "url": f"https://acct.blob.core.windows.net{subject.replace('/blobServices/default/containers', '')}",
                "contentLength": 123,
                "contentType": "application/octet-stream",
                "eTag": "0x8D1234567890",
            },
            topic=(
                "/subscriptions/sub-id/resourceGroups/rg/providers/"
                "Microsoft.Storage/storageAccounts/acct"
            ),
            subject=subject,
            event_type=event_type,
            event_time=datetime.now(timezone.utc),
            data_version="1.0",
        )

    return _build


@pytest.mark.unit
@pytest.mark.asyncio
async def test_event_ignorado_por_tipo_no_relevante(make_event):
    event = make_event(
        subject="/blobServices/default/containers/incoming-invoices/blobs/Factura.pdf",
        event_type="Microsoft.Storage.BlobDeleted",
    )

    with patch("src.functions.blob_processor.function.BlobStorageService") as MockStorage:
        from src.functions.blob_processor.function import normalize_invoice_name

        await normalize_invoice_name(event)

        MockStorage.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_subject_formato_invalido(make_event):
    event = make_event(
        subject="/blobServices/default/containers/incoming-invoices/otro/path",
    )

    with patch("src.functions.blob_processor.function.BlobStorageService") as MockStorage:
        from src.functions.blob_processor.function import normalize_invoice_name

        await normalize_invoice_name(event)

        MockStorage.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_extension_no_permitida_ignorada(make_event):
    event = make_event(
        subject="/blobServices/default/containers/incoming-invoices/blobs/evidencia.txt",
    )

    with patch("src.functions.blob_processor.function.BlobStorageService") as MockStorage:
        mock_storage = AsyncMock()
        mock_storage.copy_blob_with_normalized_name = AsyncMock()
        MockStorage.return_value = mock_storage

        from src.functions.blob_processor.function import normalize_invoice_name

        await normalize_invoice_name(event)

        mock_storage.copy_blob_with_normalized_name.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_nombre_no_normalizable(make_event):
    event = make_event(
        subject="/blobServices/default/containers/incoming-invoices/blobs/!!!.pdf",
    )

    with patch("src.functions.blob_processor.function.BlobStorageService") as MockStorage:
        mock_storage = AsyncMock()
        mock_storage.copy_blob_with_normalized_name = AsyncMock()
        MockStorage.return_value = mock_storage

        from src.functions.blob_processor.function import normalize_invoice_name

        await normalize_invoice_name(event)

        mock_storage.copy_blob_with_normalized_name.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_nombre_ya_normalizado_ignorado(make_event):
    event = make_event(
        subject="/blobServices/default/containers/incoming-invoices/blobs/factura.pdf",
    )

    with patch("src.functions.blob_processor.function.BlobStorageService") as MockStorage:
        mock_storage = AsyncMock()
        mock_storage.copy_blob_with_normalized_name = AsyncMock()
        MockStorage.return_value = mock_storage

        from src.functions.blob_processor.function import normalize_invoice_name

        await normalize_invoice_name(event)

        mock_storage.copy_blob_with_normalized_name.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_normalizacion_exitosa_sin_carpeta(make_event):
    event = make_event(
        subject=(
            "/blobServices/default/containers/incoming-invoices/blobs/"
            "CFDI Ñoño.xml"
        ),
    )

    with patch("src.functions.blob_processor.function.BlobStorageService") as MockStorage:
        mock_storage = AsyncMock()
        mock_storage.incoming_container = "incoming-invoices"
        mock_storage.copy_blob_with_normalized_name = AsyncMock(
            return_value=(
                "https://acct.blob.core.windows.net/incoming-invoices/cfdi_nono.xml"
            )
        )
        MockStorage.return_value = mock_storage

        from src.functions.blob_processor.function import normalize_invoice_name

        await normalize_invoice_name(event)

        mock_storage.copy_blob_with_normalized_name.assert_called_once_with(
            original_name="CFDI Ñoño.xml",
            normalized_name="cfdi_nono.xml",
            source_container="incoming-invoices",
            destination_container="incoming-invoices",
        )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_normalizacion_exitosa_con_carpeta(make_event):
    event = make_event(
        subject=(
            "/blobServices/default/containers/incoming-invoices/blobs/"
            "porvalidar/Factura Enero 2024.PDF"
        ),
    )

    with patch("src.functions.blob_processor.function.BlobStorageService") as MockStorage:
        mock_storage = AsyncMock()
        mock_storage.incoming_container = "incoming-invoices"
        mock_storage.copy_blob_with_normalized_name = AsyncMock(
            return_value=(
                "https://acct.blob.core.windows.net/incoming-invoices/"
                "porvalidar/factura_enero_2024.pdf"
            )
        )
        MockStorage.return_value = mock_storage

        from src.functions.blob_processor.function import normalize_invoice_name

        await normalize_invoice_name(event)

        mock_storage.copy_blob_with_normalized_name.assert_called_once_with(
            original_name="porvalidar/Factura Enero 2024.PDF",
            normalized_name="porvalidar/factura_enero_2024.pdf",
            source_container="incoming-invoices",
            destination_container="incoming-invoices",
        )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_storage_error_mueve_a_failed(make_event):
    event = make_event(
        subject="/blobServices/default/containers/incoming-invoices/blobs/Factura 2026.pdf",
    )

    with patch("src.functions.blob_processor.function.BlobStorageService") as MockStorage:
        mock_storage = AsyncMock()
        mock_storage.incoming_container = "incoming-invoices"
        mock_storage.copy_blob_with_normalized_name = AsyncMock(
            side_effect=StorageError("Fallo en copia")
        )
        mock_storage.move_blob_to_failed = AsyncMock()
        MockStorage.return_value = mock_storage

        from src.functions.blob_processor.function import normalize_invoice_name

        await normalize_invoice_name(event)

        mock_storage.move_blob_to_failed.assert_called_once()
        kwargs = mock_storage.move_blob_to_failed.call_args.kwargs
        assert kwargs["blob_name"] == "Factura 2026.pdf"
        assert kwargs["source_container"] == "incoming-invoices"
        assert "Fallo en copia" in kwargs["error_message"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_storage_error_y_falla_mover_a_failed(make_event):
    event = make_event(
        subject="/blobServices/default/containers/incoming-invoices/blobs/Factura.pdf",
    )

    with patch("src.functions.blob_processor.function.BlobStorageService") as MockStorage:
        mock_storage = AsyncMock()
        mock_storage.incoming_container = "incoming-invoices"
        mock_storage.copy_blob_with_normalized_name = AsyncMock(
            side_effect=StorageError("copy-error")
        )
        mock_storage.move_blob_to_failed = AsyncMock(side_effect=Exception("failed-move"))
        MockStorage.return_value = mock_storage

        from src.functions.blob_processor.function import normalize_invoice_name

        await normalize_invoice_name(event)

        mock_storage.move_blob_to_failed.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_error_inesperado_mueve_a_failed(make_event):
    event = make_event(
        subject="/blobServices/default/containers/incoming-invoices/blobs/Factura.pdf",
    )

    with patch("src.functions.blob_processor.function.BlobStorageService") as MockStorage:
        mock_storage = AsyncMock()
        mock_storage.incoming_container = "incoming-invoices"
        mock_storage.copy_blob_with_normalized_name = AsyncMock(
            side_effect=RuntimeError("boom")
        )
        mock_storage.move_blob_to_failed = AsyncMock()
        MockStorage.return_value = mock_storage

        from src.functions.blob_processor.function import normalize_invoice_name

        await normalize_invoice_name(event)

        mock_storage.move_blob_to_failed.assert_called_once()
        kwargs = mock_storage.move_blob_to_failed.call_args.kwargs
        assert kwargs["blob_name"] == "Factura.pdf"
        assert "RuntimeError" in kwargs["error_message"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_error_inesperado_y_falla_mover_a_failed(make_event):
    event = make_event(
        subject="/blobServices/default/containers/incoming-invoices/blobs/Factura.pdf",
    )

    with patch("src.functions.blob_processor.function.BlobStorageService") as MockStorage:
        mock_storage = AsyncMock()
        mock_storage.incoming_container = "incoming-invoices"
        mock_storage.copy_blob_with_normalized_name = AsyncMock(
            side_effect=RuntimeError("boom")
        )
        mock_storage.move_blob_to_failed = AsyncMock(side_effect=Exception("failed-move"))
        MockStorage.return_value = mock_storage

        from src.functions.blob_processor.function import normalize_invoice_name

        await normalize_invoice_name(event)

        mock_storage.move_blob_to_failed.assert_called_once()
