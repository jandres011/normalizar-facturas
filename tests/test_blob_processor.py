"""
Tests para blob_processor enfocados en normalización por nombre.
No se accede al contenido del archivo (solo string del nombre).
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

import azure.functions as func

from src.core.exceptions import StorageError


@pytest.fixture
def make_blob():
    """Factory para construir InputStream mock con nombre configurable."""

    def _build(name: str):
        blob = MagicMock(spec=func.InputStream)
        blob.name = f"incoming-invoices/{name}"
        blob.length = 123
        blob.uri = f"https://acct.blob.core.windows.net/incoming-invoices/{name}"
        blob.read = MagicMock(side_effect=AssertionError("No se debe leer contenido"))
        return blob

    return _build


@pytest.mark.unit
@pytest.mark.asyncio
async def test_blob_trigger_pdf_valido(make_blob):
    blob = make_blob("Factura Enero 2024.PDF")

    with patch("src.functions.blob_processor.function.BlobStorageService") as MockStorage:
        mock_storage = AsyncMock()
        mock_storage.incoming_container = "incoming-invoices"
        mock_storage.archived_container = "normalized-invoices"
        mock_storage.copy_blob_with_normalized_name = AsyncMock(
            return_value=(
                "https://acct.blob.core.windows.net/normalized-invoices/"
                "factura_enero_2024.pdf"
            )
        )
        MockStorage.return_value = mock_storage

        from src.functions.blob_processor.function import normalize_invoice_name

        await normalize_invoice_name(blob)

        mock_storage.copy_blob_with_normalized_name.assert_called_once_with(
            original_name="Factura Enero 2024.PDF",
            normalized_name="factura_enero_2024.pdf",
            source_container="incoming-invoices",
            destination_container="normalized-invoices",
        )
        blob.read.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_blob_trigger_xml_valido(make_blob):
    blob = make_blob("CFDI Ñoño.xml")

    with patch("src.functions.blob_processor.function.BlobStorageService") as MockStorage:
        mock_storage = AsyncMock()
        mock_storage.incoming_container = "incoming-invoices"
        mock_storage.archived_container = "normalized-invoices"
        mock_storage.copy_blob_with_normalized_name = AsyncMock(
            return_value=(
                "https://acct.blob.core.windows.net/normalized-invoices/"
                "cfdi_nono.xml"
            )
        )
        MockStorage.return_value = mock_storage

        from src.functions.blob_processor.function import normalize_invoice_name

        await normalize_invoice_name(blob)

        mock_storage.copy_blob_with_normalized_name.assert_called_once_with(
            original_name="CFDI Ñoño.xml",
            normalized_name="cfdi_nono.xml",
            source_container="incoming-invoices",
            destination_container="normalized-invoices",
        )
        blob.read.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_blob_trigger_extension_invalida_ignorada(make_blob):
    blob = make_blob("evidencia.txt")

    with patch("src.functions.blob_processor.function.BlobStorageService") as MockStorage:
        mock_storage = AsyncMock()
        mock_storage.copy_blob_with_normalized_name = AsyncMock()
        MockStorage.return_value = mock_storage

        from src.functions.blob_processor.function import normalize_invoice_name

        await normalize_invoice_name(blob)

        mock_storage.copy_blob_with_normalized_name.assert_not_called()
        blob.read.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_blob_trigger_archivo_duplicado_resuelto(make_blob):
    blob = make_blob("Factura.xml")

    with patch("src.functions.blob_processor.function.BlobStorageService") as MockStorage:
        mock_storage = AsyncMock()
        mock_storage.incoming_container = "incoming-invoices"
        mock_storage.archived_container = "normalized-invoices"
        mock_storage.copy_blob_with_normalized_name = AsyncMock(
            return_value=(
                "https://acct.blob.core.windows.net/normalized-invoices/"
                "factura_1.xml"
            )
        )
        MockStorage.return_value = mock_storage

        from src.functions.blob_processor.function import normalize_invoice_name

        await normalize_invoice_name(blob)

        mock_storage.copy_blob_with_normalized_name.assert_called_once_with(
            original_name="Factura.xml",
            normalized_name="factura.xml",
            source_container="incoming-invoices",
            destination_container="normalized-invoices",
        )
        blob.read.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_blob_trigger_error_en_copia_mueve_a_failed(make_blob):
    blob = make_blob("Factura 2026.pdf")

    with patch("src.functions.blob_processor.function.BlobStorageService") as MockStorage:
        mock_storage = AsyncMock()
        mock_storage.incoming_container = "incoming-invoices"
        mock_storage.archived_container = "normalized-invoices"
        mock_storage.copy_blob_with_normalized_name = AsyncMock(
            side_effect=StorageError("Fallo en copia")
        )
        mock_storage.move_blob_to_failed = AsyncMock()
        MockStorage.return_value = mock_storage

        from src.functions.blob_processor.function import normalize_invoice_name

        await normalize_invoice_name(blob)

        mock_storage.move_blob_to_failed.assert_called_once()
        call_kwargs = mock_storage.move_blob_to_failed.call_args.kwargs
        assert call_kwargs["blob_name"] == "Factura 2026.pdf"
        assert call_kwargs["source_container"] == "incoming-invoices"
        assert "Fallo en copia" in call_kwargs["error_message"]
        blob.read.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_blob_trigger_nombre_no_normalizable(make_blob):
    blob = make_blob("   .pdf")

    with patch("src.functions.blob_processor.function.BlobStorageService") as MockStorage:
        mock_storage = AsyncMock()
        mock_storage.copy_blob_with_normalized_name = AsyncMock()
        MockStorage.return_value = mock_storage

        from src.functions.blob_processor.function import normalize_invoice_name

        await normalize_invoice_name(blob)

        mock_storage.copy_blob_with_normalized_name.assert_not_called()
        blob.read.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_blob_trigger_error_inesperado_mueve_a_failed(make_blob):
    blob = make_blob("factura.pdf")

    with patch("src.functions.blob_processor.function.BlobStorageService") as MockStorage:
        mock_storage = AsyncMock()
        mock_storage.incoming_container = "incoming-invoices"
        mock_storage.archived_container = "normalized-invoices"
        mock_storage.copy_blob_with_normalized_name = AsyncMock(
            side_effect=RuntimeError("boom")
        )
        mock_storage.move_blob_to_failed = AsyncMock()
        MockStorage.return_value = mock_storage

        from src.functions.blob_processor.function import normalize_invoice_name

        await normalize_invoice_name(blob)

        mock_storage.move_blob_to_failed.assert_called_once()
        kwargs = mock_storage.move_blob_to_failed.call_args.kwargs
        assert kwargs["blob_name"] == "factura.pdf"
        assert "RuntimeError" in kwargs["error_message"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_blob_trigger_error_inesperado_y_falla_failed(make_blob):
    blob = make_blob("factura.pdf")

    with patch("src.functions.blob_processor.function.BlobStorageService") as MockStorage:
        mock_storage = AsyncMock()
        mock_storage.incoming_container = "incoming-invoices"
        mock_storage.archived_container = "normalized-invoices"
        mock_storage.copy_blob_with_normalized_name = AsyncMock(
            side_effect=RuntimeError("boom")
        )
        mock_storage.move_blob_to_failed = AsyncMock(side_effect=Exception("failed-move"))
        MockStorage.return_value = mock_storage

        from src.functions.blob_processor.function import normalize_invoice_name

        await normalize_invoice_name(blob)

        mock_storage.move_blob_to_failed.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_blob_trigger_storage_error_y_falla_failed(make_blob):
    blob = make_blob("factura.pdf")

    with patch("src.functions.blob_processor.function.BlobStorageService") as MockStorage:
        mock_storage = AsyncMock()
        mock_storage.incoming_container = "incoming-invoices"
        mock_storage.archived_container = "normalized-invoices"
        mock_storage.copy_blob_with_normalized_name = AsyncMock(
            side_effect=StorageError("copy-error")
        )
        mock_storage.move_blob_to_failed = AsyncMock(side_effect=Exception("failed-move"))
        MockStorage.return_value = mock_storage

        from src.functions.blob_processor.function import normalize_invoice_name

        await normalize_invoice_name(blob)

        mock_storage.move_blob_to_failed.assert_called_once()
