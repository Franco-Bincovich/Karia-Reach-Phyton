"""
Configuracion centralizada via Pydantic BaseSettings.

Todas las variables de entorno se leen desde aqui.
El resto del codigo importa `settings` — nunca usa os.environ directo.
"""

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Variables de entorno de la aplicacion."""

    # --- Servidor ---
    PORT: int = 3001
    NODE_ENV: str = "development"  # Legado del stack Node.js anterior, se mantiene por docker-compose
    BASE_URL: str = "http://localhost:3001"
    ALLOWED_ORIGINS: str = "http://localhost:3000"

    # --- Supabase ---
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_KEY: str = ""

    # --- Anthropic ---
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-sonnet-4-20250514"

    # --- Gmail OAuth ---
    GMAIL_CLIENT_ID: str = ""
    GMAIL_CLIENT_SECRET: str = ""
    GMAIL_REFRESH_TOKEN: str = ""
    GMAIL_FROM_EMAIL: str = ""

    # --- Auth ---
    KARIA_API_KEY: str = ""
    SECRET_KEY: str = ""

    # --- Cifrado de API keys de terceros en DB ---
    ENCRYPTION_KEY: str = ""

    # --- Rate Limiting (requests/minuto) ---
    RATE_LIMIT_GENERAL: str = "120/minute"
    RATE_LIMIT_COMPOSE: str = "10/minute"
    RATE_LIMIT_SEND: str = "5/minute"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @property
    def is_production(self) -> bool:
        """Devuelve True si estamos en produccion."""
        return self.NODE_ENV == "production"

    @property
    def origins_list(self) -> List[str]:
        """Parsea ALLOWED_ORIGINS (separados por coma) a lista."""
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",")]


@lru_cache
def get_settings() -> Settings:
    """Singleton cacheado de Settings."""
    return Settings()
