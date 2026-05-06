"""
Configuración de logging estructurado para Azure Functions.

Este módulo configura structlog para proporcionar logging estructurado
con formato JSON y manejo seguro de información sensible.
"""

import logging
import sys
from typing import Any, Dict

import structlog
from pythonjsonlogger import jsonlogger

from src.core.config.settings import get_settings


def setup_logging() -> None:
    """
    Configura el sistema de logging estructurado.

    Configura structlog con procesadores para logging seguro,
    formato JSON y filtrado de información sensible.
    """
    settings = get_settings()

    # Configurar logging estándar de Python
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level),
    )

    # Configurar procesadores de structlog
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        _filter_sensitive_data,
        _add_invocation_id,
    ]

    if settings.log_format == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        context_class=dict,
        cache_logger_on_first_use=True,
    )


def _filter_sensitive_data(
    logger: Any, method_name: str, event_dict: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Filtra información sensible de los logs.

    Args:
        logger: Logger instance
        method_name: Nombre del método de logging
        event_dict: Diccionario con datos del evento

    Returns:
        Dict[str, Any]: Diccionario filtrado
    """
    sensitive_keys = {
        "password",
        "token",
        "secret",
        "key",
        "authorization",
        "jwt",
        "api_key",
        "client_secret",
        "db_password",
        "document_intelligence_key",
    }

    def _is_sensitive_key(key: str) -> bool:
        """Verifica si una clave es sensible."""
        return isinstance(key, str) and any(
            sensitive in key.lower() for sensitive in sensitive_keys
        )

    def _mask_value(key: str, value: Any) -> Any:
        """Enmascara valores sensibles."""
        if not _is_sensitive_key(key):
            return value
        if isinstance(value, str) and len(value) > 4:
            return f"{value[:2]}***{value[-2:]}"
        return "***"

    def _filter_list(key: str, items: list) -> list:
        """Filtra una lista de elementos."""
        return [
            _filter_dict(item) if isinstance(item, dict) else _mask_value(key, item)
            for item in items
        ]

    def _filter_dict(data: Dict[str, Any]) -> Dict[str, Any]:
        """Filtra recursivamente un diccionario."""
        filtered = {}
        for k, v in data.items():
            if isinstance(v, dict):
                filtered[k] = _filter_dict(v)
            elif isinstance(v, list):
                filtered[k] = _filter_list(k, v)
            else:
                filtered[k] = _mask_value(k, v)
        return filtered

    return _filter_dict(event_dict)


def _add_invocation_id(
    logger: Any, method_name: str, event_dict: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Añade ID de invocación a los logs si está disponible.

    Args:
        logger: Logger instance
        method_name: Nombre del método de logging
        event_dict: Diccionario con datos del evento

    Returns:
        Dict[str, Any]: Diccionario con invocation_id añadido
    """
    # Intentar obtener invocation_id del contexto
    import contextvars

    try:
        invocation_id_var = contextvars.ContextVar("invocation_id", default=None)
        invocation_id = invocation_id_var.get()
        if invocation_id:
            event_dict["invocation_id"] = invocation_id
    except Exception:
        pass  # Si no hay contexto, continuar sin invocation_id

    return event_dict


def get_logger(name: str = None) -> structlog.BoundLogger:
    """
    Obtiene un logger estructurado.

    Args:
        name: Nombre del logger (opcional)

    Returns:
        structlog.BoundLogger: Logger configurado
    """
    return structlog.get_logger(name)


class SecurityLogger:
    """
    Logger especializado para eventos de seguridad.

    Proporciona métodos específicos para registrar eventos
    relacionados con seguridad de manera consistente.
    """

    def __init__(self) -> None:
        """Inicializa el logger de seguridad."""
        self.logger = get_logger("security")

    def log_authentication_attempt(
        self, username: str, success: bool, ip_address: str = None
    ) -> None:
        """
        Registra un intento de autenticación.

        Args:
            username: Nombre de usuario
            success: Si la autenticación fue exitosa
            ip_address: Dirección IP del cliente
        """
        self.logger.info(
            "authentication_attempt",
            username=username,
            success=success,
            ip_address=ip_address,
        )

    def log_authorization_failure(
        self, username: str, resource: str, action: str
    ) -> None:
        """
        Registra un fallo de autorización.

        Args:
            username: Nombre de usuario
            resource: Recurso al que se intentó acceder
            action: Acción que se intentó realizar
        """
        self.logger.warning(
            "authorization_failure",
            username=username,
            resource=resource,
            action=action,
        )

    def log_suspicious_activity(
        self, activity_type: str, details: Dict[str, Any]
    ) -> None:
        """
        Registra actividad sospechosa.

        Args:
            activity_type: Tipo de actividad sospechosa
            details: Detalles adicionales
        """
        self.logger.warning(
            "suspicious_activity",
            activity_type=activity_type,
            details=details,
        )
