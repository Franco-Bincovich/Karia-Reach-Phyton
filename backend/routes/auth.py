"""
Rutas de autenticacion — login publico.

Endpoints:
  POST /api/auth/login
"""

from fastapi import APIRouter
from pydantic import BaseModel, EmailStr, Field

from controllers import auth_controller

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    """Credenciales de login."""
    email: EmailStr
    password: str = Field(..., min_length=1)


@router.post("/login")
async def login(body: LoginRequest) -> dict:
    """Autentica usuario y devuelve JWT."""
    return await auth_controller.login(body.email, body.password)
