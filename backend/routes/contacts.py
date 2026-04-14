"""
Rutas de contactos — validacion con Pydantic, delegacion a controller.

Endpoints:
  GET    /api/contacts
  POST   /api/contacts/search-ai
  POST   /api/contacts/save-selection
  POST   /api/contacts/manual
  DELETE /api/contacts/{id}
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field, field_validator

from controllers import contacts_controller
from logger import get_logger
from middleware.auth import get_usuario_id_from_request
from middleware.rate_limiter import search_limit

log = get_logger(__name__)

router = APIRouter(prefix="/api/contacts", tags=["contacts"], redirect_slashes=False)


# --- Modelos de validacion ---

class SearchAIRequest(BaseModel):
    """Parametros para busqueda de contactos con IA."""
    rubro: str = Field("", description="Industria o sector")
    ubicacion: str = Field("", description="Zona geografica")
    cantidad: int = Field(10, ge=5, le=50, description="Cantidad de contactos")
    prompt_personalizado: Optional[str] = Field(None, description="Filtro adicional del usuario")


class ContactoBase(BaseModel):
    """Datos base de un contacto."""
    nombre: Optional[str] = None
    empresa: str = Field(..., min_length=1)
    cargo: Optional[str] = None
    email_empresarial: Optional[str] = None
    email_personal: Optional[str] = None
    telefono_empresa: Optional[str] = None
    telefono_personal: Optional[str] = None
    linkedin_url: Optional[str] = None
    rubro: Optional[str] = None
    confianza: Optional[float] = Field(None, ge=0.0, le=1.0)
    origen: str = "ai"

    model_config = {"extra": "ignore"}

    @field_validator("email_empresarial", "email_personal", mode="before")
    @classmethod
    def empty_str_to_none(cls, v: object) -> object:
        """Convierte strings vacias a None para evitar 422 en EmailStr."""
        if isinstance(v, str) and v.strip() == "":
            return None
        return v


class SaveSelectionRequest(BaseModel):
    """Lista de contactos a guardar (max 50)."""
    contactos: List[ContactoBase] = Field(..., max_length=50)


class ManualContactRequest(ContactoBase):
    """Contacto agregado manualmente (hereda de ContactoBase)."""
    pass


class EnrichRequest(BaseModel):
    """Parametros de enriquecimiento de un contacto existente."""
    metodo: str = Field("claude", description="Metodo: claude | perplexity | apollo")


# --- Endpoints ---

@router.get("")
async def listar(request: Request) -> dict:
    """Lista todos los contactos."""
    uid = get_usuario_id_from_request(request)
    return await contacts_controller.listar(uid)


@router.post("/search-ai")
@search_limit
async def buscar_con_ia(request: Request, body: SearchAIRequest) -> dict:
    """Busca contactos usando IA con web search."""
    uid = get_usuario_id_from_request(request)
    return await contacts_controller.buscar_con_ia(body.rubro, body.ubicacion, body.cantidad, body.prompt_personalizado, uid)


@router.post("/save-selection")
async def guardar_seleccion(request: Request) -> dict:
    """Guarda una seleccion de contactos en la base de datos."""
    uid = get_usuario_id_from_request(request)
    raw = await request.json()
    log.info("Body recibido en save-selection: %s", raw)
    body = SaveSelectionRequest(**raw)
    contactos = [c.model_dump() for c in body.contactos]
    log.info("Primer contacto post-Pydantic: %s", contactos[0] if contactos else "vacío")
    return await contacts_controller.guardar_seleccion(contactos, uid)


@router.post("/manual")
async def agregar_manual(request: Request, body: ManualContactRequest) -> dict:
    """Agrega un contacto manualmente."""
    uid = get_usuario_id_from_request(request)
    return await contacts_controller.agregar_manual(body.model_dump(), uid)


@router.post("/{contact_id}/enrich")
async def enriquecer(request: Request, contact_id: UUID, body: EnrichRequest) -> dict:
    """Enriquece un contacto existente via IA u otras fuentes."""
    uid = get_usuario_id_from_request(request)
    return await contacts_controller.enriquecer_contacto(str(contact_id), body.metodo, uid)


@router.delete("/{contact_id}")
async def eliminar(contact_id: UUID) -> dict:
    """Elimina un contacto por UUID."""
    return await contacts_controller.eliminar(str(contact_id))
