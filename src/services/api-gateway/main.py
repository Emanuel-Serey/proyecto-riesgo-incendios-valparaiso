import os
from urllib.parse import quote

import requests
from fastapi import FastAPI, HTTPException
from prometheus_fastapi_instrumentator import Instrumentator


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
    version="2.2"
)


Instrumentator().instrument(app).expose(
    app,
    endpoint="/metrics",
    include_in_schema=False
)


# =========================================================
# HEALTH DEL PROPIO GATEWAY
# Usado por Kubernetes
# =========================================================

@app.get("/health")
def health():
    return {
        "status": "ok"
    }


# =========================================================
# ESTADO GENERAL DEL SISTEMA
# Usado por el frontend
# =========================================================

@app.get("/health/system")
def health_system():
    servicios = {
        "data_service": {
            "url": DATA_SERVICE,
            "status": "unavailable"
        },
        "risk_service": {
            "url": RISK_SERVICE,
            "status": "unavailable"
        }
    }

    try:
        respuesta = requests.get(
            f"{DATA_SERVICE}/health",
            timeout=3
        )

        if respuesta.status_code == 200:
            datos = respuesta.json()

            if datos.get("status") == "ok":
                servicios[
                    "data_service"
                ]["status"] = "ok"

    except requests.RequestException:
        pass


    try:
        respuesta = requests.get(
            f"{RISK_SERVICE}/health",
            timeout=3
        )

        if respuesta.status_code == 200:
            datos = respuesta.json()

            if datos.get("status") == "ok":
                servicios[
                    "risk_service"
                ]["status"] = "ok"

    except requests.RequestException:
        pass


    sistema_operativo = all(
        servicio["status"] == "ok"
        for servicio in servicios.values()
    )


    return {
        "status": (
            "ok"
            if sistema_operativo
            else "degraded"
        ),
        "services": {
            "data_service":
                servicios[
                    "data_service"
                ]["status"],

            "risk_service":
                servicios[
                    "risk_service"
                ]["status"]
        }
    }


# =========================================================
# CONSULTA DE RIESGO
# =========================================================

@app.get("/riesgo/{comuna}")
def obtener_riesgo(comuna: str):

    comuna_url = quote(
        comuna,
        safe=""
    )


    # -----------------------------------------------------
    # OBTENER VARIABLES
    # -----------------------------------------------------

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
            detail="Error al consultar Data Service"
        )


    variables = respuesta_datos.json()


    # -----------------------------------------------------
    # PREPARAR ENTRADA DEL MODELO
    # -----------------------------------------------------

    datos_modelo = {
        "id_variables":
            variables["id_variables"],

        "comuna":
            variables["comuna"],

        "fecha_prediccion":
            variables["fecha_prediccion"],

        "temperatura_media":
            variables["temperatura_media"],

        "humedad_media":
            variables["humedad_media"],

        "viento_medio":
            variables["viento_medio"],

        "vegetacion_cobertura":
            variables["vegetacion_cobertura"],

        "incendios_historicos":
            variables["incendios_historicos"]
    }


    # -----------------------------------------------------
    # INFERENCIA + EXPLICABILIDAD
    # -----------------------------------------------------

    try:
        respuesta_riesgo = requests.post(
            f"{RISK_SERVICE}/predecir",
            json=datos_modelo,
            timeout=15
        )

    except requests.RequestException:
        raise HTTPException(
            status_code=503,
            detail="Risk Service no disponible"
        )


    if respuesta_riesgo.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail="Error al consultar Risk Service"
        )


    riesgo = respuesta_riesgo.json()


    # -----------------------------------------------------
    # RESPUESTA AL FRONTEND
    # -----------------------------------------------------

    return {
        "comuna":
            variables["comuna"],

        "fecha_prediccion":
            variables["fecha_prediccion"],

        "fecha_meteorologia":
            variables["fecha_meteorologia"],

        "nivel_riesgo":
            riesgo["nivel_riesgo"],

        "score_modelo":
            riesgo["score_modelo"],

        "temperatura_media":
            variables["temperatura_media"],

        "humedad_media":
            variables["humedad_media"],

        "viento_medio":
            variables["viento_medio"],

        "vegetacion_cobertura":
            variables["vegetacion_cobertura"],

        "incendios_historicos":
            variables["incendios_historicos"],

        "factores_principales":
            riesgo.get(
                "factores_principales",
                []
            )
    }