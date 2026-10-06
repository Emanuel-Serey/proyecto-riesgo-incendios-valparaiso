from pathlib import Path
import os
import logging
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text, URL

BASE_DIR = Path(__file__).resolve().parents[2]
PROCESSED = BASE_DIR / "data/processed"
LOGS = BASE_DIR / "logs"
RUTA_DATASET = PROCESSED / "dataset_modelo_diario.csv"

LOGS.mkdir(parents=True, exist_ok=True)
load_dotenv(BASE_DIR / ".env")

logger = logging.getLogger("carga")
logger.setLevel(logging.INFO)
logger.propagate = False

if not logger.handlers:
    fmt = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    fh = logging.FileHandler(LOGS / "carga_bd.log", encoding="utf-8")
    sh = logging.StreamHandler()
    fh.setFormatter(fmt)
    sh.setFormatter(fmt)
    logger.addHandler(fh)
    logger.addHandler(sh)

COLUMNAS = [
    "comuna",
    "fecha_objetivo",
    "fecha_meteorologica",
    "codigo_estacion_principal",
    "codigo_estacion_usada",
    "nombre_estacion_usada",
    "uso_respaldo",
    "distancia_estacion_km",
    "temperatura_media",
    "temperatura_max",
    "humedad_media",
    "humedad_min",
    "viento_medio",
    "viento_max",
    "cobertura_pct",
    "vegetacion_cobertura",
    "anio_cobertura",
    "incendios_historicos",
    "cantidad_incendios",
    "superficie_afectada",
    "ocurrencia_incendio"
]

def obtener_engine():
    config = {
        "host": os.getenv("DB_HOST"),
        "database": os.getenv("DB_NAME"),
        "username": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD")
    }

    faltantes = [k for k, v in config.items() if not v]
    if faltantes:
        raise ValueError(
            f"Faltan variables de conexión en .env: {', '.join(faltantes)}"
        )

    url = URL.create(
        "postgresql+psycopg",
        username=config["username"],
        password=config["password"],
        host=config["host"],
        port=int(os.getenv("DB_PORT", "5432")),
        database=config["database"]
    )

    return create_engine(url, future=True)

def preparar_dataframe():
    if not RUTA_DATASET.exists():
        raise FileNotFoundError(
            f"No existe el dataset: {RUTA_DATASET}"
        )

    df = pd.read_csv(
        RUTA_DATASET,
        parse_dates=["fecha_objetivo", "fecha_meteorologica"]
    )

    faltantes = [c for c in COLUMNAS if c not in df.columns]
    if faltantes:
        raise ValueError(
            f"Faltan columnas en dataset_modelo_diario.csv: {faltantes}"
        )

    df = df[COLUMNAS].copy()

    df["fecha_objetivo"] = df["fecha_objetivo"].dt.date
    df["fecha_meteorologica"] = df["fecha_meteorologica"].dt.date

    for col in ["codigo_estacion_principal", "codigo_estacion_usada"]:
        df[col] = pd.to_numeric(df[col], errors="raise").astype("Int64").astype(str)

    df["anio_cobertura"] = pd.to_numeric(
        df["anio_cobertura"], errors="raise"
    ).astype(int)

    df["cantidad_incendios"] = pd.to_numeric(
        df["cantidad_incendios"], errors="raise"
    ).astype(int)

    df["ocurrencia_incendio"] = pd.to_numeric(
        df["ocurrencia_incendio"], errors="raise"
    ).astype(int)

    if not pd.api.types.is_bool_dtype(df["uso_respaldo"]):
        mapa_bool = {
            "true": True, "false": False,
            "1": True, "0": False
        }
        df["uso_respaldo"] = (
            df["uso_respaldo"]
            .astype(str)
            .str.strip()
            .str.lower()
            .map(mapa_bool)
        )

    if df["uso_respaldo"].isna().any():
        raise ValueError("Se encontraron valores inválidos en uso_respaldo.")

    if df.isna().any().any():
        columnas_nulas = df.columns[df.isna().any()].tolist()
        raise ValueError(
            f"El dataset contiene nulos en: {columnas_nulas}"
        )

    logger.info(
        "Dataset preparado | Registros=%s | Comunas=%s.",
        len(df),
        df["comuna"].nunique()
    )

    return df

