"""Búsqueda de contactos de Instagram desde perfiles de competencia."""
from __future__ import annotations

from integrations import apify_client
from logger import get_logger

log = get_logger(__name__)

_ACTOR_FOLLOWERS = "fgQu4AjetQSr58qdJ"   # Instagram Followers - No Cookies Required
_ACTOR_LIKERS    = "reGe1ST3OBgYZSsZJ"   # Instagram Hashtag Scraper (posts + likers)
_ACTOR_PROFILES  = "JNb6iSRuMKLF3OA3v"   # Instagram Profile Scraper


async def _run(actor: str, inp: dict) -> list[dict]:
    """Ejecuta un actor Apify y devuelve sus items. Retorna [] si falla."""
    try:
        run = await apify_client.run_actor(actor, inp)
        ds = run.get("defaultDatasetId")
        return await apify_client.get_dataset_items(ds) if ds else []
    except Exception as exc:
        log.warning("Actor %s falló: %s", actor, exc)
        return []


async def buscar_instagram(handles: list[str], max_por_perfil: int) -> dict:
    """
    Pipeline de 3 fases por handle:
      1. Seguidores via _ACTOR_FOLLOWERS
      2. Likers de posts recientes via _ACTOR_LIKERS
      3. Enriquecimiento de perfiles via _ACTOR_PROFILES (lotes de 50)

    Args:
        handles: Usernames sin @ (máx 8, validado en la ruta).
        max_por_perfil: Límite de contactos únicos por handle.

    Returns:
        dict con 'data' (list[dict]) y 'total' (int).
    """
    todos: list[dict] = []
    limite = max(1, max_por_perfil // 2)

    for handle in handles:
        vistos: set[str] = set()
        candidatos: list[dict] = []

        # Fase 1 — seguidores
        followers = await _run(_ACTOR_FOLLOWERS, {
            "username": handle,
            "maxItems": limite,
        })
        candidatos.extend(followers)

        # Fase 2 — likers de posts recientes
        posts = await _run(_ACTOR_LIKERS, {
            "directUrls": [f"https://www.instagram.com/{handle}/"],
            "resultsType": "posts",
            "resultsLimit": 5,
        })
        for post in posts:
            candidatos.extend(post.get("likedBy") or post.get("latestComments") or [])

        # Deduplicar por username
        usernames: list[str] = []
        for c in candidatos:
            uname = (c.get("username") or c.get("ownerUsername") or c.get("userName") or "").strip()
            if uname and uname not in vistos:
                vistos.add(uname)
                usernames.append(uname)
            if len(usernames) >= max_por_perfil:
                break

        if not usernames:
            log.info("Handle @%s: sin candidatos", handle)
            continue

        # Fase 3 — enriquecer perfiles (lotes de 50)
        for i in range(0, len(usernames), 50):
            perfiles = await _run(_ACTOR_PROFILES, {"usernames": usernames[i:i + 50]})
            for p in perfiles:
                contacto = _mapear(p)
                if contacto:
                    todos.append(contacto)

        log.info("Handle @%s: %d contactos procesados", handle, len(todos))

    return {"data": todos, "total": len(todos)}


def _mapear(perfil: dict) -> dict | None:
    """Mapea un perfil de Instagram al formato estándar de contacto."""
    username = (perfil.get("username") or "").strip()
    if not username:
        return None
    nombre = perfil.get("fullName") or perfil.get("name") or username
    bio = perfil.get("biography") or ""
    email = _extraer_email(bio)
    return {
        "nombre": nombre,
        "instagram_username": username,
        "email_empresarial": email,
        "website": perfil.get("externalUrl"),
        "confianza": 0.7 if email else 0.4,
        "origen": "instagram",
    }


def _extraer_email(texto: str) -> str | None:
    """Extrae el primer email de un texto (ej: bio de Instagram)."""
    for token in texto.split():
        token = token.strip(".,;:()")
        if "@" in token and "." in token.split("@")[-1] and len(token) < 100:
            return token
    return None
