"""
Manejo global de errores.

Define AppError para errores controlados y un handler que
normaliza toda excepcion al formato JSON estandar.
"""

from fastapi import Request
from fastapi.responses import JSONResponse

from logger import get_logger

log = get_logger(__name__)


class AppError(Exception):
    """
    Error controlado de la aplicacion.

    Args:
        message: mensaje legible para el cliente.
        code: codigo SNAKE_CASE que identifica el error.
        status_code: HTTP status code.
    """

    def __init__(
        self, message: str, code: str = "INTERNAL_ERROR", status_code: int = 500
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code


async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
    """Handler para errores AppError controlados."""
    if exc.status_code < 500:
        log.warning("AppError [%s] %s", exc.code, exc.message)
    else:
        log.error("AppError [%s] %s", exc.code, exc.message)
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": True, "message": exc.message, "code": exc.code},
    )


async def generic_error_handler(_request: Request, exc: Exception) -> JSONResponse:
    """
    Handler para excepciones no controladas.

    Loguea el detalle pero devuelve un mensaje generico al cliente.
    """
    log.error("Excepcion no controlada: %s", exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": True,
            "message": "Error interno del servidor",
            "code": "INTERNAL_ERROR",
        },
    )
