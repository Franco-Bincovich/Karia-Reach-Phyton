"""
Cliente Claude para composición y generación de emails B2B.
"""
from __future__ import annotations

import json

from logger import get_logger
from middleware.error_handler import AppError
from ._claude_base import _llamar_claude, _parsear_json, _SAFE, _JSON_ONLY, _JSON_OBJ_ONLY

log = get_logger(__name__)


async def generar_emails(
    descripcion: str, tono: str, objetivo: str,
    variantes: int = 3, instruccion_adicional: str | None = None,
) -> list[dict]:
    """Genera variantes de cold email B2B con IA.

    Args:
        descripcion: producto o servicio a promocionar.
        tono: voz del email — 'formal', 'amigable', 'persuasivo', 'directo', 'casual'.
        objetivo: CTA objetivo — 'agendar_reunion', 'vender', 'informar', 'seguimiento', 'presentacion'.
        variantes: cantidad de variantes a generar (default 3).
        instruccion_adicional: instrucción libre del usuario; sobreescribe reglas generales (opcional).

    Returns:
        Lista de dicts con 'asunto' (str) y 'cuerpo' (HTML str).

    Raises:
        AppError: CLAUDE_API_ERROR (502) si la llamada a la API de Claude falla.
        AppError: CLAUDE_PARSE_ERROR (502) si la respuesta no es JSON válido.
    """
    system = (
        "Sos el mejor redactor de cold emails B2B del mercado argentino. "
        "Tu especialidad es escribir emails que generan respuestas reales — no emails corporativos ignorados.\n\n"
        "ANTES DE ESCRIBIR, analizá estos parámetros y adaptá el email en consecuencia:\n"
        "— tono: define la voz (formal=ejecutivo directo, amigable=cercano casual, persuasivo=urgencia suave, directo=sin rodeos)\n"
        "— objetivo: define el CTA (vender=proponer demo/compra, agendar_reunion=proponer agenda, informar=generar awareness sin CTA agresivo, seguimiento=recordatorio cálido, presentacion=introducción de empresa)\n"
        "— instruccion_adicional: SI viene este campo, ES LA INSTRUCCIÓN MÁS IMPORTANTE. Seguila al pie de la letra. Sobreescribe cualquier regla general si hay conflicto.\n\n"
        "REGLAS BASE (aplicar salvo que instruccion_adicional diga lo contrario):\n"
        "— Primera línea: engancha en menos de 8 palabras. NUNCA empieces con 'Espero que este email te encuentre bien' ni similares.\n"
        "— Mencioná el rubro/industria del destinatario con un insight real y específico.\n"
        "— Propuesta de valor en máximo 2 líneas: qué problema resuelve + resultado concreto.\n"
        "— Prueba social: resultado específico con número cuando sea posible.\n"
        "— UN solo CTA claro y de bajo compromiso.\n"
        "— Extensión default: 120-150 palabras. Ajustá si instruccion_adicional especifica otro largo.\n"
        "— NUNCA uses: 'solución innovadora', 'de vanguardia', 'líder del mercado', 'nos enorgullece'.\n"
        "— NUNCA inventes estadísticas. Usá 'nuestros clientes reportan' si no hay datos reales.\n"
        "— El campo 'cuerpo' DEBE ser HTML válido: <p>, <strong>, <em>, <br>, <ul>, <li>. NUNCA markdown.\n"
        f"{_SAFE} {_JSON_ONLY}"
    )
    user = (
        f"<user_input>\n"
        f"Producto/servicio: {descripcion}\n"
        f"Tono: {tono}\n"
        f"Objetivo: {objetivo}\n"
        f"{'Instrucción adicional: ' + instruccion_adicional if instruccion_adicional else ''}\n"
        f"</user_input>\n\n"
        f"Generá {variantes} variante(s) de cold email.\n"
        'Formato: [{"asunto": "...", "cuerpo": "..."}]'
    )
    return _parsear_json(await _llamar_claude(system, user))


async def componer_desde_contactos(
    contactos: list[dict], producto: str, modo: str = "formal"
) -> list[dict]:
    """Compone un email personalizado para cada contacto de la lista.

    Args:
        contactos: lista de dicts con nombre, empresa y cargo de cada destinatario.
        producto: producto o servicio a ofrecer.
        modo: estilo de escritura — 'formal', 'casual' o 'directo'.

    Returns:
        Lista de dicts con destinatario (email), asunto (str) y cuerpo (HTML str).

    Raises:
        AppError: CLAUDE_API_ERROR (502) si la llamada a la API de Claude falla.
        AppError: CLAUDE_PARSE_ERROR (502) si la respuesta no es JSON válido.
    """
    system = (
        "Sos un copywriter B2B experto en cold emails. "
        "Escribis en español rioplatense argentino. Personalizá cada email segun el contacto. "
        "El campo 'cuerpo' DEBE ser HTML valido para email (usa <p>, <strong>, <em>, <br>, <ul>, <li>). "
        f"NUNCA uses markdown (**, *, ##, etc). {_SAFE} {_JSON_ONLY}"
    )
    resumen = json.dumps(contactos, ensure_ascii=False, indent=2)
    user = (
        f"<user_input>\nProducto/servicio: {producto}\nModo: {modo}\n"
        f"Contactos:\n{resumen}\n</user_input>\n\n"
        'Formato: [{"destinatario": "email", "asunto": "...", "cuerpo": "..."}]'
    )
    return _parsear_json(await _llamar_claude(system, user))


async def formatear_manual(asunto: str, cuerpo_natural: str) -> dict:
    """Convierte texto natural a HTML de email profesional sin alterar el contenido.

    Args:
        asunto: asunto del email (se devuelve sin modificaciones).
        cuerpo_natural: cuerpo del email en texto libre del usuario.

    Returns:
        Dict con 'asunto' (str) y 'cuerpo_html' (HTML str con tags p/strong/em/br/ul/li).

    Raises:
        AppError: CLAUDE_API_ERROR (502) si la llamada a la API de Claude falla.
        AppError: CLAUDE_PARSE_ERROR (502) si la respuesta no es JSON válido.
    """
    system = (
        "Sos un formateador de emails profesionales. "
        "Recibis texto en lenguaje natural y lo convertis a HTML limpio de email. "
        "REGLAS: mantené el contenido EXACTO del usuario, no agregues ni quites información. "
        "Solo mejorá el formato: separar en párrafos, agregar énfasis donde corresponda. "
        "Usá UNICAMENTE tags HTML de email: <p>, <strong>, <em>, <br>, <ul>, <li>. "
        f"NUNCA uses markdown. {_SAFE} {_JSON_OBJ_ONLY}"
    )
    user = (
        f"<user_input>\n{cuerpo_natural}\n</user_input>\n\n"
        'Devolvé: {"cuerpo_html": "<p>...</p>"}'
    )
    texto = await _llamar_claude(system, user)
    try:
        inicio = texto.index("{")
        fin = texto.rindex("}") + 1
        parsed = json.loads(texto[inicio:fin])
    except (ValueError, json.JSONDecodeError) as exc:
        log.error("No se pudo parsear JSON de Claude. Texto recibido: %s", texto[:1000])
        raise AppError("Respuesta de Claude no es JSON valido", "CLAUDE_PARSE_ERROR", 502) from exc
    return {"asunto": asunto, "cuerpo_html": parsed.get("cuerpo_html", "")}
