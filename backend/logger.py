"""
Logger centralizado.

- Desarrollo: formato legible con colores.
- Produccion: JSON estructurado (una linea por entrada).
"""

import json
import logging
import sys
from datetime import datetime, timezone

from config.settings import get_settings


class _ColorFormatter(logging.Formatter):
    """Formato con colores ANSI para terminal en desarrollo."""

    COLORS = {
        logging.DEBUG: "\033[36m",     # cyan
        logging.INFO: "\033[32m",      # verde
        logging.WARNING: "\033[33m",   # amarillo
        logging.ERROR: "\033[31m",     # rojo
        logging.CRITICAL: "\033[35m",  # magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        """Formatea el registro con color segun nivel."""
        color = self.COLORS.get(record.levelno, self.RESET)
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        return (
            f"{color}[{ts}] [{record.levelname}] "
            f"[{record.name}] {record.getMessage()}{self.RESET}"
        )


class _JsonFormatter(logging.Formatter):
    """Formato JSON estructurado para produccion."""

    def format(self, record: logging.LogRecord) -> str:
        """Serializa el registro a JSON en una sola linea."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "module": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info and record.exc_info[1]:
            entry["exception"] = str(record.exc_info[1])
        return json.dumps(entry, ensure_ascii=False)


def get_logger(name: str) -> logging.Logger:
    """
    Devuelve un logger configurado para el modulo indicado.

    Args:
        name: nombre del modulo (usualmente __name__).

    Returns:
        Logger con handler y formato segun NODE_ENV.
    """
    logger = logging.getLogger(name)

    # Evitar duplicar handlers si se llama multiples veces
    if logger.handlers:
        return logger

    settings = get_settings()
    logger.setLevel(logging.DEBUG if not settings.is_production else logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    formatter = _JsonFormatter() if settings.is_production else _ColorFormatter()
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.propagate = False

    return logger
