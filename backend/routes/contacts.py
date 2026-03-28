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

from fastapi import APIRouter
from pydantic import BaseModel, EmailStr, Field

from controllers import contacts_controller

router = APIRouter(prefix="/api/contacts", tags=["contacts"])


# --- Modelos de validacion ---

class SearchAIRequest(BaseModel):
    """Parametros para busqueda de contactos con IA."""
    rubro: str = Field(..., min_length=2, description="Industria o sector")
    ubicacion: str = Field(..., min_length=2, description="Zona geografica")
    cantidad: int = Field(10, ge=5, le=50, description="Cantidad de contactos")


class ContactoBase(BaseModel):
    """Datos base de un contacto."""
    nombre: str = Field(..., min_length=1)
    empresa: str = Field(..., min_length=1)
    cargo: str = ""
    email_empresarial: Optional[EmailStr] = None
    email_personal: Optional[EmailStr] = None
    telefono_empresa: Optional[str] = None
    telefono_personal: Optional[str] = None
    confianza: Optional[float] = Field(None, ge=0.0, le=1.0)
    origen: str = "ai"


class SaveSelectionRequest(BaseModel):
    """Lista de contactos a guardar (max 50)."""
    contactos: List[ContactoBase] = Field(..., max_length=50)


class ManualContactRequest(ContactoBase):
    """Contacto agregado manualmente (hereda de ContactoBase)."""
    pass


# --- Endpoints ---

@router.get("/")
async def listar() -> dict:
    """Lista todos los contactos."""
    return await contacts_controller.listar()


@router.post("/search-ai")
async def buscar_con_ia(body: SearchAIRequest) -> dict:
    """Busca contactos usando IA con web search."""
    return await contacts_controller.buscar_con_ia(body.rubro, body.ubicacion, body.cantidad)


@router.post("/save-selection")
async def guardar_seleccion(body: SaveSelectionRequest) -> dict:
    """Guarda una seleccion de contactos en la base de datos."""
    contactos = [c.model_dump() for c in body.contactos]
    return await contacts_controller.guardar_seleccion(contactos)


@router.post("/manual")
async def agregar_manual(body: ManualContactRequest) -> dict:
    """Agrega un contacto manualmente."""
    return await contacts_controller.agregar_manual(body.model_dump())


@router.delete("/{contact_id}")
async def eliminar(contact_id: UUID) -> dict:
    """Elimina un contacto por UUID."""
    return await contacts_controller.eliminar(str(contact_id))
