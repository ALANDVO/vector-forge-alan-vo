from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    APP_NAME: str = "vector-forge"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    HOST: str = "127.0.0.1"
    PORT: int = 8000

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/vector_forge.db"
    DATABASE_ECHO: bool = False

    # MCP
    MCP_TRANSPORT: str = "stdio"  # stdio, http
    MCP_HOST: str = "127.0.0.1"
    MCP_PORT: int = 8001

    # Authentication (Keycloak OIDC)
    OIDC_ISSUER_URL: str = ""
    OIDC_CLIENT_ID: str = "vector-forge"
    OIDC_CLIENT_SECRET: str = ""
    OIDC_REDIRECT_URI: str = "http://127.0.0.1:8000/auth/callback"
    OIDC_SCOPES: str = "openid profile email roles"
    OIDC_AUDIENCE: str = "vector-forge-api"

    # Demo mode (localhost only)
    DEMO_MODE: bool = False
    DEMO_USER_ID: str = "demo-user"
    DEMO_USER_ROLES: str = "viewer,operator"

    # LLM Providers
    LLM_PROVIDER: str = "openai-compatible"
    LLM_MODEL: str = ""
    LLM_BASE_URL: str = ""
    LLM_API_KEY: str = ""
    LLM_TIMEOUT: float = 30.0
    LLM_MAX_TOKENS: int = 4096

    # Analysis Limits
    MAX_ANALYSIS_TIME_SECONDS: int = 300
    MAX_MEMORY_MB: int = 1024
    MAX_OUTPUT_SIZE_MB: int = 50
    MAX_CONCURRENT_ANALYSES: int = 2

    # Ghidra
    GHIDRA_INSTALL_DIR: str = ""
    GHIDRA_JAVA_HOME: str = ""
    GHIDRA_MAX_HEAP_MB: int = 512
    GHIDRA_STARTUP_TIMEOUT_SECONDS: int = 330

    # Process Capture
    PROCESS_CAPTURE_TIMEOUT_SECONDS: int = 60
    PROCESS_CAPTURE_MAX_OUTPUT_MB: int = 10

    # Paths
    DATA_DIR: Path = Path("./data")
    SNAPSHOT_DIR: Path = Path("./data/snapshots")
    TEMP_DIR: Path = Path("./data/temp")

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def oidc_enabled(self) -> bool:
        return bool(self.OIDC_ISSUER_URL and self.OIDC_CLIENT_SECRET)

    @property
    def demo_mode_allowed(self) -> bool:
        return not self.is_production and self.DEMO_MODE

    def validate_demo_mode(self) -> None:
        if self.DEMO_MODE and self.is_production:
            raise RuntimeError("DEMO_MODE cannot be enabled in production")


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
    settings.SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    settings.TEMP_DIR.mkdir(parents=True, exist_ok=True)
    settings.validate_demo_mode()
    return settings