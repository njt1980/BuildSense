"""Configuration settings module for BuildSense.

Defines the environment settings schema and variables using Pydantic Settings v2,
loading configurations directly from environment variables and local .env files.
"""

from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Settings schema containing all core credentials and bounds for BuildSense.

    Automatically parses and validates environment settings.
    """
    # Host and port configuration
    host: str = "0.0.0.0"
    port: int = 8001

    # API Keys & Integrations
    anthropic_api_key: Optional[str] = None

    # Database Configuration (Neon / Supabase PostgreSQL)
    database_url: str = "postgresql://postgres:password@localhost:5432/buildsense"

    # Cache Configuration (Upstash Redis)
    redis_url: str = "redis://localhost:6379/0"

    # Global Daily Cost Limit
    max_global_daily_spend: float = 10.00

    # Telemetry and local developer observability
    environment: str = "local"
    service_name: str = "buildsense-api"
    telemetry_enabled: bool = True
    telemetry_log_level: str = "INFO"
    telemetry_log_format: str = "json"
    local_telemetry_viewer_enabled: bool = True
    local_telemetry_max_events: int = 1000
    local_telemetry_max_runs: int = 100

    # LangSmith Observability Integration
    langchain_tracing_v2: str = "false"
    langchain_endpoint: Optional[str] = None
    langchain_api_key: Optional[str] = None
    langchain_project: Optional[str] = None

    # Pydantic settings configuration to load .env files
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


# Instantiate a global settings object
settings = Settings()

# Set LangSmith environment variables if configured
import os
if settings.langchain_tracing_v2:
    os.environ["LANGCHAIN_TRACING_V2"] = settings.langchain_tracing_v2
if settings.langchain_endpoint:
    os.environ["LANGCHAIN_ENDPOINT"] = settings.langchain_endpoint
if settings.langchain_api_key:
    os.environ["LANGCHAIN_API_KEY"] = settings.langchain_api_key
if settings.langchain_project:
    os.environ["LANGCHAIN_PROJECT"] = settings.langchain_project
