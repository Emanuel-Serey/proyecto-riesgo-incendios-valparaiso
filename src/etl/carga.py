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
RUTA_VARIABLES_ACTUALES = PROCESSED / "variables_actuales.csv"

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

COLUMNAS_DATASET = [
    "comuna", "fecha_objetivo", "fecha_meteorologica",
    "codigo_estacion_principal", "codigo_estacion_usada",
    "nombre_estacion_usada", "uso_respaldo", "distancia_estacion_km",
    "temperatura_media", "temperatura_max", "humedad_media", "humedad_min",
    "viento_medio", "viento_max", "cobertura_pct",
    "vegetacion_cobertura", "anio_cobertura", "incendios_historicos",
    "cantidad_incendios", "superficie_afectada", "ocurrencia_incendio"
]

COLUMNAS_ACTUALES = [
    "comuna", "fecha_prediccion", "fecha_meteorologia",
    "codigo_estacion_principal", "codigo_estacion_usada",
    "nombre_estacion_usada", "uso_respaldo", "distancia_estacion_km",
    "temperatura_media", "temperatura_max", "humedad_media", "humedad_min",
    "viento_medio", "viento_max", "cobertura_pct",
    "vegetacion_cobertura", "anio_cobertura", "incendios_historicos"
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


def convertir_booleano(df, columna="uso_respaldo"):
    if pd.api.types.is_bool_dtype(df[columna]):
        return df

    mapa = {
        "true": True, "false": False,
        "1": True, "0": False
    }

    df[columna] = (
        df[columna]
        .astype(str)
        .str.strip()
        .str.lower()
        .map(mapa)
    )

    if df[columna].isna().any():
        raise ValueError(
            f"Se encontraron valores inválidos en {columna}."
        )

    return df


# =========================
# DATASET DE ENTRENAMIENTO
# =========================

def preparar_dataframe():
    if not RUTA_DATASET.exists():
        raise FileNotFoundError(
            f"No existe el dataset: {RUTA_DATASET}"
        )

    df = pd.read_csv(
        RUTA_DATASET,
        parse_dates=["fecha_objetivo", "fecha_meteorologica"]
    )

    faltantes = [
        c for c in COLUMNAS_DATASET
        if c not in df.columns
    ]

    if faltantes:
        raise ValueError(
            f"Faltan columnas en dataset_modelo_diario.csv: {faltantes}"
        )

    df = df[COLUMNAS_DATASET].copy()

    df["fecha_objetivo"] = df["fecha_objetivo"].dt.date
    df["fecha_meteorologica"] = df["fecha_meteorologica"].dt.date

    for col in [
        "codigo_estacion_principal",
        "codigo_estacion_usada"
    ]:
        df[col] = (
            pd.to_numeric(df[col], errors="raise")
            .astype("Int64")
            .astype(str)
        )

    df["anio_cobertura"] = pd.to_numeric(
        df["anio_cobertura"], errors="raise"
    ).astype(int)

    df["cantidad_incendios"] = pd.to_numeric(
        df["cantidad_incendios"], errors="raise"
    ).astype(int)

    df["ocurrencia_incendio"] = pd.to_numeric(
        df["ocurrencia_incendio"], errors="raise"
    ).astype(int)

    df = convertir_booleano(df)

    if df.isna().any().any():
        columnas_nulas = df.columns[df.isna().any()].tolist()
        raise ValueError(
            f"El dataset contiene nulos en: {columnas_nulas}"
        )

    logger.info(
        "Dataset preparado | Registros=%s | Comunas=%s.",
        len(df), df["comuna"].nunique()
    )

    return df


def crear_estructura_dataset(conn):
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

    logger.info("Tabla e índices del dataset preparados.")


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

    logger.info(
        "Vista dataset_modelo_diario creada correctamente."
    )


def cargar():
    logger.info(
        "Inicio de carga del dataset V2 a PostgreSQL."
    )

    try:
        df = preparar_dataframe()
        engine = obtener_engine()

        with engine.begin() as conn:
            bd = conn.execute(
                text("SELECT current_database();")
            ).scalar()

            logger.info(
                "Conexión PostgreSQL correcta | Base=%s.",
                bd
            )

            crear_estructura_dataset(conn)

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
                    f"CSV={len(df)} registros, "
                    f"PostgreSQL={resultado['registros']}."
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

        logger.info(
            "Carga PostgreSQL finalizada correctamente."
        )

    except Exception:
        logger.exception(
            "Error durante la carga PostgreSQL."
        )
        raise


# =========================
# VARIABLES ACTUALES
# =========================

def preparar_variables_actuales():
    if not RUTA_VARIABLES_ACTUALES.exists():
        raise FileNotFoundError(
            f"No existe: {RUTA_VARIABLES_ACTUALES}"
        )

    df = pd.read_csv(
        RUTA_VARIABLES_ACTUALES,
        parse_dates=[
            "fecha_prediccion",
            "fecha_meteorologia"
        ]
    )

    faltantes = [
        c for c in COLUMNAS_ACTUALES
        if c not in df.columns
    ]

    if faltantes:
        raise ValueError(
            f"Faltan columnas en variables_actuales.csv: {faltantes}"
        )

    df = df[COLUMNAS_ACTUALES].copy()

    df["fecha_prediccion"] = (
        df["fecha_prediccion"].dt.date
    )

    df["fecha_meteorologia"] = (
        df["fecha_meteorologia"].dt.date
    )

    for col in [
        "codigo_estacion_principal",
        "codigo_estacion_usada"
    ]:
        df[col] = (
            pd.to_numeric(df[col], errors="raise")
            .astype("Int64")
            .astype(str)
        )

    df["anio_cobertura"] = pd.to_numeric(
        df["anio_cobertura"],
        errors="raise"
    ).astype(int)

    df = convertir_booleano(df)

    if df.isna().any().any():
        columnas_nulas = df.columns[
            df.isna().any()
        ].tolist()

        raise ValueError(
            f"variables_actuales contiene nulos en: "
            f"{columnas_nulas}"
        )

    logger.info(
        "Variables actuales preparadas | "
        "Registros=%s | Comunas=%s | Fecha=%s.",
        len(df),
        df["comuna"].nunique(),
        df["fecha_prediccion"].max()
    )

    return df


def crear_estructura_operacional(conn):
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS public.variables_actuales (
            id_variables BIGSERIAL PRIMARY KEY,

            comuna VARCHAR(80) NOT NULL,
            fecha_prediccion DATE NOT NULL,
            fecha_meteorologia DATE NOT NULL,

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

            UNIQUE (comuna, fecha_prediccion)
        );
    """))

    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_variables_fecha
        ON public.variables_actuales(fecha_prediccion);
    """))

    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_variables_comuna
        ON public.variables_actuales(comuna);
    """))

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS public.registro_inferencias (
            id_inferencia BIGSERIAL PRIMARY KEY,
            id_variables BIGINT NOT NULL
                REFERENCES public.variables_actuales(id_variables)
                ON DELETE CASCADE,

            score_modelo DOUBLE PRECISION NOT NULL
                CHECK (score_modelo >= 0 AND score_modelo <= 1),

            nivel_riesgo VARCHAR(10) NOT NULL
                CHECK (nivel_riesgo IN ('Bajo', 'Medio', 'Alto')),

            modelo_version VARCHAR(50) NOT NULL,
            fecha_inferencia TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

            UNIQUE (id_variables, modelo_version)
        );
    """))

    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_inferencias_fecha
        ON public.registro_inferencias(fecha_inferencia);
    """))

    logger.info(
        "Tablas variables_actuales y registro_inferencias preparadas."
    )


def cargar_variables_actuales():
    logger.info(
        "Inicio de carga de variables actuales a PostgreSQL."
    )

    try:
        df = preparar_variables_actuales()
        engine = obtener_engine()

        sql = text("""
            INSERT INTO public.variables_actuales (
                comuna,
                fecha_prediccion,
                fecha_meteorologia,
                codigo_estacion_principal,
                codigo_estacion_usada,
                nombre_estacion_usada,
                uso_respaldo,
                distancia_estacion_km,
                temperatura_media,
                temperatura_max,
                humedad_media,
                humedad_min,
                viento_medio,
                viento_max,
                cobertura_pct,
                vegetacion_cobertura,
                anio_cobertura,
                incendios_historicos
            )
            VALUES (
                :comuna,
                :fecha_prediccion,
                :fecha_meteorologia,
                :codigo_estacion_principal,
                :codigo_estacion_usada,
                :nombre_estacion_usada,
                :uso_respaldo,
                :distancia_estacion_km,
                :temperatura_media,
                :temperatura_max,
                :humedad_media,
                :humedad_min,
                :viento_medio,
                :viento_max,
                :cobertura_pct,
                :vegetacion_cobertura,
                :anio_cobertura,
                :incendios_historicos
            )

            ON CONFLICT (comuna, fecha_prediccion)

            DO UPDATE SET
                fecha_meteorologia = EXCLUDED.fecha_meteorologia,
                codigo_estacion_principal = EXCLUDED.codigo_estacion_principal,
                codigo_estacion_usada = EXCLUDED.codigo_estacion_usada,
                nombre_estacion_usada = EXCLUDED.nombre_estacion_usada,
                uso_respaldo = EXCLUDED.uso_respaldo,
                distancia_estacion_km = EXCLUDED.distancia_estacion_km,
                temperatura_media = EXCLUDED.temperatura_media,
                temperatura_max = EXCLUDED.temperatura_max,
                humedad_media = EXCLUDED.humedad_media,
                humedad_min = EXCLUDED.humedad_min,
                viento_medio = EXCLUDED.viento_medio,
                viento_max = EXCLUDED.viento_max,
                cobertura_pct = EXCLUDED.cobertura_pct,
                vegetacion_cobertura = EXCLUDED.vegetacion_cobertura,
                anio_cobertura = EXCLUDED.anio_cobertura,
                incendios_historicos = EXCLUDED.incendios_historicos;
        """)

        registros = df.to_dict(orient="records")

        with engine.begin() as conn:
            bd = conn.execute(
                text("SELECT current_database();")
            ).scalar()

            logger.info(
                "Conexión PostgreSQL correcta | Base=%s.",
                bd
            )

            crear_estructura_operacional(conn)
            conn.execute(sql, registros)

            fecha = max(
                registro["fecha_prediccion"]
                for registro in registros
            )

            resultado = conn.execute(
                text("""
                    SELECT
                        COUNT(*) AS registros,
                        COUNT(DISTINCT comuna) AS comunas
                    FROM public.variables_actuales
                    WHERE fecha_prediccion = :fecha;
                """),
                {"fecha": fecha}
            ).mappings().one()

            logger.info(
                "Variables actuales cargadas | "
                "Fecha=%s | Registros=%s | Comunas=%s.",
                fecha,
                resultado["registros"],
                resultado["comunas"]
            )

        engine.dispose()

        logger.info(
            "Carga de variables actuales finalizada correctamente."
        )

    except Exception:
        logger.exception(
            "Error durante carga de variables actuales."
        )
        raise


if __name__ == "__main__":
    cargar()