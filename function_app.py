"""
Azure Function App - Punto de entrada principal.

Este módulo configura las Azure Functions HTTP usando el programming model v2.
Implementa Clean Architecture con todas las mejores prácticas del proyecto template.python.back,
adaptado para Azure Functions con soporte para Azure Document Intelligence.
"""

import logging
import sys
from pathlib import Path
import azure.functions as func

# IMPORTANTE: Agregar src/ al PYTHONPATH para imports
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.core.logging import setup_logging
from src.functions.blob_processor.function import bp as blob_processor_bp

# Configurar logging estructurado
setup_logging()
logger = logging.getLogger(__name__)

# Crear la instancia de la Function App
app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

# Registrar blueprints del modelo v2
app.register_functions(blob_processor_bp)


logger.info("Azure Function App inicializada con blob processor")
