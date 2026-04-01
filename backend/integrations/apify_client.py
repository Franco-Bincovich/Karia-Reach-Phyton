"""
Cliente async para la API de Apify.

Ejecuta Actors, espera resultados y descarga datasets.
"""

from __future__ import annotations

import asyncio

import httpx

from config.settings import get_settings
from logger import get_logger
from middleware.error_handler import AppError

log = get_logger(__name__)
settings = get_settings()

_BASE = "https://api.apify.com/v2"
_POLL_INTERVAL = 3  # segundos entre checks
_TIMEOUT = 300  # segundos max de espera


async def _get_api_key() -> str:
    """Obtiene API key de DB (integraciones) o .env como fallback."""
    from repositories import integrations_repository
    key = await integrations_repository.obtener_api_key("apify")
    return key or settings.APIFY_API_KEY


async def run_actor(actor_id: str, input_data: dict) -> dict:
    """
    Ejecuta un Actor de Apify y espera a que termine.

    Args:
        actor_id: ID o nombre del Actor (ej. 'compass/google-maps-scraper').
        input_data: JSON de input para el Actor.

    Returns:
        Dict con la info del run finalizado.

    Raises:
        AppError: si el run falla o excede el timeout.
    """
    url = f"{_BASE}/acts/{actor_id}/runs"
    api_key = await _get_api_key()
    headers = {"Authorization": f"Bearer {api_key}"}

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, json=input_data, headers=headers)
            resp.raise_for_status()
            run_info = resp.json()["data"]
            run_id = run_info["id"]
            log.info("Apify run iniciado: actor=%s run=%s", actor_id, run_id)

            # Polling hasta que termine
            elapsed = 0
            status_url = f"{_BASE}/actor-runs/{run_id}"
            while elapsed < _TIMEOUT:
                await asyncio.sleep(_POLL_INTERVAL)
                elapsed += _POLL_INTERVAL
                check = await client.get(status_url, headers=headers)
                check.raise_for_status()
                status = check.json()["data"]["status"]
                if status == "SUCCEEDED":
                    log.info("Apify run completado: %s (%ds)", actor_id, elapsed)
                    return check.json()["data"]
                if status in ("FAILED", "ABORTED", "TIMED-OUT"):
                    raise AppError(
                        f"Apify run {status}: {actor_id}",
                        "APIFY_RUN_FAILED", 502,
                    )

            raise AppError(
                f"Apify run timeout ({_TIMEOUT}s): {actor_id}",
                "APIFY_RUN_TIMEOUT", 504,
            )
    except AppError:
        raise
    except Exception as exc:
        log.error("Error ejecutando Actor %s: %s", actor_id, exc)
        raise AppError(
            f"Error conectando con Apify: {actor_id}",
            "APIFY_CONNECTION_ERROR", 502,
        ) from exc


async def get_dataset_items(dataset_id: str) -> list[dict]:
    """
    Descarga los items de un dataset de Apify.

    Args:
        dataset_id: ID del dataset (viene del run).

    Returns:
        Lista de dicts con los resultados.
    """
    url = f"{_BASE}/datasets/{dataset_id}/items"
    api_key = await _get_api_key()
    headers = {"Authorization": f"Bearer {api_key}"}

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            items = resp.json()
            log.info("Dataset %s: %d items descargados", dataset_id, len(items))
            return items
    except Exception as exc:
        log.error("Error descargando dataset %s: %s", dataset_id, exc)
        raise AppError(
            "Error descargando resultados de Apify",
            "APIFY_DATASET_ERROR", 502,
        ) from exc
