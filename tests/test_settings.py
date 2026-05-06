"""
Tests para configuración de settings.
"""

import pytest
import os
from unittest.mock import patch
from pydantic import ValidationError

from src.core.config.settings import Settings, get_settings


@pytest.mark.unit
def test_settings_default_values():
    """Test valores por defecto de settings."""
    with patch.dict(os.environ, {}, clear=True):
        settings = Settings()
        
        assert settings.environment == "development"
        assert settings.log_level == "INFO"
        assert settings.log_format == "json"
        assert settings.source_container_name == "entrada"
        assert settings.destination_container_name == "salida"
        assert settings.failed_container_name == "error"


@pytest.mark.unit
def test_settings_custom_environment():
    """Test configuración con valores personalizados."""
    with patch.dict(os.environ, {
        "ENVIRONMENT": "production",
        "LOG_LEVEL": "WARNING",
        "SOURCE_CONTAINER_NAME": "inbox",
    }):
        settings = Settings()
        
        assert settings.environment == "production"
        assert settings.log_level == "WARNING"
        assert settings.source_container_name == "inbox"



@pytest.mark.unit
def test_settings_storage_connection_string():
    """Test configuración de Storage."""
    conn_str = "DefaultEndpointsProtocol=https;AccountName=test;AccountKey=abc123"
    with patch.dict(os.environ, {
        "STORAGE_CONNECTION_STRING": conn_str,
    }):
        settings = Settings()
        
        assert settings.storage_connection_string == conn_str
@pytest.mark.unit
def test_get_settings_singleton():
    """Test que get_settings retorna la misma instancia."""
    settings1 = get_settings()
    settings2 = get_settings()
    
    assert settings1 is settings2


@pytest.mark.unit
def test_settings_case_insensitive():
    """Test que las variables de entorno son case insensitive."""
    with patch.dict(os.environ, {
        "environment": "testing",  # lowercase
        "LOG_LEVEL": "DEBUG",      # uppercase
    }):
        settings = Settings()
        
        assert settings.environment == "testing"
        assert settings.log_level == "DEBUG"


@pytest.mark.unit
def test_settings_optional_fields_none():
    """Test que campos opcionales pueden ser None."""
    with patch.dict(os.environ, {}, clear=True):
        settings = Settings()
        
        assert settings.storage_connection_string is None
        assert settings.source_container_name == "entrada"
        assert settings.destination_container_name == "salida"
        assert settings.failed_container_name == "error"


@pytest.mark.unit
def test_settings_log_format():
    """Test configuración de formato de log."""
    with patch.dict(os.environ, {
        "LOG_FORMAT": "json",
    }):
        settings = Settings()
        
        assert settings.log_format == "json"

@pytest.mark.unit
def test_settings_all_config_together():
    """Test configuración completa con todos los valores."""
    env_vars = {
        "ENVIRONMENT": "production",
        "LOG_LEVEL": "ERROR",
        "LOG_FORMAT": "json",
        "STORAGE_CONNECTION_STRING": "conn-str",
        "SOURCE_CONTAINER_NAME": "entrada",
        "DESTINATION_CONTAINER_NAME": "salida",
        "FAILED_CONTAINER_NAME": "error",
    }
    
    with patch.dict(os.environ, env_vars):
        settings = Settings()
        
        assert settings.environment == "production"
        assert settings.log_level == "ERROR"
        assert settings.source_container_name == "entrada"


@pytest.mark.unit
def test_settings_invalid_environment():
    """Test que rechaza environment inválido."""
    with patch.dict(os.environ, {"ENVIRONMENT": "invalid"}):
        with pytest.raises(ValidationError) as exc:
            Settings()
        
        assert "environment" in str(exc.value).lower()


@pytest.mark.unit
def test_settings_invalid_log_level():
    """Test que rechaza log_level inválido."""
    with patch.dict(os.environ, {"LOG_LEVEL": "INVALID"}):
        with pytest.raises(ValidationError) as exc:
            Settings()
        
        assert "log level" in str(exc.value).lower() or "log_level" in str(exc.value).lower()


@pytest.mark.unit
def test_settings_invalid_log_format():
    """Test que rechaza log_format inválido."""
    with patch.dict(os.environ, {"LOG_FORMAT": "xml"}):
        with pytest.raises(ValidationError) as exc:
            Settings()
        
        assert "log format" in str(exc.value).lower() or "log_format" in str(exc.value).lower()


@pytest.mark.unit
def test_settings_is_production():
    """Test property is_production."""
    with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
        settings = Settings()
        assert settings.is_production is True
    
    with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
        settings = Settings()
        assert settings.is_production is False


@pytest.mark.unit
def test_settings_is_development():
    """Test property is_development."""
    with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
        settings = Settings()
        assert settings.is_development is True
    
    with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
        settings = Settings()
        assert settings.is_development is False



