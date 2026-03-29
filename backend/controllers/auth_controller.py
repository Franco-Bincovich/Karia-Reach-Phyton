"""
Controller de autenticacion — adapta HTTP a services.
Sin logica de negocio, solo traduce request/response.
"""

from __future__ import annotations

from services import auth_service


async def login(email: str, password: str) -> dict:
    """Autentica usuario y devuelve JWT + datos."""
    resultado = await auth_service.login(email, password)
    return {"data": resultado}
