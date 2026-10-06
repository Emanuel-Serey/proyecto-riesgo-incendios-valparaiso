from pathlib import Path
import subprocess
import sys
import logging
import time

BASE_DIR = Path(__file__).resolve().parents[2]
ETL_DIR = BASE_DIR / "src" / "etl"
LOGS = BASE_DIR / "logs"

LOGS.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("pipeline")
logger.setLevel(logging.INFO)
logger.propagate = False

if not logger.handlers:
    fmt = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

    fh = logging.FileHandler(
        LOGS / "pipeline.log",
        encoding="utf-8"
    )
    sh = logging.StreamHandler()

    fh.setFormatter(fmt)
    sh.setFormatter(fmt)

    logger.addHandler(fh)
    logger.addHandler(sh)

ETAPAS = [
    ("Ingesta", "ingesta.py"),
    ("Limpieza y transformación", "limpieza_transformacion.py"),
    ("Integración", "integracion.py"),
    ("Validación", "validacion.py"),
    ("Carga PostgreSQL", "carga.py")
]

def ejecutar_etapa(nombre, archivo):
    ruta = ETL_DIR / archivo

    if not ruta.exists():
        raise FileNotFoundError(
            f"No existe el archivo de etapa: {ruta}"
        )

    logger.info("Iniciando etapa: %s.", nombre)
    inicio = time.perf_counter()

    try:
        subprocess.run(
            [sys.executable, str(ruta)],
            cwd=BASE_DIR,
            check=True
        )

        duracion = time.perf_counter() - inicio

        logger.info(
            "Etapa finalizada: %s | Tiempo=%.2f s.",
            nombre,
            duracion
        )

    except subprocess.CalledProcessError as e:
        logger.error(
            "Falló la etapa: %s | Código de salida=%s.",
            nombre,
            e.returncode
        )
        raise

def ejecutar_pipeline():
    logger.info("=" * 55)
    logger.info("Inicio del pipeline ETL V2.")
    logger.info("=" * 55)

    inicio_total = time.perf_counter()

    try:
        for nombre, archivo in ETAPAS:
            ejecutar_etapa(nombre, archivo)

        duracion_total = time.perf_counter() - inicio_total

        logger.info("=" * 55)
        logger.info(
            "Pipeline ETL V2 finalizado correctamente | Tiempo total=%.2f s.",
            duracion_total
        )
        logger.info("=" * 55)

    except Exception:
        duracion_total = time.perf_counter() - inicio_total

        logger.exception(
            "Pipeline ETL V2 detenido por error | Tiempo=%.2f s.",
            duracion_total
        )

        raise

if __name__ == "__main__":
    ejecutar_pipeline()