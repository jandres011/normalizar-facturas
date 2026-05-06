"""
Tests para configuración de logging con structlog.
"""

import pytest
import logging
from unittest.mock import patch, MagicMock
from io import StringIO


@pytest.mark.unit
def test_setup_logging_development():
    """Test configuración de logging en desarrollo."""
    with patch('src.core.logging.get_settings') as mock_settings:
        settings = MagicMock()
        settings.environment = "development"
        settings.log_level = "DEBUG"
        settings.log_format = "console"
        mock_settings.return_value = settings
        
        from src.core.logging import setup_logging
        
        # No debe lanzar error
        setup_logging()


@pytest.mark.unit
def test_setup_logging_production():
    """Test configuración de logging en producción."""
    with patch('src.core.logging.get_settings') as mock_settings:
        settings = MagicMock()
        settings.environment = "production"
        settings.log_level = "INFO"
        settings.log_format = "json"
        mock_settings.return_value = settings
        
        from src.core.logging import setup_logging
        
        # No debe lanzar error
        setup_logging()


@pytest.mark.unit
def test_get_logger():
    """Test obtener logger."""
    from src.core.logging import get_logger
    
    logger = get_logger()
    
    assert logger is not None
    assert hasattr(logger, 'info')
    assert hasattr(logger, 'error')
    assert hasattr(logger, 'warning')


@pytest.mark.unit
def test_get_logger_with_name():
    """Test obtener logger con nombre."""
    from src.core.logging import get_logger
    
    logger = get_logger("test_module")
    
    assert logger is not None


@pytest.mark.unit
def test_log_levels():
    """Test diferentes niveles de log."""
    from src.core.logging import get_logger
    
    logger = get_logger()
    
    # No debe lanzar errores
    logger.debug("Debug message")
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")


@pytest.mark.unit
def test_security_logger_authentication_attempt():
    """Test log de intento de autenticación."""
    from src.core.logging import SecurityLogger
    
    logger = SecurityLogger()
    
    # No debe lanzar error
    logger.log_authentication_attempt(
        username="testuser",
        success=True,
        ip_address="192.168.1.1"
    )


@pytest.mark.unit
def test_security_logger_authentication_failure():
    """Test log de fallo de autenticación."""
    from src.core.logging import SecurityLogger
    
    logger = SecurityLogger()
    
    # No debe lanzar error
    logger.log_authentication_attempt(
        username="baduser",
        success=False,
        ip_address="10.0.0.1"
    )


@pytest.mark.unit
def test_security_logger_authorization_failure():
    """Test log de fallo de autorización."""
    from src.core.logging import SecurityLogger
    
    logger = SecurityLogger()
    
    # No debe lanzar error
    logger.log_authorization_failure(
        username="testuser",
        resource="/api/admin",
        action="DELETE"
    )


@pytest.mark.unit
def test_security_logger_suspicious_activity():
    """Test log de actividad sospechosa."""
    from src.core.logging import SecurityLogger
    
    logger = SecurityLogger()
    
    # No debe lanzar error
    logger.log_suspicious_activity(
        activity_type="multiple_failed_logins",
        details={"attempts": 5, "ip": "1.2.3.4"}
    )


@pytest.mark.unit
def test_logger_with_context():
    """Test logger con contexto adicional."""
    from src.core.logging import get_logger
    
    logger = get_logger("test_module")
    
    # Log con contexto estructurado
    logger.info("test_event", user_id=123, action="create")
    logger.warning("warning_event", code=404)
    logger.error("error_event", error_type="ValidationError")


@pytest.mark.unit
def test_logger_sensitive_data_in_logs():
    """Test que datos sensibles se loguean (filtrado interno)."""
    from src.core.logging import get_logger
    
    logger = get_logger()
    
    # El filtrado debe ocurrir internamente
    logger.info("user_login", password="secret123", username="test")
    logger.info("api_call", api_key="mykey456789", endpoint="/api/data")
    logger.info("config", token="bearer_token_xyz", database="mydb")


@pytest.mark.unit
def test_setup_logging_json_format():
    """Test configuración con formato JSON."""
    with patch('src.core.logging.get_settings') as mock_settings:
        settings = MagicMock()
        settings.environment = "production"
        settings.log_level = "WARNING"
        settings.log_format = "json"
        mock_settings.return_value = settings
        
        from src.core.logging import setup_logging
        
        setup_logging()


@pytest.mark.unit
def test_setup_logging_console_format():
    """Test configuración con formato consola."""
    with patch('src.core.logging.get_settings') as mock_settings:
        settings = MagicMock()
        settings.environment = "development"
        settings.log_level = "DEBUG"
        settings.log_format = "console"
        mock_settings.return_value = settings
        
        from src.core.logging import setup_logging
        
        setup_logging()


@pytest.mark.unit
def test_get_logger_different_names():
    """Test obtener loggers con diferentes nombres."""
    from src.core.logging import get_logger
    
    logger1 = get_logger("module1")
    logger2 = get_logger("module2")
    logger3 = get_logger()
    
    assert logger1 is not None
    assert logger2 is not None
    assert logger3 is not None


