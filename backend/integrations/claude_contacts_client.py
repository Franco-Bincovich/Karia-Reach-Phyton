"""
Cliente Claude para búsqueda de contactos via web search OSINT.
"""
from __future__ import annotations

import httpx

from config.settings import get_settings
from logger import get_logger
from ._claude_base import _llamar_claude, _parsear_json, _SAFE, _JSON_ONLY, _API_URL, _HEADERS

log = get_logger(__name__)
settings = get_settings()


async def _inferir_rubro(prompt_personalizado: str) -> str:
    """Infiere el rubro/industria de un prompt de busqueda en 2-4 palabras via httpx."""
    payload = {
        "model": settings.ANTHROPIC_MODEL,
        "max_tokens": 30,
        "system": "Extraé el rubro o industria en 2-4 palabras. Solo el rubro, nada más.",
        "messages": [{"role": "user", "content": f"¿Cuál es el rubro de esta búsqueda? {prompt_personalizado}"}],
    }
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(_API_URL, headers=_HEADERS, json=payload)
        if response.status_code == 200:
            data = response.json()
            textos = [b["text"] for b in data.get("content", []) if b.get("type") == "text"]
            return textos[0].strip() if textos else prompt_personalizado[:30]
    except Exception:
        pass
    return prompt_personalizado[:30]


async def buscar_contactos(
    rubro: str, ubicacion: str, cantidad: int = 10,
    prompt_personalizado: str | None = None,
) -> list[dict]:
    """Busca contactos via web search OSINT con estrategia de 6 pasos.

    Args:
        rubro: industria o sector a buscar.
        ubicacion: zona geográfica.
        cantidad: cantidad de contactos a buscar (default 10).
        prompt_personalizado: instrucción adicional del usuario (opcional).

    Returns:
        Lista de dicts con datos de contacto (nombre, empresa, cargo, emails,
        teléfonos, redes sociales, website, dirección y confianza).

    Raises:
        AppError: CLAUDE_API_ERROR (502) si la llamada a la API de Claude falla.
    """
    system = (
        "Sos un investigador OSINT comercial de élite. Tenés acceso a web_search — usalo extensivamente.\n\n"
        "ESTRATEGIA OBLIGATORIA (6 pasos por cada contacto):\n"
        "PASO 1 — Identificar empresa y responsable:\n"
        "  → Buscar '{rubro} {ubicacion} dueño propietario gerente director contacto'\n"
        "  → LinkedIn empresa, Google Maps, sitio web oficial\n\n"
        "PASO 2 — Email corporativo:\n"
        "  → Buscar en sitio web oficial, Google Maps, Facebook página, LinkedIn empresa\n"
        "  → '{nombre} {empresa} email contacto'\n"
        "  → Mínimo 5 búsquedas antes de poner null\n\n"
        "PASO 3 — Email personal:\n"
        "  → '{nombre completo} gmail hotmail outlook'\n"
        "  → LinkedIn perfil personal, Instagram bio, Facebook personal\n\n"
        "PASO 4 — Teléfono y WhatsApp:\n"
        "  → Sitio web oficial, Google Maps, Facebook página de empresa\n"
        "  → '{nombre completo} whatsapp celular {ubicacion}'\n"
        "  → LinkedIn, Instagram bio\n\n"
        "PASO 5 — Redes sociales:\n"
        "  → LinkedIn URL del perfil personal\n"
        "  → Instagram: buscar '@{nombre}' o '{nombre} {empresa} instagram'\n"
        "  → Facebook: página personal o de empresa\n\n"
        "PASO 6 — Datos de empresa/ubicación:\n"
        "  → Website oficial (URL completa)\n"
        "  → Dirección física, ciudad, país (Google Maps, Facebook, sitio web)\n\n"
        "REGLAS ESTRICTAS:\n"
        "— nombre y empresa NUNCA null — buscá hasta encontrar el responsable real\n"
        "— NUNCA inventar datos — null si no encontrás después de buscar\n"
        "— Excluir contactos sin al menos 1 email O 1 teléfono\n"
        "— Si hay prompt_personalizado, ES LA INSTRUCCIÓN MÁS IMPORTANTE\n"
        "— Confianza por campos de contacto encontrados: 1.0=4+ | 0.75=3 | 0.5=2 | 0.25=1\n"
        f"{_SAFE} {_JSON_ONLY}"
    )
    _json_template = (
        '[{"nombre":"...","empresa":"...","cargo":"...",'
        '"email_empresarial":"...","email_personal":"...",'
        '"telefono_empresa":"...","telefono_personal":"...",'
        '"linkedin_url":"...","instagram_username":"...","facebook_url":"...",'
        '"whatsapp":"...","website":"...","direccion":"...","ciudad":"...","pais":"...",'
        '"confianza":0.75,"origen":"ai"}]'
    )
    if prompt_personalizado:
        user = (
            f"<user_input>\n"
            f"{'Rubro: ' + rubro if rubro else ''}\n"
            f"{'Ubicacion: ' + ubicacion if ubicacion else ''}\n"
            f"Cantidad: {cantidad}\n"
            f"Instrucción del usuario: {prompt_personalizado}\n"
            f"</user_input>\n\n"
            f"Interpretá la instrucción del usuario para entender qué contactos buscar. "
            f"Ejecutá los 6 pasos de la estrategia usando web_search.\n"
            f"Devolvé ÚNICAMENTE este JSON array:\n{_json_template}"
        )
    else:
        user = (
            f"<user_input>\nRubro: {rubro}\nUbicacion: {ubicacion}\nCantidad: {cantidad}\n"
            f"</user_input>\n"
            f"Ejecutá los 6 pasos de la estrategia usando web_search.\n"
            f"Devolvé JSON array:\n{_json_template}"
        )
    rubro_inferido = rubro
    if not rubro and prompt_personalizado:
        rubro_inferido = await _inferir_rubro(prompt_personalizado)
    tools = [{"type": "web_search_20250305", "name": "web_search"}]
    resultados = _parsear_json(await _llamar_claude(system, user, tools=tools))
    for contacto in resultados:
        contacto["rubro"] = rubro if rubro else rubro_inferido
    return resultados
