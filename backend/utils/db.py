"""Utilidades de base de datos — helpers para conversion de tipos asyncpg."""
from __future__ import annotations

import uuid
from datetime import datetime


def record_to_dict(record) -> dict:
    """Convierte un asyncpg.Record a dict serializable.

    Args:
        record: asyncpg.Record o None.

    Returns:
        dict con los valores del record, o {} si record es None.
    """
    if record is None:
        return {}
    row = dict(record)
    for key, val in list(row.items()):
        if isinstance(val, uuid.UUID):
            row[key] = str(val)
        elif isinstance(val, datetime):
            row[key] = val.isoformat()
    return row


METODOS_BUSQUEDA_VALIDOS = frozenset([
    "claude_ai", "apollo", "perplexity", "google_maps",
    "instagram", "scraping_web", "carga_manual",
])
