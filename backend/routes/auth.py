"""
Rutas de autenticacion — login publico.

Endpoints:
  POST /api/auth/login
"""

from fastapi import APIRouter, Request
from pydantic import BaseModel, EmailStr, Field

from controllers import auth_controller
from middleware.rate_limiter import limiter

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    """Credenciales de login."""
    email: EmailStr
    password: str = Field(..., min_length=1)


@router.post("/login")
@limiter.limit("5/15minutes")
async def login(request: Request, body: LoginRequest) -> dict:
    """Autentica usuario y devuelve JWT."""
    return await auth_controller.login(body.email, body.password)
