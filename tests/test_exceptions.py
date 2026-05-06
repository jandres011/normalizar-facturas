"""
Tests para excepciones personalizadas.
"""

import pytest
from src.core.exceptions import (
    AppException,
    ValidationException,
    UnauthorizedException,
    ForbiddenException,
    NotFoundException,
    ConflictException,
    DatabaseException,
    ExternalServiceException,
    ExternalAPIError,
    StorageError,
    DocumentIntelligenceException,
)


@pytest.mark.unit
def test_app_exception_default():
    """Test excepción base con valores por defecto."""
    exc = AppException("Test error")
    
    assert str(exc) == "Test error"
    assert exc.message == "Test error"
    assert exc.status_code == 500
    assert exc.error_code == "INTERNAL_ERROR"
    assert exc.details == {}


@pytest.mark.unit
def test_app_exception_custom():
    """Test excepción base con valores personalizados."""
    details = {"field": "email", "reason": "invalid"}
    exc = AppException(
        message="Custom error",
        status_code=400,
        error_code="CUSTOM_ERROR",
        details=details
    )
    
    assert exc.message == "Custom error"
    assert exc.status_code == 400
    assert exc.error_code == "CUSTOM_ERROR"
    assert exc.details == details


@pytest.mark.unit
def test_validation_exception():
    """Test excepción de validación."""
    exc = ValidationException("Invalid input")
    
    assert exc.message == "Invalid input"
    assert exc.status_code == 400
    assert exc.error_code == "VALIDATION_ERROR"


@pytest.mark.unit
def test_validation_exception_with_details():
    """Test excepción de validación con detalles."""
    details = {"errors": [{"field": "name", "message": "Required"}]}
    exc = ValidationException("Validation failed", details=details)
    
    assert exc.details == details


@pytest.mark.unit
def test_unauthorized_exception():
    """Test excepción de no autorizado."""
    exc = UnauthorizedException()
    
    assert exc.message == "Credenciales inválidas"
    assert exc.status_code == 401
    assert exc.error_code == "UNAUTHORIZED"


@pytest.mark.unit
def test_unauthorized_exception_custom_message():
    """Test excepción unauthorized con mensaje personalizado."""
    exc = UnauthorizedException("Token expired")
    
    assert exc.message == "Token expired"
    assert exc.status_code == 401


@pytest.mark.unit
def test_forbidden_exception():
    """Test excepción de acceso denegado."""
    exc = ForbiddenException()
    
    assert exc.message == "Acceso denegado"
    assert exc.status_code == 403
    assert exc.error_code == "FORBIDDEN"


@pytest.mark.unit
def test_forbidden_exception_custom():
    """Test forbidden con mensaje custom."""
    exc = ForbiddenException("Insufficient permissions")
    
    assert exc.message == "Insufficient permissions"


@pytest.mark.unit
def test_not_found_exception():
    """Test excepción de recurso no encontrado."""
    exc = NotFoundException()
    
    assert exc.message == "Recurso no encontrado"
    assert exc.status_code == 404
    assert exc.error_code == "NOT_FOUND"


@pytest.mark.unit
def test_not_found_exception_custom():
    """Test not found con recurso específico."""
    exc = NotFoundException("User not found")
    
    assert exc.message == "User not found"
    assert exc.status_code == 404


@pytest.mark.unit
def test_conflict_exception():
    """Test excepción de conflicto."""
    exc = ConflictException()
    
    assert exc.message == "El recurso ya existe"
    assert exc.status_code == 409
    assert exc.error_code == "CONFLICT"


@pytest.mark.unit
def test_conflict_exception_custom():
    """Test conflict con mensaje custom."""
    exc = ConflictException("Email already exists")
    
    assert exc.message == "Email already exists"


@pytest.mark.unit
def test_database_exception():
    """Test excepción de base de datos."""
    exc = DatabaseException()
    
    assert exc.message == "Error de base de datos"
    assert exc.status_code == 500
    assert exc.error_code == "DATABASE_ERROR"


@pytest.mark.unit
def test_database_exception_with_details():
    """Test database exception con detalles."""
    details = {"query": "SELECT * FROM users", "error": "Connection lost"}
    exc = DatabaseException("Query failed", details=details)
    
    assert exc.message == "Query failed"
    assert exc.details == details


@pytest.mark.unit
def test_external_service_exception():
    """Test excepción de servicio externo."""
    exc = ExternalServiceException(
        message="Service unavailable",
        service_name="PaymentGateway"
    )
    
    assert exc.message == "Service unavailable"
    assert exc.status_code == 502
    assert exc.error_code == "EXTERNAL_SERVICE_ERROR"
    assert exc.details["service"] == "PaymentGateway"


@pytest.mark.unit
def test_external_service_exception_default_service():
    """Test external service con nombre por defecto."""
    exc = ExternalServiceException()
    
    assert exc.details["service"] == "unknown"


@pytest.mark.unit
def test_external_api_error():
    """Test excepción de API externa."""
    exc = ExternalAPIError("API request failed")
    
    assert exc.message == "API request failed"
    assert exc.status_code == 502
    assert exc.error_code == "EXTERNAL_API_ERROR"


@pytest.mark.unit
def test_external_api_error_default():
    """Test external API error con mensaje por defecto."""
    exc = ExternalAPIError()
    
    assert "API externa" in exc.message


@pytest.mark.unit
def test_storage_error():
    """Test excepción de storage."""
    exc = StorageError("Blob not found")
    
    assert exc.message == "Blob not found"
    assert exc.status_code == 500
    assert exc.error_code == "STORAGE_ERROR"


@pytest.mark.unit
def test_storage_error_default():
    """Test storage error con mensaje por defecto."""
    exc = StorageError()
    
    assert "Storage" in exc.message


@pytest.mark.unit
def test_document_intelligence_exception_default():
    """Test excepción de Document Intelligence con valores por defecto."""
    exc = DocumentIntelligenceException()

    assert "documento" in exc.message.lower()
    assert exc.status_code == 500
    assert exc.error_code == "DOCUMENT_INTELLIGENCE_ERROR"


@pytest.mark.unit
def test_exception_inheritance():
    """Test que todas las excepciones heredan de AppException."""
    exceptions = [
        ValidationException(),
        UnauthorizedException(),
        ForbiddenException(),
        NotFoundException(),
        ConflictException(),
        DatabaseException(),
        ExternalServiceException(),
        ExternalAPIError(),
        StorageError(),
    ]
    
    for exc in exceptions:
        assert isinstance(exc, AppException)
        assert isinstance(exc, Exception)


@pytest.mark.unit
def test_exception_can_be_raised():
    """Test que las excepciones se pueden lanzar y capturar."""
    with pytest.raises(ValidationException) as exc_info:
        raise ValidationException("Test validation")
    
    assert exc_info.value.message == "Test validation"
    
    with pytest.raises(NotFoundException) as exc_info:
        raise NotFoundException("Item not found")
    
    assert exc_info.value.status_code == 404



