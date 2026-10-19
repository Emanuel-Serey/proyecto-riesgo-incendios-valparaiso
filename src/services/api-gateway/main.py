import os
import requests

from urllib.parse import quote
from fastapi import FastAPI, HTTPException
from prometheus_fastapi_instrumentator import Instrumentator

DATA_SERVICE = os.getenv("DATA_SERVICE_URL", "http://data-service:8001")
RISK_SERVICE = os.getenv("RISK_SERVICE_URL", "http://risk-service:8002")

app = FastAPI(
    title="API Gateway - Riesgo de Incendios Forestales",
    version="2.0"
)

Instrumentator().instrument(app).expose(
    app,
    endpoint="/metrics",
    include_in_schema=False
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/riesgo/{comuna}")
def obtener_riesgo(comuna: str):
    comuna_url = quote(comuna, safe="")

    try:
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
            status_code=502,
            detail="Error al obtener las variables"
        )

    variables = respuesta_datos.json()

    datos_modelo = {
        "id_variables": variables["id_variables"],
        "comuna": variables["comuna"],
        "fecha_prediccion": variables["fecha_prediccion"],
        "temperatura_media": variables["temperatura_media"],
        "humedad_media": variables["humedad_media"],
        "viento_medio": variables["viento_medio"],
        "vegetacion_cobertura": variables["vegetacion_cobertura"],
        "incendios_historicos": variables["incendios_historicos"]
    }

    try:
        respuesta_riesgo = requests.post(
            f"{RISK_SERVICE}/predecir",
            json=datos_modelo,
            timeout=10
        )
    except requests.RequestException:
        raise HTTPException(
            status_code=503,
            detail="Risk Service no disponible"
        )

    if respuesta_riesgo.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail="Error al calcular el riesgo"
        )

    riesgo = respuesta_riesgo.json()

    return {
        "comuna": variables["comuna"],
        "fecha_prediccion": variables["fecha_prediccion"],
        "fecha_meteorologia": variables["fecha_meteorologia"],
        "nivel_riesgo": riesgo["nivel_riesgo"],
        "score_modelo": riesgo["score_modelo"],
        "modelo_version": riesgo["modelo_version"],
        "temperatura_media": variables["temperatura_media"],
        "humedad_media": variables["humedad_media"],
        "viento_medio": variables["viento_medio"],
        "vegetacion_cobertura": variables["vegetacion_cobertura"],
        "incendios_historicos": variables["incendios_historicos"]
    }