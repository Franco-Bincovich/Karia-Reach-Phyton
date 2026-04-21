"""
Cliente de PostgreSQL via asyncpg.

Expone un pool de conexiones global que se inicializa en el startup
de FastAPI y se cierra en el shutdown. El resto del codigo consume
el pool a traves de get_pool().
"""

from typing import Optional

import asyncpg
from asyncpg import Pool

from config.settings import get_settings
from logger import get_logger

log = get_logger(__name__)

_pool: Optional[Pool] = None


async def init_pool() -> None:
    """
    Crea e inicializa el pool de conexiones contra PostgreSQL.

    Lee la configuracion desde settings (pg_host, pg_port, pg_user,
    pg_password, pg_database, pg_pool_min_size, pg_pool_max_size).
    Debe llamarse una sola vez durante el startup de FastAPI.

    Raises:
        Exception: si asyncpg no puede conectarse al servidor.
    """
    global _pool
    settings = get_settings()
    dsn = (
        f"postgresql://{settings.pg_user}:{settings.pg_password}"
        f"@{settings.pg_host}:{settings.pg_port}/{settings.pg_database}"
    )
    _pool = await asyncpg.create_pool(
        dsn=dsn,
        min_size=settings.pg_pool_min_size,
        max_size=settings.pg_pool_max_size,
    )
    log.info(
        "Postgres pool inicializado — %s:%s/%s (min=%s max=%s)",
        settings.pg_host,
        settings.pg_port,
        settings.pg_database,
        settings.pg_pool_min_size,
        settings.pg_pool_max_size,
    )


async def close_pool() -> None:
    """
    Cierra el pool de conexiones de PostgreSQL.

    Debe llamarse durante el shutdown de FastAPI. Si el pool no fue
    inicializado, la funcion retorna sin hacer nada.
    """
    global _pool
    if _pool is None:
        return
    await _pool.close()
    _pool = None
    log.info("Postgres pool cerrado")


def get_pool() -> Pool:
    """
    Devuelve el pool de conexiones ya inicializado.

    Returns:
        Pool de asyncpg listo para usar.

    Raises:
        RuntimeError: si init_pool() no fue llamado previamente.
    """
    if _pool is None:
        raise RuntimeError(
            "El pool de PostgreSQL no fue inicializado. "
            "Asegurate de llamar a init_pool() en el startup de FastAPI."
        )
    return _pool
