from pathlib import Path

import joblib
import pandas as pd

from fastapi import FastAPI
from pydantic import BaseModel


BASE_DIR = Path(__file__).resolve().parent

RUTA_MODELO = (
    BASE_DIR
    / "models"
    / "random_forest_incendios.joblib"
)

modelo = joblib.load(RUTA_MODELO)


app = FastAPI(
    title="Risk Service - Incendios Forestales",
    version="1.0"
)


class VariablesRiesgo(BaseModel):
    temperatura_media: float
    humedad_media: float
    viento_medio: float
    vegetacion_cobertura: str
    incendios_historicos: float


def clasificar_riesgo(score: float):

    if score < 0.35:
        return "Bajo"

    elif score < 0.50:
        return "Medio"

    return "Alto"


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/predecir")
def predecir(datos: VariablesRiesgo):

    entrada = pd.DataFrame([
        datos.model_dump()
    ])

    score = modelo.predict_proba(entrada)[0, 1]

    nivel_riesgo = clasificar_riesgo(score)

    return {
        "nivel_riesgo": nivel_riesgo
    }