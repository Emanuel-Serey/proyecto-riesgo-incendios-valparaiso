from pathlib import Path
from datetime import date
import os

import joblib
import pandas as pd

from fastapi import FastAPI, HTTPException
from prometheus_fastapi_instrumentator import Instrumentator
from pydantic import BaseModel
from sqlalchemy import create_engine, text, URL
from sqlalchemy.exc import SQLAlchemyError


BASE_DIR = Path(__file__).resolve().parent
RUTA_MODELO = BASE_DIR / "models" / "random_forest_incendios.joblib"
MODELO_VERSION = os.getenv("MODELO_VERSION", "random_forest_v1")

if not RUTA_MODELO.exists():
    raise FileNotFoundError(f"No existe el modelo: {RUTA_MODELO}")

modelo = joblib.load(RUTA_MODELO)

url = URL.create(
    drivername="postgresql+psycopg2",
    username=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    host=os.getenv("DB_HOST"),
    port=int(os.getenv("DB_PORT", 5432)),
    database=os.getenv("DB_NAME")
)

engine = create_engine(url, pool_pre_ping=True)

app = FastAPI(
    title="Risk Service - Incendios Forestales",
    version="2.0"
)

Instrumentator().instrument(app).expose(
    app,
    endpoint="/metrics",
    include_in_schema=False
)


class VariablesRiesgo(BaseModel):
    id_variables: int
    comuna: str
    fecha_prediccion: date
    temperatura_media: float
    humedad_media: float
    viento_medio: float
    vegetacion_cobertura: str
    incendios_historicos: float


def clasificar_riesgo(score: float):
    if score < 0.35:
        return "Bajo"
    if score < 0.50:
        return "Medio"
    return "Alto"


def registrar_inferencia(id_variables: int, score: float, nivel_riesgo: str):
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

    with engine.begin() as conexion:
        conexion.execute(
            consulta,
            {
                "id_variables": id_variables,
                "score_modelo": score,
                "nivel_riesgo": nivel_riesgo,
                "modelo_version": MODELO_VERSION
            }
        )


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/predecir")
def predecir(datos: VariablesRiesgo):
    try:
        entrada = pd.DataFrame([{
            "temperatura_media": datos.temperatura_media,
            "humedad_media": datos.humedad_media,
            "viento_medio": datos.viento_medio,
            "vegetacion_cobertura": datos.vegetacion_cobertura,
            "incendios_historicos": datos.incendios_historicos
        }])

        score = float(modelo.predict_proba(entrada)[0, 1])
        nivel_riesgo = clasificar_riesgo(score)

        registrar_inferencia(
            datos.id_variables,
            score,
            nivel_riesgo
        )

        return {
            "id_variables": datos.id_variables,
            "comuna": datos.comuna,
            "fecha_prediccion": datos.fecha_prediccion,
            "score_modelo": score,
            "nivel_riesgo": nivel_riesgo,
            "modelo_version": MODELO_VERSION
        }

    except SQLAlchemyError:
        raise HTTPException(
            status_code=500,
            detail="Error al registrar la inferencia en PostgreSQL"
        )

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Error durante la inferencia: {error}"
        )