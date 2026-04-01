"""Orquestador del pipeline de enriquecimiento con 8 Actors de Apify."""
from __future__ import annotations

from integrations import apify_client
from logger import get_logger

log = get_logger(__name__)
_A = {"gmaps": "nwua9Gu5YrADL7ZDj", "web": "aYG0l9s7dbB7j3gbS",
      "fb": "4Hv5RhChiaDk6iwad", "ig": "shu8hvrXbJbY3Eb9W",
      "google": "nFJndFXA5zjCTuudP", "li": "dev_fusion/Linkedin-Profile-Scraper",
      "tw": "apidojo/tweet-scraper", "tt": "clockworks/tiktok-scraper"}


async def _fase(nombre: str, actor: str, inp: dict) -> list[dict]:
    """Ejecuta una fase. Retorna items o [] si falla."""
    try:
        run = await apify_client.run_actor(actor, inp)
        ds = run.get("defaultDatasetId")
        return await apify_client.get_dataset_items(ds) if ds else []
    except Exception as exc:
        log.warning("Fase %s falló: %s", nombre, exc)
        return []


async def enriquecer_contacto(contacto: dict) -> dict:
    """Pipeline de 8 fases para enriquecer un contacto."""
    r: dict = {}
    empresa = contacto.get("empresa", "")
    ciudad = contacto.get("ciudad", "")
    website = contacto.get("website")
    ig = contacto.get("instagram_username")
    fb = contacto.get("facebook_url")
    nombre = contacto.get("nombre")

    # F1 — Google Maps
    if empresa:
        items = await _fase("GMaps", _A["gmaps"], {
            "searchStringsArray": [f"{empresa} {ciudad}".strip()],
            "maxCrawledPlacesPerSearch": 1, "language": "es",
        })
        if items:
            p = items[0]
            r["telefono_empresa"] = p.get("phone")
            r["website"] = p.get("website")
            r["direccion"] = p.get("address")
            r["ciudad"] = p.get("city") or ciudad
            for link in p.get("socialMediaLinks", []):
                if "facebook.com" in link:
                    r["facebook_url"] = link
                elif "instagram.com" in link:
                    r["instagram_username"] = link.split("/")[-1].strip("/ ")
            website = r.get("website") or website
            fb = r.get("facebook_url") or fb
            ig = r.get("instagram_username") or ig

    # F2 — Website
    if website:
        items = await _fase("Web", _A["web"], {"startUrls": [{"url": website}]})
        if items:
            w = items[0]
            r["email_empresarial"] = (w.get("emails") or [None])[0]
            r["whatsapp"] = w.get("whatsapp") or (w.get("phones") or [None])[0]
            if not ig:
                ig = w.get("instagram")
                r["instagram_username"] = ig

    # F2b — Google Search redes sociales
    if empresa and not ig and not fb:
        items = await _fase("Google-social", _A["google"], {
            "queries": f"{empresa} instagram OR facebook",
            "maxPagesPerQuery": 1, "resultsPerPage": 5,
        })
        for item in (items[0].get("organicResults", items) if items else []):
            url = item.get("url") or item.get("link", "")
            _bad = ("/p/", "/reel/", "/stories/", "/explore/", "/locations/")
            if "instagram.com/" in url and not any(b in url for b in _bad):
                if not r.get("instagram_username"):
                    candidate = url.split("instagram.com/")[-1].strip("/ ").split("?")[0]
                    if "/" not in candidate and len(candidate) < 31:
                        ig = candidate
                        r["instagram_username"] = ig
            elif "facebook.com/" in url and "/posts/" not in url and "/videos/" not in url:
                if not r.get("facebook_url"):
                    fb = url
                    r["facebook_url"] = fb

    # F3 — Facebook
    if fb:
        items = await _fase("FB", _A["fb"], {"startUrls": [{"url": fb}]})
        if items:
            r.setdefault("email_empresarial", items[0].get("email"))
            r.setdefault("telefono_empresa", items[0].get("phone"))

    # F4 — Instagram
    if ig:
        items = await _fase("IG", _A["ig"], {
            "directUrls": [f"https://www.instagram.com/{ig}/"], "resultsType": "details", "resultsLimit": 1,
        })
        if items and not nombre:
            nombre = items[0].get("fullName")
            r["nombre_decisor"] = nombre

    # F5 — Google Search → LinkedIn
    li_url = contacto.get("linkedin_url")
    if nombre and empresa and not li_url:
        items = await _fase("Google", _A["google"], {
            "queries": f'"{nombre}" "{empresa}" site:linkedin.com/in',
            "maxPagesPerQuery": 1,
        })
        for item in (items[0].get("organicResults", items) if items else []):
            url = item.get("url") or item.get("link", "")
            if "linkedin.com/in" in url:
                li_url = url
                r["linkedin_url"] = li_url
                break

    # F6 — LinkedIn
    if li_url:
        items = await _fase("LI", _A["li"], {"profileUrls": [li_url]})
        if items:
            li = items[0]
            r["cargo"] = li.get("headline") or li.get("title")
            exp = li.get("experience") or []
            if exp:
                r["historial_laboral"] = "; ".join(
                    f"{e.get('title','')} @ {e.get('company','')}" for e in exp[:5])
            r["idiomas"] = ", ".join(li.get("languages") or [])

    # F7 — Twitter / F8 — TikTok
    handle = (nombre or "").replace(" ", "").lower()
    if handle:
        items = await _fase("TW", _A["tw"], {"handles": [handle]})
        if items:
            r["twitter_url"] = f"https://twitter.com/{handle}"
        items = await _fase("TT", _A["tt"], {
            "profiles": [{"url": f"https://tiktok.com/@{handle}"}], "resultsPerPage": 1,
        })
        if items and items[0].get("authorMeta", {}).get("name"):
            r["tiktok_username"] = items[0]["authorMeta"]["name"]

    # Confianza
    email = r.get("email_empresarial")
    if email and nombre and li_url:
        r["confianza"] = 1.0
    elif email and nombre:
        r["confianza"] = 0.75
    elif email:
        r["confianza"] = 0.5
    else:
        r["confianza"] = 0.25
    log.info("Enriquecimiento: %d campos, confianza=%.2f",
             len([v for v in r.values() if v]), r["confianza"])
    return r


async def buscar_por_maps(rubro: str, ubicacion: str, pais: str, cantidad: int) -> list[dict]:
    """Busca negocios en Google Maps via Apify (solo Fase 1)."""
    items = await _fase("GMaps-busq", _A["gmaps"], {
        "searchStringsArray": [f"{rubro} {ubicacion} {pais}"],
        "maxCrawledPlacesPerSearch": min(cantidad, 20), "maxImages": 0, "reviewsCount": 0, "language": "es",
    })
    return [
        {"empresa": p.get("title", ""), "telefono_empresa": p.get("phone"),
         "website": p.get("website"), "direccion": p.get("address"),
         "ciudad": p.get("city") or ubicacion, "confianza": 0.25, "origen": "apify"}
        for p in items
    ]
