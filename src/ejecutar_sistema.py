from pathlib import Path
import subprocess
import sys
import logging
import time

BASE_DIR = Path(__file__).resolve().parents[1]
LOGS = BASE_DIR / "logs"
PIPELINE_ETL = BASE_DIR / "src" / "etl" / "pipeline_etl.py"

LOGS.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("sistema")
logger.setLevel(logging.INFO)
logger.propagate = False

if not logger.handlers:
    fmt = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    fh = logging.FileHandler(LOGS / "sistema.log", encoding="utf-8")
    sh = logging.StreamHandler()
    fh.setFormatter(fmt)
    sh.setFormatter(fmt)
    logger.addHandler(fh)
    logger.addHandler(sh)


def ejecutar(nombre, ruta):
    if not ruta.exists():
        raise FileNotFoundError(f"No existe: {ruta}")

    logger.info("Iniciando: %s.", nombre)
    inicio = time.perf_counter()

    subprocess.run(
        [sys.executable, str(ruta)],
        cwd=BASE_DIR,
        check=True
    )

    logger.info(
        "%s finalizado correctamente | Tiempo=%.2f s.",
        nombre,
        time.perf_counter() - inicio
    )


def ejecutar_sistema():
    logger.info("=" * 60)
    logger.info("Inicio de actualización de datos del sistema.")
    logger.info("=" * 60)

    inicio = time.perf_counter()

    try:
        ejecutar("Pipeline ETL", PIPELINE_ETL)

        logger.info("=" * 60)
        logger.info(
            "Actualización de datos finalizada correctamente | Tiempo total=%.2f s.",
            time.perf_counter() - inicio
        )
        logger.info("=" * 60)

    except subprocess.CalledProcessError as error:
        logger.exception(
            "Proceso detenido | Código de salida=%s.",
            error.returncode
        )
        raise

    except Exception:
        logger.exception("Error durante la actualización de datos.")
        raise


if __name__ == "__main__":
    ejecutar_sistema()