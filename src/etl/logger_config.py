import logging
from pathlib import Path


RUTA_LOGS = Path("logs")

RUTA_LOGS.mkdir(
    parents=True,
    exist_ok=True
)


def obtener_logger(nombre, archivo):

    logger = logging.getLogger(nombre)

    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    formato = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s"
    )

    handler = logging.FileHandler(
        RUTA_LOGS / archivo,
        encoding="utf-8"
    )

    handler.setFormatter(formato)

    logger.addHandler(handler)

    return logger