"""
Utilidad para normalización de nombres de archivos de facturas.

Convierte nombres de blobs a formato estandarizado:
- Todo en minúsculas
- Espacios reemplazados por guión bajo
- Caracteres especiales (acentos, ñ) transliterados a ASCII
- Caracteres no alfanuméricos (excepto guión, punto, guión bajo) eliminados
"""

import re
import unicodedata


def normalize_blob_name(name: str) -> str:
    """
    Normaliza el nombre de un blob de factura.

    Transformaciones aplicadas en orden:
    1. Separar extensión para preservarla
    2. Transliterar caracteres Unicode (acentos, ñ) a ASCII
    3. Convertir a minúsculas
    4. Reemplazar espacios y guiones por guión bajo
    5. Eliminar caracteres que no sean alfanuméricos, guión o punto
    6. Colapsar múltiples guiones bajos consecutivos en uno solo
    7. Limpiar guiones bajos al inicio/fin del stem

    Args:
        name: Nombre original del blob (puede incluir ruta parcial)

    Returns:
        Nombre normalizado, preservando la extensión original

    Examples:
        >>> normalize_blob_name("Factura Enero 2024.pdf")
        'factura_enero_2024.pdf'
        >>> normalize_blob_name("CFDI Ñoño S.A. de C.V..xml")
        'cfdi_nono_s.a._de_c.v..xml'
        >>> normalize_blob_name("  Factura   con   Espacios  .PDF")
        'factura_con_espacios_.pdf'
    """
    if not name or not name.strip():
        raise ValueError("El nombre del blob no puede estar vacío")

    # Separar extensión (todo lo que viene después del último punto)
    dot_index = name.rfind(".")
    if dot_index > 0:
        stem = name[:dot_index]
        extension = name[dot_index:].lower()  # extensión siempre en minúsculas
    else:
        stem = name
        extension = ""

    # 1. Transliterar Unicode → ASCII (maneja acentos, ñ, ü, etc.)
    normalized = unicodedata.normalize("NFKD", stem)
    ascii_stem = normalized.encode("ascii", errors="ignore").decode("ascii")

    # 2. Minúsculas
    lower_stem = ascii_stem.lower()

    # 3. Espacios y guiones → guión bajo
    underscored = re.sub(r"[\s\-]+", "_", lower_stem)

    # 4. Eliminar caracteres no permitidos (mantener alfanuméricos, _, .)
    clean_stem = re.sub(r"[^\w.]", "", underscored)

    # 5. Colapsar múltiples guiones bajos consecutivos
    collapsed = re.sub(r"_{2,}", "_", clean_stem)

    # 6. Limpiar guiones bajos al inicio y fin del stem
    final_stem = collapsed.strip("_")

    if not final_stem:
        raise ValueError(
            f"El nombre '{name}' resultó vacío después de la normalización"
        )

    return final_stem + extension


def normalize_blob_path(path: str) -> str:
    """
    Normaliza un path completo de blob, preservando la estructura de carpetas.

    Útil cuando el blob trigger entrega un path con subdirectorios
    (ej: 'proveedor_abc/Factura Enero.pdf').

    Args:
        path: Path completo del blob (puede incluir '/')

    Returns:
        Path con cada segmento normalizado individualmente

    Examples:
        >>> normalize_blob_path("Proveedor ABC/Factura Enero 2024.pdf")
        'proveedor_abc/factura_enero_2024.pdf'
    """
    if "/" not in path:
        return normalize_blob_name(path)

    parts = path.split("/")
    normalized_parts = []
    for i, part in enumerate(parts):
        if not part:
            continue
        # El último segmento es el nombre de archivo (preserva extensión)
        # Los segmentos anteriores son carpetas (sin extensión a preservar)
        normalized_parts.append(normalize_blob_name(part))

    return "/".join(normalized_parts)