"""
Servicio de scraping — orquesta crawl, extraccion y formateo de contactos.

Gestiona las preferencias del usuario y convierte emails encontrados
en contactos con formato estandar.
"""

from __future__ import annotations

import ipaddress
import json
import socket
import unicodedata
from urllib.parse import urlparse

from integrations import scraping_client
from logger import get_logger
from middleware.error_handler import AppError
from repositories import integrations_repository
from services.contacts_service import anotar_existencia

log = get_logger(__name__)

_SERVICIO = "scraping_preferencias"
_DOMINIOS_BLOQUEADOS = {
    "facebook.com", "instagram.com", "twitter.com", "x.com",
    "tiktok.com", "linkedin.com", "youtube.com", "wikipedia.org",
}
_KW_ALTA = frozenset({"hacienda","rentas","secretaria","mesadeentrada","cobranzas","tesoreria","contaduria","administracion","finanzas","tributaria","recaudacion","licitaciones","compras","proveedores"})

_PREFS_DEFAULT: dict = {
    "extraer_emails": True,
    "extraer_telefonos": True,
    "extraer_autoridades": True,
    "extraer_direcciones": False,
    "max_paginas": 60,
    "profundidad": 3,
    "guardar_directo": False,
}


async def obtener_preferencias(usuario_id: str) -> dict:
    """
    Devuelve preferencias de scraping del usuario.

    Returns defaults si el usuario no tiene preferencias guardadas.
    """
    raw = await integrations_repository.obtener_api_key(_SERVICIO, usuario_id)
    if raw:
        try:
            return {**_PREFS_DEFAULT, **json.loads(raw)}
        except (json.JSONDecodeError, TypeError):
            pass
    return dict(_PREFS_DEFAULT)


async def guardar_preferencias(usuario_id: str, preferencias: dict) -> None:
    """
    Persiste preferencias de scraping del usuario.

    Almacena el JSON en la tabla integraciones con servicio='scraping_preferencias'.
    """
    merged = {**_PREFS_DEFAULT, **preferencias}
    await integrations_repository.guardar_api_key(_SERVICIO, json.dumps(merged), usuario_id)


def _es_ip_privada(ip_str: str) -> bool:
    """True si la IP cae en un rango privado, reservado o de loopback."""
    try:
        addr = ipaddress.ip_address(ip_str)
        return addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved or addr.is_unspecified
    except ValueError:
        return True


def _calcular_confianza(email: str) -> float:
    """0.9 si el local-part contiene palabra clave institucional; 0.5 si no."""
    local = "".join(c for c in unicodedata.normalize("NFD", email.split("@")[0].lower()) if unicodedata.category(c) != "Mn")
    return 0.9 if any(kw in local for kw in _KW_ALTA) else 0.5


def _es_url_valida(url: str) -> bool:
    """Valida URL: no es red social y no apunta a una IP privada o reservada."""
    try:
        parsed = urlparse(url)
        netloc = parsed.netloc.lower().removeprefix("www.")
        hostname = parsed.hostname
        if not hostname:
            return False
        if any(bloq in netloc for bloq in _DOMINIOS_BLOQUEADOS):
            return False
        ip = socket.gethostbyname(hostname)
        return not _es_ip_privada(ip)
    except Exception:
        return False


async def buscar_por_scraping(
    entradas: list[str],
    usuario_id: str,
    preferencias: dict,
) -> list[dict]:
    """
    Crawlea cada sitio y extrae contactos con formato estandar.

    Para cada entrada: resuelve URL, valida dominio, crawlea el sitio,
    extrae datos de contacto y los convierte al formato interno.

    Args:
        entradas: lista de URLs o nombres de sitios/instituciones.
        usuario_id: ID del usuario que realiza la busqueda.
        preferencias: configuracion de extraccion del usuario.

    Returns:
        Lista de contactos en formato estandar con flag ya_existe.
    """
    if not entradas:
        raise AppError("Se requiere al menos una entrada", "SCRAPING_EMPTY", 400)
    if len(entradas) > 20:
        raise AppError("Maximo 20 sitios por busqueda", "SCRAPING_LIMIT", 400)

    prefs = {**_PREFS_DEFAULT, **preferencias}
    max_pags = max(1, min(100, int(prefs.get("max_paginas", 60))))
    profundidad = max(1, min(5, int(prefs.get("profundidad", 3))))
    contactos: list[dict] = []

    for entrada in entradas:
        entrada = entrada.strip()
        if not entrada:
            continue
        try:
            url = await scraping_client.resolver_url(entrada)
            if not _es_url_valida(url):
                log.warning("URL bloqueada (red social/personal): %s", url)
                continue
            resultado = await scraping_client.crawl_sitio(
                url, max_paginas=max_pags, profundidad=profundidad,
            )
            extraidos = scraping_client.extraer_contactos(resultado["texto_completo"], prefs)
            dominio = urlparse(url).netloc.removeprefix("www.")
            tel_principal = extraidos["telefonos"][0] if extraidos["telefonos"] else None
            for email in extraidos["emails"]:
                contactos.append({
                    "nombre": None,
                    "empresa": dominio,
                    "email_empresarial": email,
                    "telefono_empresa": tel_principal,
                    "origen": "scraping",
                    "confianza": _calcular_confianza(email),
                })
            log.info(
                "Scraping %s: %d emails, %d tel, %d pags",
                url, len(extraidos["emails"]), len(extraidos["telefonos"]),
                resultado["paginas_visitadas"],
            )
        except AppError as exc:
            log.warning("Error scraping '%s': %s", entrada, exc.message)
            continue

    return await anotar_existencia(contactos, usuario_id)