@pytest.mark.unit
def test_logger_with_non_string_sensitive_values():
    """Test logging con valores sensibles no-string."""
    from src.core.logging import get_logger
    
    logger = get_logger()
    
    # Log con valores sensibles de diferentes tipos (int, None, bool)
    logger.info("test_event", password=123, token=None, secret=True)
    logger.info("numeric_secret", api_key=9999, secret=42)


@pytest.mark.unit
def test_logger_with_lists_of_non_dict_sensitive_items():
    """Test logging con listas de items sensibles no-dict."""
    from src.core.logging import get_logger
    
    logger = get_logger()
    
    # Log con listas de valores sensibles simples (no diccionarios)
    logger.info("secrets_list", passwords=["pass1", "pass2", 123, None])
    logger.info("tokens_list", api_keys=["key1", "key2", "key3"])
    logger.info("mixed_list", secrets=["secret", 456, True, None])


@pytest.mark.unit
def test_logger_with_short_sensitive_non_string():
    """Test logging con valores sensibles cortos no-string."""
    from src.core.logging import get_logger
    
    logger = get_logger()
    
    # Valores sensibles cortos de diferentes tipos
    logger.info("short_values", password=12, token=None, secret=False)
    logger.info("empty_values", api_key="", secret="")


@pytest.mark.unit
def test_logger_invocation_id_context():
    """Test logger con contextvars para invocation_id."""
    from src.core.logging import get_logger
    import contextvars
    
    logger = get_logger()
    
    # Crear context var con invocation_id
    invocation_id_var = contextvars.ContextVar("invocation_id", default=None)
    invocation_id_var.set("test-invocation-123")
    
    # Log debería incluir el invocation_id automáticamente
    logger.info("test_with_invocation", action="test")


@pytest.mark.unit
def test_logger_invocation_id_error_handling():
    """Test manejo de errores al obtener invocation_id."""
    from src.core.logging import get_logger
    
    logger = get_logger()
    
    # Sin contexto configurado, no debería fallar
    logger.info("test_without_context", data="test")
    logger.warning("warning_test", code=123)


@pytest.mark.unit
def test_filter_sensitive_data_non_string_short_value():
    """Test filtrado de valores sensibles cortos no-string."""
    from src.core.logging import _filter_sensitive_data
    
    # Valores sensibles de tipo int, bool, None
    event_dict = {
        "password": 123,  # int
        "token": False,  # bool
        "secret": None,  # None
        "api_key": 0  # int 0
    }
    
    # Llamar directamente a la función interna
    filtered = _filter_sensitive_data(None, None, event_dict)
    
    # Todos deberían ser enmascarados como "***"
    assert filtered["password"] == "***"
    assert filtered["token"] == "***"
    assert filtered["secret"] == "***"
    assert filtered["api_key"] == "***"


@pytest.mark.unit
def test_filter_sensitive_data_list_with_primitives():
    """Test filtrado de listas con valores primitivos sensibles."""
    from src.core.logging import _filter_sensitive_data
    
    event_dict = {
        "passwords": ["longpass123", 456, None, True, "short"],
        "normal_list": ["val1", "val2", 123]
    }
    
    filtered = _filter_sensitive_data(None, None, event_dict)
    
    # Passwords deberían estar filtrados
    assert "***" in str(filtered["passwords"])
    # Lista normal no debería estar filtrada
    assert filtered["normal_list"] == ["val1", "val2", 123]


@pytest.mark.unit
def test_add_invocation_id_exception_handling():
    """Test _add_invocation_id cuando get() lanza excepción - cubre líneas 146-148."""
    from src.core.logging import _add_invocation_id
    
    # Mockear el módulo contextvars a nivel global
    import sys
    from unittest.mock import MagicMock
    
    # Guardar el módulo original
    original_contextvars = sys.modules.get('contextvars')
    
    # Crear mock de contextvars
    mock_contextvars = MagicMock()
    mock_context_var = MagicMock()
    mock_context_var.get.side_effect = RuntimeError("Simulated context error")
    mock_contextvars.ContextVar.return_value = mock_context_var
    
    # Reemplazar el módulo
    sys.modules['contextvars'] = mock_contextvars
    
    try:
        event_dict = {"test": "data", "user": "test@example.com"}
        
        # No debería lanzar excepción, debe manejarla silenciosamente
        result = _add_invocation_id(None, None, event_dict)
        
        # Debería retornar el dict original sin invocation_id
        assert result == event_dict
        assert "invocation_id" not in result
    finally:
        # Restaurar el módulo original
        if original_contextvars:
            sys.modules['contextvars'] = original_contextvars


@pytest.mark.unit
def test_add_invocation_id_success_branch():
    """Test _add_invocation_id cuando existe un invocation_id válido."""
    from src.core.logging import _add_invocation_id

    import sys
    from unittest.mock import MagicMock

    original_contextvars = sys.modules.get('contextvars')

    mock_contextvars = MagicMock()
    mock_context_var = MagicMock()
    mock_context_var.get.return_value = "inv-123"
    mock_contextvars.ContextVar.return_value = mock_context_var
    sys.modules['contextvars'] = mock_contextvars

    try:
        event_dict = {"event": "test"}
        result = _add_invocation_id(None, None, event_dict)

        assert result["invocation_id"] == "inv-123"
    finally:
        if original_contextvars:
            sys.modules['contextvars'] = original_contextvars



