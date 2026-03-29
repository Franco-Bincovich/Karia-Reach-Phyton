"""
Rate limiting con slowapi.

Define 3 limiters preconfigurados:
- general: 120 req/min (default para todas las rutas).
- compose: 10 req/min (generacion de contenido).
- send: 5 req/min (envio de emails).
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

from config.settings import get_settings

settings = get_settings()

# Limiter principal — se registra como middleware en main.py
limiter = Limiter(key_func=get_remote_address, default_limits=[settings.RATE_LIMIT_GENERAL])

# Decoradores reutilizables para rutas especificas
compose_limit = limiter.limit(settings.RATE_LIMIT_COMPOSE)
send_limit = limiter.limit(settings.RATE_LIMIT_SEND)
apollo_limit = limiter.limit("20/minute")
search_limit = limiter.limit("5/minute")  # Busqueda IA: costosa (Claude + web_search)
