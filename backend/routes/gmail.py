"""
Rutas de Gmail OAuth por usuario.

Endpoints:
  GET  /api/gmail/status           — estado de la integracion del usuario autenticado
  GET  /api/gmail/oauth/authorize  — genera URL de autorizacion de Google
  GET  /api/gmail/oauth/callback   — callback OAuth (PUBLICO — Google redirige aqui)
  POST /api/gmail/disconnect       — desconecta la integracion Gmail del usuario
"""

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from controllers import gmail_controller
from middleware.auth import get_rol_from_request, get_usuario_id_from_request

router = APIRouter(prefix="/api/gmail", tags=["gmail"])


@router.get("/status")
async def estado(request: Request) -> dict:
    """Retorna si el usuario tiene Gmail conectado y el email asociado."""
    uid = get_usuario_id_from_request(request)
    return await gmail_controller.estado(uid)


@router.get("/oauth/authorize")
async def autorizar(request: Request) -> dict:
    """Genera y retorna la URL de autorización de Google OAuth."""
    uid = get_usuario_id_from_request(request)
    return await gmail_controller.autorizar(uid)


@router.get("/oauth/callback")
async def callback(request: Request, code: str = None, state: str = None, error: str = None) -> RedirectResponse:
    """Callback de Google OAuth — público. Procesa code y redirige al frontend."""
    return await gmail_controller.callback(code=code, state=state, error=error)


@router.post("/disconnect")
async def desconectar(request: Request) -> dict:
    """Desconecta la integración Gmail del usuario autenticado."""
    uid = get_usuario_id_from_request(request)
    return await gmail_controller.desconectar(uid)
