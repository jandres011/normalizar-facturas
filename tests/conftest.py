"""
Configuración de fixtures para pytest.

Este módulo proporciona fixtures compartidos para todos los tests.
Sin base de datos - solo procesamiento de documentos.
"""

import asyncio

import pytest


@pytest.fixture(scope="session")
def event_loop():
    """Crea un event loop para toda la sesión de tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()



