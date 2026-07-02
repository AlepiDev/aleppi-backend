# utils/logging.py
"""Configuración centralizada de logging para el backend.

Expone:
    - setup_logging(): configura handlers (archivo rotativo diario + consola). Idempotente.
    - get_logger(name): devuelve un logger listo para usar en cualquier módulo/router.

El archivo de log rota cada medianoche y conserva los últimos 14 días.
"""
import logging
import os
from logging.handlers import TimedRotatingFileHandler

# Carpeta de logs en la raíz del proyecto: <repo>/logs/
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
LOG_FILE = os.path.join(LOG_DIR, "aleppi.log")

LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Logger raíz de la aplicación. Todos los loggers nombrados cuelgan de la raíz.
_APP_LOGGER_NAME = "aleppi"

_configured = False


def setup_logging() -> None:
    """Configura el logging de la aplicación una sola vez.

    - Crea la carpeta ``logs/`` si no existe.
    - Añade un ``TimedRotatingFileHandler`` (rotación diaria, 14 backups).
    - Añade un ``StreamHandler`` para mantener la salida en consola.
    - Nivel configurable vía la variable de entorno ``LOG_LEVEL`` (default INFO).
    """
    global _configured
    if _configured:
        return

    os.makedirs(LOG_DIR, exist_ok=True)

    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)

    file_handler = TimedRotatingFileHandler(
        LOG_FILE,
        when="midnight",
        interval=1,
        backupCount=14,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Evita duplicar handlers si setup_logging() se llama más de una vez.
    if not any(isinstance(h, TimedRotatingFileHandler) for h in root_logger.handlers):
        root_logger.addHandler(file_handler)
    if not any(isinstance(h, logging.StreamHandler) and not isinstance(h, TimedRotatingFileHandler)
               for h in root_logger.handlers):
        root_logger.addHandler(console_handler)

    # Asegura que el logger de la app use el nivel configurado.
    logging.getLogger(_APP_LOGGER_NAME).setLevel(level)

    _configured = True


def get_logger(name: str | None = None) -> logging.Logger:
    """Devuelve un logger configurado.

    Úsalo en cada router/módulo::

        from utils.logging import get_logger
        logger = get_logger(__name__)
    """
    if not _configured:
        setup_logging()
    return logging.getLogger(name or _APP_LOGGER_NAME)
