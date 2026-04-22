"""
Servicio de autenticacion — login con email/password y generacion de JWT.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta

import bcrypt
import jwt

from config.settings import get_settings
from logger import get_logger
from middleware.error_handler import AppError
from repositories import auth_repository

log = get_logger(__name__)
settings = get_settings()


async def login(email: str, password: str) -> dict:
    """
    Autentica un usuario por email/password y genera JWT.

    Flujo: busca usuario en DB → verifica password con bcrypt →
    genera JWT con payload {usuario_id, email, nombre, rol}.

    Args:
        email: email del usuario.
        password: password en texto plano.

    Returns:
        Dict con 'token' (JWT string) y 'usuario' (nombre, email, rol).

    Raises:
        AppError 401 si credenciales invalidas.
    """
    usuario = await auth_repository.buscar_usuario_por_email(email)
    if not usuario:
        raise AppError("Credenciales invalidas", "AUTH_INVALID", 401)

    # bcrypt.checkpw espera bytes
    password_valido = bcrypt.checkpw(
        password.encode("utf-8"),
        usuario["password_hash"].encode("utf-8"),
    )
    if not password_valido:
        raise AppError("Credenciales invalidas", "AUTH_INVALID", 401)

    # Generar JWT con audience/issuer para evitar token confusion entre sistemas
    payload = {
        "usuario_id": usuario["id"],
        "email": usuario["email"],
        "nombre": usuario.get("nombre", ""),
        "rol": usuario.get("rol", "user"),
        "aud": "karia-reach",
        "iss": "karia-reach-backend",
        "exp": datetime.now(timezone.utc) + timedelta(hours=settings.JWT_EXPIRATION_HOURS),
    }
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")

    log.info("Login exitoso: %s", email)
    return {
        "token": token,
        "usuario": {
            "nombre": usuario.get("nombre", ""),
            "email": usuario["email"],
            "rol": usuario.get("rol", "user"),
            "metodos_habilitados": usuario.get("metodos_habilitados", []),
        },
    }
