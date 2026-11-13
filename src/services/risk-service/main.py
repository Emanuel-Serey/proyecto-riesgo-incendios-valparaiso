from pathlib import Path
from datetime import date
import os

import joblib
import numpy as np
import pandas as pd
import shap

from fastapi import FastAPI, HTTPException
from prometheus_fastapi_instrumentator import Instrumentator
from pydantic import BaseModel
from sqlalchemy import create_engine, text, URL
from sqlalchemy.exc import SQLAlchemyError


# =========================================================
# CONFIGURACION
# =========================================================

BASE_DIR = Path(__file__).resolve().parent

RUTA_MODELO = (
    BASE_DIR
    / "models"
    / "random_forest_incendios.joblib"
)

MODELO_VERSION = os.getenv(
    "MODELO_VERSION",
    "random_forest_v1"
)


if not RUTA_MODELO.exists():
    raise FileNotFoundError(
        f"No existe el modelo: {RUTA_MODELO}"
    )


# Pipeline completo:
# preprocesamiento + Random Forest
modelo = joblib.load(
    RUTA_MODELO
)


# =========================================================
# SHAP
# =========================================================

# El ultimo paso del Pipeline corresponde
# al Random Forest.
clasificador = modelo.steps[-1][1]

# Todo lo anterior corresponde al
# preprocesamiento.
preprocesador = modelo[:-1]

explicador_shap = shap.TreeExplainer(
    clasificador
)


# =========================================================
# POSTGRESQL
# =========================================================

url = URL.create(
    drivername="postgresql+psycopg2",
    username=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    host=os.getenv("DB_HOST"),
    port=int(
        os.getenv(
            "DB_PORT",
            5432
        )
    ),
    database=os.getenv("DB_NAME")
)


engine = create_engine(
    url,
    pool_pre_ping=True
)


# =========================================================
# FASTAPI
# =========================================================

app = FastAPI(
    title="Risk Service - Incendios Forestales",
    version="2.1"
)


Instrumentator().instrument(
    app
).expose(
    app,
    endpoint="/metrics",
    include_in_schema=False
)


# =========================================================
# ENTRADA
# =========================================================

class VariablesRiesgo(BaseModel):
    id_variables: int
    comuna: str
    fecha_prediccion: date

    temperatura_media: float
    humedad_media: float
    viento_medio: float
    vegetacion_cobertura: str
    incendios_historicos: float

class ConsultaRiesgo(BaseModel):
    id_variables: int
    comuna: str
    fecha_prediccion: date
    fecha_meteorologia: date | None = None

    nivel_riesgo: str
    score_modelo: float

    origen: str = "web_publica"

# =========================================================
# CLASIFICACION
# =========================================================

def clasificar_riesgo(
    score: float
):
    if score < 0.35:
        return "Bajo"

    if score < 0.50:
        return "Medio"

    return "Alto"


# =========================================================
# REGISTRO POSTGRESQL
# =========================================================

