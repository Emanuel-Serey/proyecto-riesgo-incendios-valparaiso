import asyncio
import os

from dotenv import load_dotenv

from fastapi import (
    FastAPI,
    HTTPException
)

from pydantic import BaseModel

from google import genai

from google.genai import (
    errors,
    types
)


# =========================================================
# VARIABLES DE ENTORNO
# =========================================================

load_dotenv()


GEMINI_API_KEY = os.getenv(
    "GEMINI_API_KEY"
)

GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.5-flash-lite"
)


# =========================================================
# GEMINI
# =========================================================

gemini = (
    genai.Client(
        api_key=GEMINI_API_KEY
    )
    if GEMINI_API_KEY
    else None
)


# =========================================================
# FASTAPI
# =========================================================

app = FastAPI(
    title="AI Service - Explicacion de Riesgo",
    version="2.2"
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


    # =====================================================
    # ENFOQUE SEGÚN NIVEL DE RIESGO
    # =====================================================

    nivel = datos.nivel_riesgo.strip().lower()


    if nivel == "alto":

        enfoque = """
El nivel de riesgo es ALTO.

Explica principalmente cuáles son las condiciones que
están contribuyendo a aumentar el riesgo.

Utiliza un tono preventivo y prudente, sin alarmar
al usuario.

La última oración debe indicar que esta información
corresponde a una evaluación preventiva y que el nivel
de riesgo alto no significa que necesariamente ocurrirá
un incendio.
""".strip()


    elif nivel == "medio":

        enfoque = """
El nivel de riesgo es MEDIO.

Explica de manera equilibrada cuáles son las condiciones
que están aumentando el riesgo y cuáles pueden estar
ayudando a moderarlo.

No presentes la situación como una emergencia ni como
una condición de peligro inmediato.

La última oración debe indicar que esta información
corresponde a una evaluación preventiva y que el nivel
de riesgo medio no significa que necesariamente ocurrirá
un incendio.
""".strip()


    else:

        enfoque = """
El nivel de riesgo es BAJO.

Explica principalmente qué condiciones están ayudando
a mantener un nivel de riesgo bajo.

No digas que no existe riesgo ni que es imposible que
ocurra un incendio.

Utiliza un tono tranquilo, informativo y preventivo.

La última oración debe indicar que esta información
corresponde a una evaluación preventiva y que un nivel
de riesgo bajo no significa que el riesgo de incendio
sea inexistente.
""".strip()


    # =====================================================
    # PROMPT
    # =====================================================

    return f"""
Debes explicar a una persona común por qué una comuna
presenta determinado nivel preventivo de riesgo de
incendio forestal.

La persona que leerá la respuesta NO tiene conocimientos
de inteligencia artificial, estadística ni ciencia de datos.

Utiliza solamente la siguiente información:

Comuna:
{datos.comuna}

Fecha:
{datos.fecha_prediccion}

Nivel de riesgo:
{datos.nivel_riesgo}

Condiciones observadas:

- Temperatura media: {datos.temperatura_media:.1f} °C
- Humedad media: {datos.humedad_media:.1f} %
- Viento medio: {datos.viento_medio:.2f} nudos
- Cobertura vegetal: {datos.vegetacion_cobertura}
- Historial de incendios de la zona:
  {datos.incendios_historicos:.1f} incendios/año

Condiciones que tuvieron mayor influencia en el resultado:

{factores}


ENFOQUE QUE DEBES UTILIZAR PARA ESTA RESPUESTA:

{enfoque}


REGLAS OBLIGATORIAS:

1. Escribe en español claro y cotidiano.

2. Explica directamente qué condiciones están influyendo
   en el nivel de riesgo.

3. No menciones bajo ninguna circunstancia:
   - modelos
   - Random Forest
   - SHAP
   - inteligencia artificial
   - algoritmos
   - machine learning
   - scores
   - índices
   - variables
   - predicciones del modelo
   - factores técnicos

4. No digas frases como:
   "el modelo determinó",
   "el algoritmo considera",
   "la predicción indica",
   "el índice muestra"
   ni expresiones similares.

5. No inventes causas ni condiciones que no estén
   presentes en la información entregada.

6. No afirmes que ocurrirá un incendio.

7. No presentes el nivel de riesgo como una certeza
   de que ocurrirá o no ocurrirá un incendio.

8. La explicación debe tener un máximo de tres oraciones.

9. Prioriza las condiciones que aparecen como las de
   mayor influencia, pero puedes utilizar el resto de
   la información si ayuda a explicar el resultado.

10. No incluyas en la respuesta final valores numéricos
    exactos de temperatura, humedad, viento, historial
    de incendios ni ningún indicador interno.

    Utiliza esos valores únicamente para comprender
    las condiciones y exprésalos en lenguaje natural,
    por ejemplo:
    "temperaturas elevadas",
    "mayor humedad",
    "presencia de viento"
    o "antecedentes de incendios en la zona".

11. Prefiere expresiones naturales como:
    "temperaturas elevadas",
    "baja humedad",
    "presencia de viento",
    "abundante vegetación"
    y "antecedentes de incendios en la zona".

12. No utilices las palabras "probabilidad",
    "porcentaje de probabilidad" ni expresiones que puedan
    hacer pensar que se está calculando la posibilidad
    exacta de que ocurra un incendio.

13. Evita lenguaje alarmista o categórico como:
    "peligro considerable",
    "situación peligrosa",
    "alto peligro",
    "impulsa considerablemente"
    o expresiones similares.

14. Utiliza expresiones prudentes como:
    "puede favorecer",
    "contribuye al nivel de riesgo",
    "puede influir"
    o "es una de las condiciones consideradas".

15. No califiques una condición como "frecuente",
    "extrema", "muy alta", "muy baja", "crítica"
    o similar a menos que esa clasificación venga
    explícitamente indicada en los datos recibidos.


ESTILO DE REFERENCIA PARA RIESGO ALTO:

"Quilpué presenta un nivel de riesgo alto principalmente
por las temperaturas elevadas, la baja humedad y la
presencia de viento, condiciones que pueden favorecer
la propagación del fuego. La abundante vegetación y los
antecedentes de incendios en la zona también contribuyen
a este nivel de riesgo. Esta información corresponde a
una evaluación preventiva y no significa que
necesariamente ocurrirá un incendio."

No copies el ejemplo literalmente.
Adapta siempre la explicación a los datos recibidos
y al nivel de riesgo correspondiente.
""".strip()


# =========================================================
# HEALTH
# =========================================================

@app.get("/health")
def health():

    return {
        "status":
            "ok"
            if gemini
            else "degraded",

        "provider":
            "google-gemini",

        "model":
            GEMINI_MODEL,

        "api_key_configured":
            bool(
                GEMINI_API_KEY
            )
    }


# =========================================================
# EXPLICACION
# =========================================================

@app.post("/explicar")
async def explicar(
    datos: SolicitudExplicacion
):

    if gemini is None:

        raise HTTPException(
            status_code=503,
            detail=(
                "Gemini no está configurado. "
                "Falta la variable "
                "GEMINI_API_KEY."
            )
        )


    prompt = construir_prompt(
        datos
    )


    try:

        llamada_gemini = (
            gemini
            .aio
            .models
            .generate_content(
                model=GEMINI_MODEL,

                contents=prompt,

                config=types.GenerateContentConfig(

                    system_instruction=(
                        "Eres un asistente de orientación "
                        "preventiva sobre incendios forestales. "
                        "Tu función es traducir información "
                        "técnica interna del sistema a lenguaje "
                        "simple para cualquier ciudadano. "
                        "Nunca debes mencionar modelos, "
                        "algoritmos, inteligencia artificial, "
                        "SHAP, Random Forest, scores, índices "
                        "ni otros conceptos técnicos. "
                        "Habla únicamente de las condiciones "
                        "que influyen en el nivel de riesgo."
                    ),

                    temperature=0.2,

                    top_p=0.9,

                    max_output_tokens=220
                )
            )
        )


        respuesta = await asyncio.wait_for(
            llamada_gemini,
            timeout=30
        )


        explicacion = (
            respuesta.text
            or ""
        ).strip()


        if not explicacion:

            raise HTTPException(
                status_code=502,
                detail=(
                    "Gemini respondió sin "
                    "contenido de texto."
                )
            )


        return {
            "comuna":
                datos.comuna,

            "nivel_riesgo":
                datos.nivel_riesgo,

            "explicacion":
                explicacion,

            "proveedor":
                "Google Gemini",

            "modelo":
                GEMINI_MODEL
        }


    except asyncio.TimeoutError:

        raise HTTPException(
            status_code=504,
            detail=(
                "Gemini tardó más de "
                "30 segundos en responder."
            )
        )


    except HTTPException:

        raise


    except errors.APIError as error:

        codigo = getattr(
            error,
            "code",
            None
        )


        if codigo == 429:

            raise HTTPException(
                status_code=429,
                detail=(
                    "Se alcanzó temporalmente "
                    "el límite de uso de Gemini."
                )
            )


        if codigo in (
            401,
            403
        ):

            raise HTTPException(
                status_code=502,
                detail=(
                    "Gemini rechazó las credenciales "
                    "o el acceso al modelo."
                )
            )


        if codigo == 404:

            raise HTTPException(
                status_code=502,
                detail=(
                    f"El modelo {GEMINI_MODEL} "
                    "no está disponible para "
                    "esta cuenta."
                )
            )


        if codigo == 503:

            raise HTTPException(
                status_code=503,
                detail=(
                    "Gemini está temporalmente "
                    "saturado o sin capacidad "
                    "disponible."
                )
            )


        raise HTTPException(
            status_code=502,
            detail=(
                "Google Gemini no pudo "
                "procesar la solicitud. "
                f"Código: {codigo}"
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