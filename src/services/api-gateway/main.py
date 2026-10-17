import os
import requests

from urllib.parse import quote
from fastapi import FastAPI, HTTPException


DATA_SERVICE = os.getenv(
    "DATA_SERVICE_URL",
    "http://data-service:8001"
)

RISK_SERVICE = os.getenv(
    "RISK_SERVICE_URL",
    "http://risk-service:8002"
)


app = FastAPI(
    title="API Gateway - Riesgo de Incendios Forestales",
    version="1.0"
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/riesgo/{comuna}")
def obtener_riesgo(comuna: str):

    try:
        comuna_url = quote(comuna, safe="")

        respuesta_datos = requests.get(
            f"{DATA_SERVICE}/variables/{comuna_url}",
            timeout=10
        )

    except requests.RequestException:
        raise HTTPException(
            status_code=503,
            detail="Data Service no disponible"
        )

    if respuesta_datos.status_code == 404:
        raise HTTPException(
            status_code=404,
            detail="Comuna no encontrada"
        )

    if respuesta_datos.status_code != 200:
        raise HTTPException(
            status_code=500,
            detail="Error al obtener las variables"
        )

    variables = respuesta_datos.json()

    try:
        respuesta_riesgo = requests.post(
            f"{RISK_SERVICE}/predecir",
            json=variables,
            timeout=10
        )

    except requests.RequestException:
        raise HTTPException(
            status_code=503,
            detail="Risk Service no disponible"
        )

    if respuesta_riesgo.status_code != 200:
        raise HTTPException(
            status_code=500,
            detail="Error al calcular el riesgo"
        )

    resultado = respuesta_riesgo.json()

    return {
        "comuna": comuna,
        "nivel_riesgo": resultado["nivel_riesgo"]
    }