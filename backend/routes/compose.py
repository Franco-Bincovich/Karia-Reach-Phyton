"""
Rutas de composicion — validacion con Pydantic, delegacion a controller.

Endpoints:
  POST   /api/compose/generate
  POST   /api/compose/generate-from-contacts
  POST   /api/compose/format-manual
  GET    /api/compose/templates
  POST   /api/compose/templates
  DELETE /api/compose/templates/{id}
"""

from enum import Enum
from typing import List, Optional

from uuid import UUID

from fastapi import APIRouter, Request
from pydantic import BaseModel, EmailStr, Field

from controllers import compose_controller
from middleware.rate_limiter import compose_limit

router = APIRouter(prefix="/api/compose", tags=["compose"])


# --- Enums ---

class Tono(str, Enum):
    """Tonos disponibles para emails."""
    formal = "formal"
    amigable = "amigable"
    persuasivo = "persuasivo"
    directo = "directo"
    casual = "casual"


class Objetivo(str, Enum):
    """Objetivos del email."""
    agendar_reunion = "agendar_reunion"
    vender = "vender"
    informar = "informar"
    seguimiento = "seguimiento"
    presentacion = "presentacion"


# --- Modelos de validacion ---

class GenerateRequest(BaseModel):
    """Parametros para generacion de variantes."""
    descripcion: str = Field(..., min_length=10, description="Producto o servicio")
    tono: Tono
    objetivo: Objetivo
    variantes: int = Field(3, ge=1, le=5)
    instruccion_adicional: Optional[str] = Field(None, description="Instruccion libre opcional")


class ContactoInput(BaseModel):
    """Contacto minimo para composicion personalizada."""
    nombre: str
    empresa: str
    cargo: str = ""
    email: EmailStr


class GenerateFromContactsRequest(BaseModel):
    """Parametros para composicion desde contactos."""
    contactos: List[ContactoInput] = Field(..., min_length=1)
    producto: str = Field(..., min_length=5)
    modo: str = Field("formal", pattern="^(formal|casual|directo)$")


class FormatManualRequest(BaseModel):
    """Parametros para formateo manual de email."""
    asunto: str = Field(..., min_length=5, description="Asunto del email")
    cuerpo_natural: str = Field(..., min_length=10, description="Texto en lenguaje natural")
    nombre_campana: str = Field(..., min_length=2, description="Nombre de la campana")


class TemplateRequest(BaseModel):
    """Datos para crear un template."""
    nombre: str = Field(..., min_length=2)
    asunto: str = Field(..., min_length=5)
    cuerpo: str = Field(..., min_length=10)
    tono: str = ""
    objetivo: str = ""


# --- Endpoints ---

@router.post("/generate")
@compose_limit
async def generar_variantes(request: Request, body: GenerateRequest) -> dict:
    """Genera variantes de email con IA."""
    return await compose_controller.generar_variantes(
        body.descripcion, body.tono.value, body.objetivo.value,
        body.variantes, body.instruccion_adicional,
    )


@router.post("/generate-from-contacts")
@compose_limit
async def componer_desde_contactos(request: Request, body: GenerateFromContactsRequest) -> dict:
    """Compone emails personalizados para cada contacto."""
    contactos = [c.model_dump() for c in body.contactos]
    return await compose_controller.componer_desde_contactos(contactos, body.producto, body.modo)


@router.post("/format-manual")
@compose_limit
async def formatear_manual(request: Request, body: FormatManualRequest) -> dict:
    """Formatea texto natural a HTML de email profesional via IA."""
    return await compose_controller.formatear_manual(body.asunto, body.cuerpo_natural)


@router.get("/templates")
async def listar_templates() -> dict:
    """Lista todos los templates guardados."""
    return await compose_controller.listar_templates()


@router.post("/templates")
async def guardar_template(body: TemplateRequest) -> dict:
    """Guarda un template nuevo."""
    return await compose_controller.guardar_template(body.model_dump())


@router.delete("/templates/{template_id}")
async def eliminar_template(template_id: UUID) -> dict:
    """Elimina un template por UUID."""
    return await compose_controller.eliminar_template(str(template_id))
