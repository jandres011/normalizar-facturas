"""Tests para utilidades de normalizacion de nombres."""

import pytest

from src.utils.name_normalizer import normalize_blob_name, normalize_blob_path


@pytest.mark.unit
def test_normalize_blob_name_sin_extension():
    assert normalize_blob_name("Factura Enero 2024") == "factura_enero_2024"


@pytest.mark.unit
def test_normalize_blob_name_vacio_lanza_error():
    with pytest.raises(ValueError):
        normalize_blob_name("")


@pytest.mark.unit
def test_normalize_blob_name_resultado_vacio_lanza_error():
    with pytest.raises(ValueError):
        normalize_blob_name("!!!.pdf")


@pytest.mark.unit
def test_normalize_blob_path_con_carpetas_y_segmentos_vacios():
    result = normalize_blob_path("Proveedor ABC//FacturA   Final.XML")
    assert result == "proveedor_abc/factura_final.xml"


@pytest.mark.unit
def test_normalize_blob_path_sin_separador():
    assert normalize_blob_path("CFDI Ñandú.xml") == "cfdi_nandu.xml"