def crear_estructura(conn):
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS public.observaciones_incendios_diarias (
            comuna VARCHAR(80) NOT NULL,
            fecha_objetivo DATE NOT NULL,
            fecha_meteorologica DATE NOT NULL,

            codigo_estacion_principal VARCHAR(10) NOT NULL,
            codigo_estacion_usada VARCHAR(10) NOT NULL,
            nombre_estacion_usada VARCHAR(120) NOT NULL,
            uso_respaldo BOOLEAN NOT NULL,
            distancia_estacion_km DOUBLE PRECISION NOT NULL,

            temperatura_media DOUBLE PRECISION NOT NULL,
            temperatura_max DOUBLE PRECISION NOT NULL,
            humedad_media DOUBLE PRECISION NOT NULL,
            humedad_min DOUBLE PRECISION NOT NULL,
            viento_medio DOUBLE PRECISION NOT NULL,
            viento_max DOUBLE PRECISION NOT NULL,
            cobertura_pct DOUBLE PRECISION NOT NULL,

            vegetacion_cobertura VARCHAR(150) NOT NULL,
            anio_cobertura SMALLINT NOT NULL,
            incendios_historicos DOUBLE PRECISION NOT NULL,

            cantidad_incendios INTEGER NOT NULL,
            superficie_afectada DOUBLE PRECISION NOT NULL,
            ocurrencia_incendio SMALLINT NOT NULL
                CHECK (ocurrencia_incendio IN (0, 1)),

            PRIMARY KEY (comuna, fecha_objetivo)
        );
    """))

    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_incendios_fecha
        ON public.observaciones_incendios_diarias(fecha_objetivo);
    """))

    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_incendios_comuna
        ON public.observaciones_incendios_diarias(comuna);
    """))

    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_incendios_target
        ON public.observaciones_incendios_diarias(ocurrencia_incendio);
    """))

    logger.info("Tabla e índices PostgreSQL preparados.")

def crear_vista(conn):
    conn.execute(text("""
        CREATE OR REPLACE VIEW public.dataset_modelo_diario AS
        SELECT
            comuna,
            fecha_objetivo,
            temperatura_media,
            temperatura_max,
            humedad_media,
            humedad_min,
            viento_medio,
            viento_max,
            vegetacion_cobertura,
            incendios_historicos,
            ocurrencia_incendio
        FROM public.observaciones_incendios_diarias;
    """))

    logger.info("Vista dataset_modelo_diario creada correctamente.")

def cargar():
    logger.info("Inicio de carga del dataset V2 a PostgreSQL.")

    try:
        df = preparar_dataframe()
        engine = obtener_engine()

        with engine.begin() as conn:
            bd = conn.execute(
                text("SELECT current_database();")
            ).scalar()

            logger.info("Conexión PostgreSQL correcta | Base=%s.", bd)

            crear_estructura(conn)

            registros_previos = conn.execute(text("""
                SELECT COUNT(*)
                FROM public.observaciones_incendios_diarias;
            """)).scalar()

            logger.info(
                "Registros anteriores en tabla=%s.",
                registros_previos
            )

            conn.execute(text("""
                TRUNCATE TABLE public.observaciones_incendios_diarias;
            """))

            df.to_sql(
                "observaciones_incendios_diarias",
                con=conn,
                schema="public",
                if_exists="append",
                index=False,
                method="multi",
                chunksize=2000
            )

            crear_vista(conn)

            resultado = conn.execute(text("""
                SELECT
                    COUNT(*) AS registros,
                    COUNT(DISTINCT comuna) AS comunas,
                    SUM(ocurrencia_incendio) AS positivos,
                    MIN(fecha_objetivo) AS fecha_min,
                    MAX(fecha_objetivo) AS fecha_max
                FROM public.observaciones_incendios_diarias;
            """)).mappings().one()

            if resultado["registros"] != len(df):
                raise RuntimeError(
                    f"CSV={len(df)} registros, PostgreSQL={resultado['registros']}."
                )

            logger.info(
                "Carga verificada | Registros=%s | Comunas=%s | "
                "Positivos=%s | Rango=%s a %s.",
                resultado["registros"],
                resultado["comunas"],
                resultado["positivos"],
                resultado["fecha_min"],
                resultado["fecha_max"]
            )

        engine.dispose()
        logger.info("Carga PostgreSQL finalizada correctamente.")

    except Exception:
        logger.exception("Error durante la carga PostgreSQL.")
        raise

if __name__ == "__main__":
    cargar()