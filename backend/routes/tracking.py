"""
Ruta de tracking — pixel de apertura de emails.

Endpoint publico (sin auth) que valida un token HMAC, registra la
apertura via repository y devuelve un GIF transparente 1x1px.
El pixel se devuelve SIEMPRE (incluso si el token falla) para no
revelar al cliente si la validacion fallo o no.
"""

from __future__ import annotations

import base64
import hmac
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Query, Request
from fastapi.responses import Response

from logger import get_logger
from middleware.rate_limiter import tracking_limit
from repositories import tracking_repository
from utils.security import generar_token_tracking

log = get_logger(__name__)

router = APIRouter(prefix="/track", tags=["tracking"])

# GIF transparente 1x1px (47 bytes)
_PIXEL_GIF = base64.b64decode(
    "R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"
)


@router.get("/open/{campaign_id}/{contact_id}")
@tracking_limit
async def registrar_apertura(
    request: Request,
    campaign_id: UUID,
    contact_id: UUID,
    token: Optional[str] = Query(None),
) -> Response:
    """
    Registra apertura de email si el token HMAC es valido.

    El pixel GIF se devuelve siempre para no revelar si el token
    fallo — solo se registra la apertura si es legitima.
    """
    cid, ctid = str(campaign_id), str(contact_id)
    token_esperado = generar_token_tracking(cid, ctid)
    if token and hmac.compare_digest(token, token_esperado):
        await tracking_repository.registrar_apertura(cid, ctid)
    else:
        log.warning("Token invalido en tracking: campaign=%s contact=%s", cid, ctid)

    return Response(
        content=_PIXEL_GIF,
        media_type="image/gif",
        headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"},
    )