def registrar_inferencia(
    id_variables: int,
    score: float,
    nivel_riesgo: str
):
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
        ON CONFLICT (
            id_variables,
            modelo_version
        )
        DO UPDATE SET
            score_modelo = EXCLUDED.score_modelo,
            nivel_riesgo = EXCLUDED.nivel_riesgo,
            fecha_inferencia = CURRENT_TIMESTAMP;
    """)

    with engine.begin() as conexion:
        conexion.execute(
            consulta,
            {
                "id_variables":
                    id_variables,

                "score_modelo":
                    score,

                "nivel_riesgo":
                    nivel_riesgo,

                "modelo_version":
                    MODELO_VERSION
            }
        )

def registrar_consulta_riesgo(
    datos: ConsultaRiesgo
):
    consulta = text("""
        INSERT INTO public.consultas_riesgo (
            comuna,
            id_variables,
            fecha_prediccion,
            fecha_meteorologia,
            nivel_riesgo,
            score_modelo,
            origen
        )
        VALUES (
            :comuna,
            :id_variables,
            :fecha_prediccion,
            :fecha_meteorologia,
            :nivel_riesgo,
            :score_modelo,
            :origen
        );
    """)

    with engine.begin() as conexion:

        conexion.execute(
            consulta,
            {
                "comuna":
                    datos.comuna,

                "id_variables":
                    datos.id_variables,

                "fecha_prediccion":
                    datos.fecha_prediccion,

                "fecha_meteorologia":
                    datos.fecha_meteorologia,

                "nivel_riesgo":
                    datos.nivel_riesgo,

                "score_modelo":
                    datos.score_modelo,

                "origen":
                    datos.origen,
            }
        )

# =========================================================
# SHAP
# =========================================================

def obtener_nombre_original(
    nombre_transformado
):
    """
    Convierte nombres del preprocesamiento
    a las 5 variables originales.
    """

    nombre = str(
        nombre_transformado
    )

    if "__" in nombre:
        nombre = nombre.split(
            "__",
            1
        )[1]


    if nombre.startswith(
        "temperatura_media"
    ):
        return "temperatura_media"


    if nombre.startswith(
        "humedad_media"
    ):
        return "humedad_media"


    if nombre.startswith(
        "viento_medio"
    ):
        return "viento_medio"


    if nombre.startswith(
        "vegetacion_cobertura"
    ):
        return "vegetacion_cobertura"


    if nombre.startswith(
        "incendios_historicos"
    ):
        return "incendios_historicos"


    return None


def generar_explicacion(
    entrada: pd.DataFrame
):
    """
    Calcula SHAP para una prediccion y devuelve
    los tres factores con mayor impacto.
    """

    # Aplicamos exactamente el mismo
    # preprocesamiento del Pipeline.
    entrada_transformada = (
        preprocesador.transform(
            entrada
        )
    )


    if hasattr(
        entrada_transformada,
        "toarray"
    ):
        entrada_transformada = (
            entrada_transformada.toarray()
        )


    entrada_transformada = np.asarray(
        entrada_transformada
    )


    # Nombres despues del preprocesamiento.
    nombres = (
        preprocesador
        .get_feature_names_out()
    )


    # Valores SHAP.
    valores_shap = (
        explicador_shap
        .shap_values(
            entrada_transformada,
            check_additivity=False
        )
    )


    valores_shap = np.asarray(
        valores_shap
    )


    # RandomForest binario:
    # SHAP moderno normalmente devuelve
    # (muestras, features, clases).
    if valores_shap.ndim == 3:
        contribuciones = (
            valores_shap[
                0,
                :,
                1
            ]
        )

    # Compatibilidad con salida
    # (muestras, features).
    elif valores_shap.ndim == 2:
        contribuciones = (
            valores_shap[0]
        )

    else:
        raise ValueError(
            "Formato SHAP inesperado: "
            f"{valores_shap.shape}"
        )


    # Agrupamos las columnas generadas
    # por OneHotEncoder en las 5 variables
    # originales.
    impactos = {
        "temperatura_media": 0.0,
        "humedad_media": 0.0,
        "viento_medio": 0.0,
        "vegetacion_cobertura": 0.0,
        "incendios_historicos": 0.0
    }


    for (
        nombre,
        contribucion
    ) in zip(
        nombres,
        contribuciones
    ):
        original = (
            obtener_nombre_original(
                nombre
            )
        )

        if original:
            impactos[
                original
            ] += float(
                contribucion
            )


    nombres_amigables = {
        "temperatura_media":
            "Temperatura",

        "humedad_media":
            "Humedad",

        "viento_medio":
            "Viento",

        "vegetacion_cobertura":
            "Cobertura vegetal",

        "incendios_historicos":
            "Historial de incendios"
    }


    factores = []


    for (
        variable,
        impacto
    ) in impactos.items():

        if impacto > 0:
            direccion = "aumenta"

        elif impacto < 0:
            direccion = "reduce"

        else:
            direccion = "neutral"


        factores.append({
            "variable":
                variable,

            "nombre":
                nombres_amigables[
                    variable
                ],

            "direccion":
                direccion,

            "impacto":
                round(
                    impacto,
                    6
                )
        })


    factores.sort(
        key=lambda x: abs(
            x["impacto"]
        ),
        reverse=True
    )


    return factores[:3]


# =========================================================
# HEALTH
# =========================================================

@app.get("/health")
def health():
    return {
        "status": "ok"
    }


# =========================================================
# ESTADISTICAS DE USO
# =========================================================

@app.get("/estadisticas/uso")
def obtener_estadisticas_uso():

    consulta = text("""
        WITH comuna_top AS (

            SELECT
                comuna,
                COUNT(*) AS total

            FROM public.consultas_riesgo

            GROUP BY comuna

            ORDER BY
                total DESC,
                comuna ASC

            LIMIT 1
        )

        SELECT

            (
                SELECT COUNT(*)
                FROM public.consultas_riesgo
            ) AS consultas_total,

            (
                SELECT COUNT(*)
                FROM public.consultas_riesgo

                WHERE
                    (
                        fecha_consulta
                        AT TIME ZONE 'America/Santiago'
                    )::date
                    =
                    (
                        CURRENT_TIMESTAMP
                        AT TIME ZONE 'America/Santiago'
                    )::date
            ) AS consultas_hoy,

            (
                SELECT COUNT(*)
                FROM public.registro_inferencias
            ) AS inferencias_total,

            (
                SELECT comuna
                FROM comuna_top
            ) AS comuna_mas_consultada,

            (
                SELECT total
                FROM comuna_top
            ) AS comuna_mas_consultada_total;
    """)

    try:

        with engine.connect() as conexion:

            resultado = (
                conexion.execute(
                    consulta
                )
                .mappings()
                .one()
            )


        return {

            "consultas_total":
                int(
                    resultado[
                        "consultas_total"
                    ]
                    or
                    0
                ),

            "consultas_hoy":
                int(
                    resultado[
                        "consultas_hoy"
                    ]
                    or
                    0
                ),

            "inferencias_total":
                int(
                    resultado[
                        "inferencias_total"
                    ]
                    or
                    0
                ),

            "comuna_mas_consultada":
                resultado[
                    "comuna_mas_consultada"
                ],

            "comuna_mas_consultada_total":
                int(
                    resultado[
                        "comuna_mas_consultada_total"
                    ]
                    or
                    0
                ),

        }


    except SQLAlchemyError:

        raise HTTPException(
            status_code=500,
            detail=(
                "Error al obtener "
                "las estadísticas de uso"
            )
        )

# =========================================================
# PREDICCION
# =========================================================

@app.post("/consultas")
def registrar_consulta(
    datos: ConsultaRiesgo
):
    try:

        registrar_consulta_riesgo(
            datos
        )

        return {
            "registrada": True
        }

    except SQLAlchemyError:

        raise HTTPException(
            status_code=500,
            detail=(
                "Error al registrar "
                "la consulta de riesgo"
            )
        )

@app.post("/predecir")
def predecir(
    datos: VariablesRiesgo
):
    try:

        entrada = pd.DataFrame([{
            "temperatura_media":
                datos.temperatura_media,

            "humedad_media":
                datos.humedad_media,

            "viento_medio":
                datos.viento_medio,

            "vegetacion_cobertura":
                datos.vegetacion_cobertura,

            "incendios_historicos":
                datos.incendios_historicos
        }])


        # ---------------------------------------------
        # PREDICCION
        # ---------------------------------------------

        score = float(
            modelo.predict_proba(
                entrada
            )[0, 1]
        )


        nivel_riesgo = (
            clasificar_riesgo(
                score
            )
        )


        # ---------------------------------------------
        # REGISTRO
        # ---------------------------------------------

        registrar_inferencia(
            datos.id_variables,
            score,
            nivel_riesgo
        )


        # ---------------------------------------------
        # EXPLICACION
        # ---------------------------------------------

        try:

            factores_principales = (
                generar_explicacion(
                    entrada
                )
            )

        except Exception as error:

            print(
                "SHAP no pudo generar "
                f"explicacion: {error}"
            )

            factores_principales = []


        # ---------------------------------------------
        # RESPUESTA
        # ---------------------------------------------

        return {
            "id_variables":
                datos.id_variables,

            "comuna":
                datos.comuna,

            "fecha_prediccion":
                datos.fecha_prediccion,

            "score_modelo":
                score,

            "nivel_riesgo":
                nivel_riesgo,

            "modelo_version":
                MODELO_VERSION,

            "factores_principales":
                factores_principales
        }


    except SQLAlchemyError:

        raise HTTPException(
            status_code=500,
            detail=(
                "Error al registrar "
                "la inferencia en PostgreSQL"
            )
        )


    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=(
                "Error durante la inferencia: "
                f"{error}"
            )
        )