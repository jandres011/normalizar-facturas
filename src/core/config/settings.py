"""
Configuración de la aplicación usando Pydantic Settings.

Este módulo maneja todas las variables de entorno y configuraciones
de la aplicación de manera tipada y validada, adaptado para Azure Functions.
"""

from functools import lru_cache
from typing import Optional

from pydantic import Field, validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Configuración de la aplicación.

    Todas las configuraciones se cargan desde variables de entorno
    con validación automática de tipos.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Configuración del entorno
    environment: str = Field(
        default="development", description="Entorno de ejecución"
    )

    """# Configuración de Azure Key Vault
    azure_key_vault_url: Optional[str] = Field(
        default=None, description="URL del Azure Key Vault"
    )
    azure_tenant_id: Optional[str] = Field(
        default=None, description="Tenant ID de Azure"
    )
    azure_client_id: Optional[str] = Field(
        default=None, description="Client ID de Azure"
    )
    azure_client_secret: Optional[str] = Field(
        default=None, description="Client Secret de Azure"
    ) """
    # Configuración de Azure Storage
    storage_connection_string: Optional[str] = Field(
        default=None, description="Connection string de Azure Storage para blobs"
    )
    source_container_name: str = Field(
        default="entrada",
        description="Nombre del contenedor origen para blobs entrantes",
    )
    destination_container_name: str = Field(
        default="salida",
        description="Nombre del contenedor destino para blobs normalizados",
    )
    failed_container_name: str = Field(
        default="error",
        description="Nombre del contenedor para blobs con error",
    )

    # Configuración de logging
    log_level: str = Field(default="INFO", description="Nivel de logging")
    log_format: str = Field(default="json", description="Formato de logging")

    @validator("environment")
    def validate_environment(cls, v: str) -> str:
        """Valida que el entorno sea válido."""
        allowed = ["development", "testing", "production"]
        if v not in allowed:
            raise ValueError(f"Environment debe ser uno de: {allowed}")
        return v

    @validator("log_level")
    def validate_log_level(cls, v: str) -> str:
        """Valida que el nivel de log sea válido."""
        allowed = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in allowed:
            raise ValueError(f"Log level debe ser uno de: {allowed}")
        return v.upper()

    @validator("log_format")
    def validate_log_format(cls, v: str) -> str:
        """Valida que el formato de log sea válido."""
        allowed = ["json", "text"]
        if v not in allowed:
            raise ValueError(f"Log format debe ser uno de: {allowed}")
        return v

    @property
    def is_production(self) -> bool:
        """
        Verifica si el entorno es producción.

        Returns:
            bool: True si es producción
        """
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        """
        Verifica si el entorno es desarrollo.

        Returns:
            bool: True si es desarrollo
        """
        return self.environment == "development"


@lru_cache()
def get_settings() -> Settings:
    """
    Obtiene la configuración de la aplicación (singleton).

    Returns:
        Settings: Configuración de la aplicación
    """
    return Settings()
