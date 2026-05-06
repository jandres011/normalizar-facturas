"""
Manejo centralizado de excepciones y errores personalizados.

Este módulo define excepciones personalizadas para Azure Functions
siguiendo las mejores prácticas de manejo de errores.
"""

from typing import Any, Dict


class AppException(Exception):
    """Excepción base para errores de la aplicación."""

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: str = "INTERNAL_ERROR",
        details: Dict[str, Any] | None = None,
    ):
        """
        Inicializa la excepción.

        Args:
            message: Mensaje de error
            status_code: Código de estado HTTP
            error_code: Código de error personalizado
            details: Detalles adicionales del error
        """
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class ValidationException(AppException):
    """Excepción para errores de validación."""

    def __init__(
        self,
        message: str = "Datos de entrada inválidos",
        details: Dict[str, Any] | None = None,
    ):
        """
        Inicializa la excepción de validación.

        Args:
            message: Mensaje de error
            details: Detalles de validación
        """
        super().__init__(
            message=message,
            status_code=400,
            error_code="VALIDATION_ERROR",
            details=details,
        )


class UnauthorizedException(AppException):
    """Excepción para errores de autenticación."""

    def __init__(
        self,
        message: str = "Credenciales inválidas",
        details: Dict[str, Any] | None = None,
    ):
        """
        Inicializa la excepción de autenticación.

        Args:
            message: Mensaje de error
            details: Detalles del error
        """
        super().__init__(
            message=message,
            status_code=401,
            error_code="UNAUTHORIZED",
            details=details,
        )


class ForbiddenException(AppException):
    """Excepción para errores de autorización."""

    def __init__(
        self,
        message: str = "Acceso denegado",
        details: Dict[str, Any] | None = None,
    ):
        """
        Inicializa la excepción de autorización.

        Args:
            message: Mensaje de error
            details: Detalles del error
        """
        super().__init__(
            message=message,
            status_code=403,
            error_code="FORBIDDEN",
            details=details,
        )


class NotFoundException(AppException):
    """Excepción para recursos no encontrados."""

    def __init__(
        self,
        message: str = "Recurso no encontrado",
        details: Dict[str, Any] | None = None,
    ):
        """
        Inicializa la excepción de recurso no encontrado.

        Args:
            message: Mensaje de error
            details: Detalles del error
        """
        super().__init__(
            message=message,
            status_code=404,
            error_code="NOT_FOUND",
            details=details,
        )


class ConflictException(AppException):
    """Excepción para conflictos de recursos."""

    def __init__(
        self,
        message: str = "El recurso ya existe",
        details: Dict[str, Any] | None = None,
    ):
        """
        Inicializa la excepción de conflicto.

        Args:
            message: Mensaje de error
            details: Detalles del error
        """
        super().__init__(
            message=message,
            status_code=409,
            error_code="CONFLICT",
            details=details,
        )


class DatabaseException(AppException):
    """Excepción para errores de base de datos."""

    def __init__(
        self,
        message: str = "Error de base de datos",
        details: Dict[str, Any] | None = None,
    ):
        """
        Inicializa la excepción de base de datos.

        Args:
            message: Mensaje de error
            details: Detalles del error
        """
        super().__init__(
            message=message,
            status_code=500,
            error_code="DATABASE_ERROR",
            details=details,
        )


class ExternalServiceException(AppException):
    """Excepción para errores de servicios externos."""

    def __init__(
        self,
        message: str = "Error en servicio externo",
        service_name: str = "unknown",
        details: Dict[str, Any] | None = None,
    ):
        """
        Inicializa la excepción de servicio externo.

        Args:
            message: Mensaje de error
            service_name: Nombre del servicio externo
            details: Detalles del error
        """
        error_details = details or {}
        error_details["service"] = service_name

        super().__init__(
            message=message,
            status_code=502,
            error_code="EXTERNAL_SERVICE_ERROR",
            details=error_details,
        )


class ExternalAPIError(AppException):
    """Excepción para errores al comunicarse con API externa."""

    def __init__(
        self,
        message: str = "Error al comunicarse con API externa",
        details: Dict[str, Any] | None = None,
    ):
        """
        Inicializa la excepción de API externa.

        Args:
            message: Mensaje de error
            details: Detalles del error
        """
        super().__init__(
            message=message,
            status_code=502,
            error_code="EXTERNAL_API_ERROR",
            details=details,
        )


class StorageError(AppException):
    """Excepción para errores de Azure Storage."""

    def __init__(
        self,
        message: str = "Error al operar con Azure Storage",
        details: Dict[str, Any] | None = None,
    ):
        """
        Inicializa la excepción de storage.

        Args:
            message: Mensaje de error
            details: Detalles del error
        """
        super().__init__(
            message=message,
            status_code=500,
            error_code="STORAGE_ERROR",
            details=details,
        )


class DocumentIntelligenceException(AppException):
    """Excepción para errores de Azure Document Intelligence."""

    def __init__(
        self,
        message: str = "Error al procesar documento",
        details: Dict[str, Any] | None = None,
    ):
        """
        Inicializa la excepción de Document Intelligence.

        Args:
            message: Mensaje de error
            details: Detalles del error
        """
        super().__init__(
            message=message,
            status_code=500,
            error_code="DOCUMENT_INTELLIGENCE_ERROR",
            details=details,
        )
