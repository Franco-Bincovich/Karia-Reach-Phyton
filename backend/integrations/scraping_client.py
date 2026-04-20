"""
Cliente Playwright para web scraping.

Crawlea sitios web de forma headless, prioriza paginas de contacto
y extrae emails/telefonos/direcciones con regex.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse

from playwright.async_api import async_playwright

from integrations import claude_client
from logger import get_logger
from middleware.error_handler import AppError

log = get_logger(__name__)

_PRIORIDAD = {
    "contacto", "contact", "equipo", "team", "about", "nosotros",
    "autoridades", "directivos", "oficinas", "areas", "departamentos", "organigrama",
}
_IGNORAR = {"noticias", "news", "eventos", "events", "galeria", "gallery", "licitaciones", "blog"}

_RE_EMAIL = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
_RE_TEL = re.compile(
    r"(?:\+?54\s?)?(?:\(?\d{2,4}\)?[\s\-]?)?\d{4}[\s\-]?\d{4}(?:\s*(?:int\.?|interno)\s*\d+)?",
    re.IGNORECASE,
)
_RE_DIR = re.compile(
    r"(?:Av\.?|Calle|Ruta|Bv\.?)\s+[A-ZÁÉÍÓÚ][a-záéíóúñ\s]+\s+\d+",
    re.UNICODE,
)
_EXT_IGNORAR = (".png", ".jpg", ".jpeg", ".gif", ".svg", ".css", ".js", ".ico")


def _score_url(url: str) -> int:
    """Retorna 0=prioridad alta, 1=normal, 99=ignorar."""
    lower = url.lower()
    if any(k in lower for k in _IGNORAR):
        return 99
    return 0 if any(k in lower for k in _PRIORIDAD) else 1


async def crawl_sitio(url: str, max_paginas: int = 60, profundidad: int = 3) -> dict:
    """
    Crawlea un sitio con Playwright headless bloqueando imagenes, CSS y fuentes.

    Args:
        url: URL base del sitio a crawlear.
        max_paginas: limite de paginas a visitar.
        profundidad: profundidad maxima de crawl desde la URL base.

    Returns:
        Dict con url_base (str), paginas_visitadas (int), texto_completo (str).
    """
    visitados: set[str] = set()
    textos: list[str] = []
    cola: list[tuple[str, int]] = [(url, 0)]
    base_netloc = urlparse(url).netloc

    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            ctx = await browser.new_context()
            await ctx.route(
                "**/*.{png,jpg,jpeg,gif,svg,ico,css,woff,woff2,ttf,eot}",
                lambda r: r.abort(),
            )
            while cola and len(visitados) < max_paginas:
                cola.sort(key=lambda x: (_score_url(x[0]), x[1]))
                current_url, depth = cola.pop(0)
                if current_url in visitados or _score_url(current_url) == 99:
                    continue
                visitados.add(current_url)
                page = None
                try:
                    page = await ctx.new_page()
                    await page.goto(current_url, timeout=15000, wait_until="domcontentloaded")
                    textos.append(await page.inner_text("body"))
                    if depth < profundidad:
                        links = await page.eval_on_selector_all(
                            "a[href]", "els => els.map(e => e.href)"
                        )
                        for link in links:
                            if urlparse(link).netloc == base_netloc and link not in visitados:
                                cola.append((link, depth + 1))
                except Exception as exc:
                    log.warning("Error crawleando %s: %s", current_url, exc)
                finally:
                    if page:
                        try:
                            await page.close()
                        except Exception:
                            pass
            await browser.close()
    except AppError:
        raise
    except Exception as exc:
        raise AppError("Error al crawlear el sitio", "SCRAPING_ERROR", 502) from exc

    return {
        "url_base": url,
        "paginas_visitadas": len(visitados),
        "texto_completo": "\n\n".join(textos),
    }


def extraer_contactos(texto: str, preferencias: dict) -> dict:
    """
    Extrae datos de contacto del texto plano con regex.

    Args:
        texto: texto extraido del sitio.
        preferencias: flags extraer_emails, extraer_telefonos, extraer_direcciones.

    Returns:
        Dict con emails (list), telefonos (list), direcciones (list).
    """
    emails: list[str] = []
    telefonos: list[str] = []
    direcciones: list[str] = []

    if preferencias.get("extraer_emails", True):
        encontrados = _RE_EMAIL.findall(texto)
        emails = list({
            e.lower() for e in encontrados
            if "." in e.split("@")[-1] and not e.lower().endswith(_EXT_IGNORAR)
        })

    if preferencias.get("extraer_telefonos", True):
        encontrados = _RE_TEL.findall(texto)
        telefonos = list({
            t.strip() for t in encontrados
            if len(re.sub(r"\D", "", t)) >= 7
        })

    if preferencias.get("extraer_direcciones", False):
        direcciones = list(set(_RE_DIR.findall(texto)))

    return {"emails": emails, "telefonos": telefonos, "direcciones": direcciones}


async def resolver_url(nombre_o_url: str) -> str:
    """
    Resuelve la URL oficial de un sitio desde nombre o URL directa.

    Si el input empieza con 'http', lo devuelve tal cual.
    De lo contrario usa Claude con web_search para encontrar el sitio oficial.

    Args:
        nombre_o_url: URL directa o nombre de empresa/municipio/institucion.

    Returns:
        URL del sitio oficial.
    """
    if nombre_o_url.strip().startswith("http"):
        return nombre_o_url.strip()

    tools = [{"type": "web_search_20250305", "name": "web_search"}]
    try:
        resultado = await claude_client._llamar_claude(
            "Sos un buscador de URLs oficiales. Respondés SOLO con la URL, sin texto adicional.",
            f"Encontrá la URL oficial del sitio web de: {nombre_o_url}. "
            "Devolvé ÚNICAMENTE la URL, sin texto adicional.",
            tools=tools,
        )
        for parte in resultado.strip().split():
            if parte.startswith("http"):
                return parte
        raise AppError(
            f"No se encontró URL oficial para: {nombre_o_url}",
            "SCRAPING_URL_NOT_FOUND", 400,
        )
    except AppError:
        raise
    except Exception as exc:
        raise AppError(
            f"Error resolviendo URL para: {nombre_o_url}",
            "SCRAPING_URL_ERROR", 502,
        ) from exc
