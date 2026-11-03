import os

import boto3

from botocore.exceptions import (
    ClientError,
    NoCredentialsError
)

from fastapi import (
    FastAPI,
    HTTPException
)

from pydantic import BaseModel


# =========================================================
# CONFIGURACION
# =========================================================

AWS_REGION = os.getenv(
    "AWS_DEFAULT_REGION",
    "us-east-1"
)

BEDROCK_MODEL_ID = os.getenv(
    "BEDROCK_MODEL_ID",
    "anthropic.claude-3-haiku-20240307-v1:0"
)


# =========================================================
# BEDROCK
# =========================================================

bedrock = boto3.client(
    "bedrock-runtime",
    region_name=AWS_REGION
)


# =========================================================
# FASTAPI
# =========================================================

app = FastAPI(
    title="AI Service - Explicacion de Riesgo",
    version="1.0"
)


# =========================================================
# MODELOS DE ENTRADA
# =========================================================

class FactorShap(BaseModel):
    variable: str
    nombre: str
    direccion: str
    impacto: float


class SolicitudExplicacion(BaseModel):
    comuna: str
    fecha_prediccion: str

    nivel_riesgo: str
    score_modelo: float

    temperatura_media: float
    humedad_media: float
    viento_medio: float
    vegetacion_cobertura: str
    incendios_historicos: float

    factores_principales: list[FactorShap]


# =========================================================
# PROMPT
# =========================================================

def construir_prompt(
    datos: SolicitudExplicacion
) -> str:

    factores = "\n".join(
        (
            f"- {factor.nombre}: "
            f"{factor.direccion} el nivel de riesgo"
        )
        for factor
        in datos.factores_principales
    )


    return f"""
Analiza el resultado de un sistema preventivo de riesgo
de incendios forestales para la Región de Valparaíso.

Comuna:
{datos.comuna}

Fecha evaluada:
{datos.fecha_prediccion}

Nivel de riesgo:
{datos.nivel_riesgo}

Índice del modelo:
{datos.score_modelo:.3f}

Variables utilizadas:

- Temperatura media: {datos.temperatura_media:.1f} °C
- Humedad media: {datos.humedad_media:.1f} %
- Viento medio: {datos.viento_medio:.2f} nudos
- Cobertura vegetal: {datos.vegetacion_cobertura}
- Promedio histórico: {datos.incendios_historicos:.1f} incendios/año

Factores principales obtenidos mediante SHAP:

{factores}

Redacta una explicación preventiva en español
de máximo tres oraciones.

Debes cumplir estas reglas:

1. Explica principalmente usando los factores SHAP.
2. No inventes información que no aparezca en los datos.
3. No afirmes que ocurrirá un incendio.
4. No describas el índice como una probabilidad exacta.
5. Deja claro que se trata de una evaluación preventiva
   de riesgo.
6. Usa lenguaje comprensible para un usuario no técnico.
""".strip()


# =========================================================
# HEALTH
# =========================================================

@app.get("/health")
def health():

    return {
        "status": "ok",
        "provider": "aws-bedrock",
        "model": BEDROCK_MODEL_ID
    }


# =========================================================
# EXPLICACION
# =========================================================

@app.post("/explicar")
def explicar(
    datos: SolicitudExplicacion
):

    prompt = construir_prompt(
        datos
    )


    try:

        respuesta = bedrock.converse(
            modelId=BEDROCK_MODEL_ID,

            system=[
                {
                    "text": (
                        "Eres un asistente especializado "
                        "en comunicar resultados de un "
                        "sistema preventivo de incendios "
                        "forestales. Debes ser preciso, "
                        "prudente y no inventar datos."
                    )
                }
            ],

            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "text": prompt
                        }
                    ]
                }
            ],

            inferenceConfig={
                "maxTokens": 220,
                "temperature": 0.2,
                "topP": 0.9
            }
        )


        explicacion = (
            respuesta[
                "output"
            ][
                "message"
            ][
                "content"
            ][0][
                "text"
            ]
        )


        return {
            "comuna":
                datos.comuna,

            "nivel_riesgo":
                datos.nivel_riesgo,

            "explicacion":
                explicacion.strip(),

            "proveedor":
                "AWS Bedrock",

            "modelo":
                BEDROCK_MODEL_ID
        }


    except NoCredentialsError:

        raise HTTPException(
            status_code=503,
            detail=(
                "No existen credenciales "
                "AWS configuradas"
            )
        )


    except ClientError as error:

        codigo = (
            error.response
            .get(
                "Error",
                {}
            )
            .get(
                "Code",
                "BedrockError"
            )
        )

        raise HTTPException(
            status_code=502,
            detail=(
                "AWS Bedrock no pudo "
                f"procesar la solicitud: {codigo}"
            )
        )


    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=(
                "Error interno en AI Service: "
                f"{type(error).__name__}"
            )
        )