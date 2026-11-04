from pathlib import Path
import os
import logging
import joblib
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text, URL

BASE_DIR = Path(__file__).resolve().parents[2]
MODELO = BASE_DIR / "models/random_forest_incendios.joblib"
LOGS = BASE_DIR / "logs"
LOGS.mkdir(parents=True, exist_ok=True)

load_dotenv(BASE_DIR / ".env")

MODELO_VERSION = os.getenv("MODELO_VERSION", "random_forest_v1")

logger = logging.getLogger("inferencia")
logger.setLevel(logging.INFO)
logger.propagate = False

if not logger.handlers:
    fmt = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    fh = logging.FileHandler(LOGS / "inferencia.log", encoding="utf-8")
    sh = logging.StreamHandler()
    fh.setFormatter(fmt)
    sh.setFormatter(fmt)
    logger.addHandler(fh)
    logger.addHandler(sh)


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


def cargar_modelo():
    if not MODELO.exists():
        raise FileNotFoundError(f"No existe el modelo: {MODELO}")

    modelo = joblib.load(MODELO)
    logger.info(
        "Modelo cargado correctamente | Archivo=%s | Versión=%s.",
        MODELO.name, MODELO_VERSION
    )
    return modelo


def obtener_variables_actuales(engine):
    consulta = text("""
        SELECT
            id_variables,
            comuna,
            fecha_prediccion,
            fecha_meteorologia,
            temperatura_media,
            humedad_media,
            viento_medio,
            vegetacion_cobertura,
            incendios_historicos
        FROM public.variables_actuales
        WHERE fecha_prediccion = (
            SELECT MAX(fecha_prediccion)
            FROM public.variables_actuales
        )
        ORDER BY comuna;
    """)

    df = pd.read_sql(consulta, engine)

    if df.empty:
        raise ValueError(
            "No existen variables actuales en PostgreSQL para realizar inferencia."
        )

    variables_modelo = [
        "temperatura_media",
        "humedad_media",
        "viento_medio",
        "vegetacion_cobertura",
        "incendios_historicos"
    ]

    faltantes = [c for c in variables_modelo if c not in df.columns]
    if faltantes:
        raise ValueError(f"Faltan variables requeridas por el modelo: {faltantes}")

    if df[variables_modelo].isna().any().any():
        nulos = df[variables_modelo].isna().sum()
        raise ValueError(
            f"Existen nulos en las variables del modelo: {nulos.to_dict()}"
        )

    if df["comuna"].nunique() != 36:
        raise ValueError(
            f"Se esperaban 36 comunas y se encontraron {df['comuna'].nunique()}."
        )

    logger.info(
        "Variables cargadas | Registros=%s | Comunas=%s | "
        "Meteorología=%s | Predicción=%s.",
        len(df),
        df["comuna"].nunique(),
        df["fecha_meteorologia"].min(),
        df["fecha_prediccion"].max()
    )

    return df


def clasificar_riesgo(score):
    if score < 0.35:
        return "Bajo"
    if score < 0.50:
        return "Medio"
    return "Alto"


def predecir(modelo, datos):
    columnas = [
        "temperatura_media",
        "humedad_media",
        "viento_medio",
        "vegetacion_cobertura",
        "incendios_historicos"
    ]

    X = datos[columnas]
    resultado = datos[
        ["id_variables", "comuna", "fecha_prediccion"]
    ].copy()

    resultado["score_modelo"] = modelo.predict_proba(X)[:, 1]
    resultado["nivel_riesgo"] = resultado["score_modelo"].apply(clasificar_riesgo)

    logger.info(
        "Inferencias generadas | Bajo=%s | Medio=%s | Alto=%s.",
        (resultado["nivel_riesgo"] == "Bajo").sum(),
        (resultado["nivel_riesgo"] == "Medio").sum(),
        (resultado["nivel_riesgo"] == "Alto").sum()
    )

    return resultado


def guardar_inferencias(engine, resultados):
    consulta = text("""
        INSERT INTO public.registro_inferencias (
            id_variables,
            score_modelo,
            nivel_riesgo,
            modelo_version
        )
        VALUES (
            :id_variables,
            :score_modelo,
            :nivel_riesgo,
            :modelo_version
        )
        ON CONFLICT (id_variables, modelo_version)
        DO UPDATE SET
            score_modelo = EXCLUDED.score_modelo,
            nivel_riesgo = EXCLUDED.nivel_riesgo,
            fecha_inferencia = CURRENT_TIMESTAMP;
    """)

    registros = [
        {
            "id_variables": int(fila["id_variables"]),
            "score_modelo": float(fila["score_modelo"]),
            "nivel_riesgo": fila["nivel_riesgo"],
            "modelo_version": MODELO_VERSION
        }
        for _, fila in resultados.iterrows()
    ]

    with engine.begin() as conn:
        conn.execute(consulta, registros)

        fecha = resultados["fecha_prediccion"].max()

        verificacion = conn.execute(
            text("""
                SELECT
                    COUNT(*) AS registros,
                    COUNT(*) FILTER (WHERE nivel_riesgo = 'Bajo') AS bajo,
                    COUNT(*) FILTER (WHERE nivel_riesgo = 'Medio') AS medio,
                    COUNT(*) FILTER (WHERE nivel_riesgo = 'Alto') AS alto
                FROM public.registro_inferencias ri
                JOIN public.variables_actuales va
                    ON va.id_variables = ri.id_variables
                WHERE va.fecha_prediccion = :fecha
                  AND ri.modelo_version = :modelo_version;
            """),
            {
                "fecha": fecha,
                "modelo_version": MODELO_VERSION
            }
        ).mappings().one()

    if verificacion["registros"] != len(resultados):
        raise RuntimeError(
            f"Se generaron {len(resultados)} inferencias, pero PostgreSQL "
            f"contiene {verificacion['registros']}."
        )

    logger.info(
        "Inferencias guardadas | Fecha=%s | Registros=%s | "
        "Bajo=%s | Medio=%s | Alto=%s.",
        fecha,
        verificacion["registros"],
        verificacion["bajo"],
        verificacion["medio"],
        verificacion["alto"]
    )


def ejecutar_inferencia():
    logger.info("=" * 55)
    logger.info("Inicio del pipeline de inferencia.")
    logger.info("=" * 55)

    engine = None

    try:
        engine = obtener_engine()
        modelo = cargar_modelo()
        datos = obtener_variables_actuales(engine)
        resultados = predecir(modelo, datos)
        guardar_inferencias(engine, resultados)

        logger.info(
            "Pipeline de inferencia finalizado correctamente | "
            "Fecha predicción=%s.",
            resultados["fecha_prediccion"].max()
        )

        return resultados

    except Exception:
        logger.exception("Error durante el pipeline de inferencia.")
        raise

    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    ejecutar_inferencia()