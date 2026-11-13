import hmac
import os

from datetime import (
    datetime,
    timedelta,
    timezone,
)

from pathlib import Path

from urllib.parse import quote

import jwt
import requests

from dotenv import load_dotenv

from fastapi import (
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)

from fastapi.responses import (
    JSONResponse,
    Response,
)

from fastapi.security import (
    OAuth2PasswordBearer,
    OAuth2PasswordRequestForm,
)

from jwt.exceptions import (
    InvalidTokenError,
)

from prometheus_fastapi_instrumentator import (
    Instrumentator,
)

from pwdlib import PasswordHash

from pydantic import BaseModel


# =========================================================
# VARIABLES
# =========================================================

def cargar_variables_entorno():

    archivo_actual = Path(
        __file__
    ).resolve()

    for carpeta in archivo_actual.parents:

        archivo_env = (
            carpeta / ".env"
        )

        if archivo_env.exists():

            load_dotenv(
                archivo_env
            )

            return

    load_dotenv()


cargar_variables_entorno()


DATA_SERVICE = os.getenv(
    "DATA_SERVICE_URL",
    "http://data-service:8001",
)

RISK_SERVICE = os.getenv(
    "RISK_SERVICE_URL",
    "http://risk-service:8002",
)

REPORT_SERVICE = os.getenv(
    "REPORT_SERVICE_URL",
    "http://127.0.0.1:8004",
)

AI_SERVICE = os.getenv(
    "AI_SERVICE_URL",
    "http://ai-service:8003",
)


ADMIN_USERNAME = os.getenv(
    "ADMIN_USERNAME",
    "",
)

ADMIN_PASSWORD_HASH = os.getenv(
    "ADMIN_PASSWORD_HASH",
    "",
)

JWT_SECRET = os.getenv(
    "JWT_SECRET",
    "",
)

ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv(
        "ACCESS_TOKEN_EXPIRE_MINUTES",
        "60",
    )
)

JWT_ALGORITHM = "HS256"


password_hasher = (
    PasswordHash.recommended()
)


oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="auth/token"
)


# =========================================================
# APP
# =========================================================

app = FastAPI(
    title=(
        "API Gateway - "
        "Riesgo de Incendios Forestales"
    ),
    version="2.8",
)


Instrumentator().instrument(
    app
).expose(
    app,
    endpoint="/metrics",
    include_in_schema=False,
)


# =========================================================
# MODELOS AUTH
# =========================================================

class TokenResponse(BaseModel):

    access_token: str

    token_type: str

    expires_in: int


class AdminActual(BaseModel):

    username: str

    role: str


# =========================================================
# AUTH
# =========================================================

def verificar_configuracion_auth():

    if (
        not ADMIN_USERNAME
        or
        not ADMIN_PASSWORD_HASH
        or
        not JWT_SECRET
    ):

        raise HTTPException(
            status_code=503,
            detail=(
                "La autenticación administrativa "
                "no está configurada correctamente"
            ),
        )


def verificar_password(
    password: str,
) -> bool:

    try:

        return password_hasher.verify(
            password,
            ADMIN_PASSWORD_HASH,
        )

    except Exception:

        return False


def autenticar_admin(
    username: str,
    password: str,
) -> bool:

    verificar_configuracion_auth()


    return (

        hmac.compare_digest(
            username,
            ADMIN_USERNAME,
        )

        and

        verificar_password(
            password
        )

    )


def crear_access_token(
    username: str,
) -> str:

    ahora = datetime.now(
        timezone.utc
    )


    expiracion = (
        ahora
        +
        timedelta(
            minutes=
                ACCESS_TOKEN_EXPIRE_MINUTES
        )
    )


    payload = {

        "sub":
            username,

        "role":
            "admin",

        "iat":
            ahora,

        "exp":
            expiracion,

    }


    return jwt.encode(
        payload,
        JWT_SECRET,
        algorithm=
            JWT_ALGORITHM,
    )


def obtener_admin_actual(

    token: str = Depends(
        oauth2_scheme
    ),

) -> AdminActual:

    verificar_configuracion_auth()


    excepcion = HTTPException(
        status_code=
            status.HTTP_401_UNAUTHORIZED,

        detail=
            "Token inválido o expirado",

        headers={
            "WWW-Authenticate":
                "Bearer"
        },
    )


    try:

        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[
                JWT_ALGORITHM
            ],
        )


        username = payload.get(
            "sub"
        )


        role = payload.get(
            "role"
        )


        if (
            username is None
            or
            role !=
            "admin"
        ):

            raise excepcion


        if not hmac.compare_digest(
            username,
            ADMIN_USERNAME,
        ):

            raise excepcion


    except InvalidTokenError:

        raise excepcion


    return AdminActual(
        username=
            username,

        role=
            role,
    )


# =========================================================
# LOGIN
# =========================================================

@app.post(
    "/auth/token",
    response_model=
        TokenResponse,
)
def login_admin(

    form_data:
        OAuth2PasswordRequestForm
        =
        Depends(),

):

    if not autenticar_admin(
        form_data.username,
        form_data.password,
    ):

        raise HTTPException(
            status_code=
                status.HTTP_401_UNAUTHORIZED,

            detail=
                "Usuario o contraseña incorrectos",

            headers={
                "WWW-Authenticate":
                    "Bearer"
            },
        )


    token = crear_access_token(
        form_data.username
    )


    return {

        "access_token":
            token,

        "token_type":
            "bearer",

        "expires_in":
            ACCESS_TOKEN_EXPIRE_MINUTES
            *
            60,

    }


@app.get(
    "/auth/me",
    response_model=
        AdminActual,
)
def auth_me(

    admin: AdminActual = Depends(
        obtener_admin_actual
    ),

):

    return admin


# =========================================================
# HEALTH
# =========================================================

@app.get("/health")
def health():

    return {
        "status":
            "ok"
    }


def consultar_health(
    url: str,
    timeout: int = 4,
):

    try:

        respuesta = requests.get(
            url,
            timeout=
                timeout,
        )


        if (
            respuesta.status_code
            !=
            200
        ):

            return {
                "status":
                    "unavailable"
            }


        datos = respuesta.json()


        return {

            "status":
                (
                    "ok"

                    if
                    datos.get(
                        "status"
                    )
                    ==
                    "ok"

                    else
                    "unavailable"
                ),

            "data":
                datos,

        }


    except (
        requests.RequestException,
        ValueError,
    ):

        return {
            "status":
                "unavailable"
        }


@app.get("/health/system")
def health_system():

    data_estado = consultar_health(
        f"{DATA_SERVICE}/health"
    )


    risk_estado = consultar_health(
        f"{RISK_SERVICE}/health"
    )


    operativo = (

        data_estado[
            "status"
        ] == "ok"

        and

        risk_estado[
            "status"
        ] == "ok"

    )


    return {

        "status":
            (
                "ok"

                if
                operativo

                else
                "degraded"
            ),

        "services": {

            "data_service":
                data_estado[
                    "status"
                ],

            "risk_service":
                risk_estado[
                    "status"
                ],

        },

    }


# =========================================================
# ESTADO DEL SISTEMA - ADMIN
# =========================================================

@app.get(
    "/admin/system/status"
)
def admin_system_status(

    admin: AdminActual = Depends(
        obtener_admin_actual
    ),

):

    data_estado = consultar_health(
        f"{DATA_SERVICE}/health"
    )


    risk_estado = consultar_health(
        f"{RISK_SERVICE}/health"
    )


    report_estado = consultar_health(
        f"{REPORT_SERVICE}/health"
    )


    report_db_estado = consultar_health(
        f"{REPORT_SERVICE}/db-health"
    )


    yolo_estado = consultar_health(
        f"{REPORT_SERVICE}/model-health",
        timeout=30,
    )


    servicios = {

        "api_gateway": {

            "name":
                "API Gateway",

            "description":
                "Punto de entrada principal del sistema",

            "status":
                "ok",

        },

        "data_service": {

            "name":
                "Servicio de datos",

            "description":
                "Variables meteorológicas y datos de entrada",

            "status":
                data_estado[
                    "status"
                ],

        },

        "risk_service": {

            "name":
                "Servicio de riesgo",

            "description":
                "Inferencia preventiva y explicabilidad",

            "status":
                risk_estado[
                    "status"
                ],

        },

        "report_service": {

            "name":
                "Servicio de reportes",

            "description":
                "Gestión de reportes ciudadanos",

            "status":
                report_estado[
                    "status"
                ],

        },

        "report_database": {

            "name":
                "Base de datos de reportes",

            "description":
                "PostgreSQL / PostGIS",

            "status":
                report_db_estado[
                    "status"
                ],

        },

    }


    modelos = {

        "risk_model": {

            "name":
                "Modelo de riesgo preventivo",

            "technology":
                "Random Forest",

            "description":
                "Predicción de riesgo de incendio por comuna",

            "status":
                risk_estado[
                    "status"
                ],

        },

        "fire_smoke_detector": {

            "name":
                "Detector de fuego y humo",

            "technology":
                "YOLOv8",

            "description":
                "Análisis de imágenes de reportes ciudadanos",

            "status":
                yolo_estado[
                    "status"
                ],

        },

    }


    estados = [

        item[
            "status"
        ]

        for item
        in servicios.values()

    ] + [

        item[
            "status"
        ]

        for item
        in modelos.values()

    ]


    estado_general = (

        "ok"

        if all(
            estado ==
            "ok"

            for estado
            in estados
        )

        else
        "degraded"

    )


    return {

        "status":
            estado_general,

        "checked_at":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "services":
            servicios,

        "models":
            modelos,

    }


# =========================================================
# RIESGO
# =========================================================


def calcular_riesgo_comuna(
    comuna: str,
    registrar_consulta: bool = False,
):

    comuna_url = quote(
        comuna,
        safe="",
    )


    try:

        respuesta_datos = requests.get(
            f"{DATA_SERVICE}/variables/{comuna_url}",
            timeout=10,
        )


    except requests.RequestException:

        raise HTTPException(
            status_code=503,
            detail=(
                "Data Service no disponible"
            ),
        )


    if (
        respuesta_datos.status_code
        ==
        404
    ):

        raise HTTPException(
            status_code=404,
            detail=(
                "Comuna no encontrada"
            ),
        )


    if (
        respuesta_datos.status_code
        !=
        200
    ):

        raise HTTPException(
            status_code=502,
            detail=(
                "Error al consultar "
                "Data Service"
            ),
        )


    variables = (
        respuesta_datos.json()
    )


    datos_modelo = {

        "id_variables":
            variables[
                "id_variables"
            ],

        "comuna":
            variables[
                "comuna"
            ],

        "fecha_prediccion":
            variables[
                "fecha_prediccion"
            ],

        "temperatura_media":
            variables[
                "temperatura_media"
            ],

        "humedad_media":
            variables[
                "humedad_media"
            ],

        "viento_medio":
            variables[
                "viento_medio"
            ],

        "vegetacion_cobertura":
            variables[
                "vegetacion_cobertura"
            ],

        "incendios_historicos":
            variables[
                "incendios_historicos"
            ],

    }


    try:

        respuesta_riesgo = requests.post(
            f"{RISK_SERVICE}/predecir",

            json=
                datos_modelo,

            timeout=
                15,
        )


    except requests.RequestException:

        raise HTTPException(
            status_code=503,
            detail=(
                "Risk Service no disponible"
            ),
        )


    if (
        respuesta_riesgo.status_code
        !=
        200
    ):

        raise HTTPException(
            status_code=502,
            detail=(
                "Error al consultar "
                "Risk Service"
            ),
        )


    riesgo = (
        respuesta_riesgo.json()
    )

    datos_consulta = {

        "id_variables":
            variables[
                "id_variables"
            ],

        "comuna":
            variables[
                "comuna"
            ],

        "fecha_prediccion":
            variables[
                "fecha_prediccion"
            ],

        "fecha_meteorologia":
            variables.get(
                "fecha_meteorologia"
            ),

        "nivel_riesgo":
            riesgo[
                "nivel_riesgo"
            ],

        "score_modelo":
            riesgo[
                "score_modelo"
            ],

        "origen":
            "web_publica",

    }

    if registrar_consulta:

        try:

            respuesta_consulta = requests.post(

                f"{RISK_SERVICE}/consultas",

                json=
                    datos_consulta,

                timeout=
                    10,

            )


            if (
                respuesta_consulta.status_code
                !=
                200
            ):

                print(
                    "No fue posible registrar "
                    "la consulta de riesgo: "
                    f"{respuesta_consulta.text}"
                )


        except requests.RequestException as error:

            print(
                "No fue posible registrar "
                "la consulta de riesgo: "
                f"{error}"
            )    


    return {

        "comuna":
            variables[
                "comuna"
            ],

        "fecha_prediccion":
            variables[
                "fecha_prediccion"
            ],

        "fecha_meteorologia":
            variables[
                "fecha_meteorologia"
            ],

        "nivel_riesgo":
            riesgo[
                "nivel_riesgo"
            ],

        "score_modelo":
            riesgo[
                "score_modelo"
            ],

        "temperatura_media":
            variables[
                "temperatura_media"
            ],

        "humedad_media":
            variables[
                "humedad_media"
            ],

        "viento_medio":
            variables[
                "viento_medio"
            ],

        "vegetacion_cobertura":
            variables[
                "vegetacion_cobertura"
            ],

        "incendios_historicos":
            variables[
                "incendios_historicos"
            ],

        "factores_principales":
            riesgo.get(
                "factores_principales",
                [],
            ),

    }

@app.get("/riesgo/{comuna}")
def obtener_riesgo(
    comuna: str,
):

    return calcular_riesgo_comuna(
        comuna,
        registrar_consulta=True,
    )

# =========================================================
# RIESGO + EXPLICACION PARA EL USUARIO
# =========================================================

@app.get(
    "/riesgo/{comuna}/explicado"
)
def obtener_riesgo_explicado(
    comuna: str,
):

    # -----------------------------------------------------
    # OBTENER RESULTADO REAL DEL SISTEMA
    # -----------------------------------------------------

    resultado = calcular_riesgo_comuna(
        comuna,
        registrar_consulta=False,
    )


    # -----------------------------------------------------
    # PREPARAR DATOS PARA AI SERVICE
    # -----------------------------------------------------

    datos_explicacion = {

        "comuna":
            resultado[
                "comuna"
            ],

        "fecha_prediccion":
            resultado[
                "fecha_prediccion"
            ],

        "nivel_riesgo":
            resultado[
                "nivel_riesgo"
            ],

        "score_modelo":
            resultado[
                "score_modelo"
            ],

        "temperatura_media":
            resultado[
                "temperatura_media"
            ],

        "humedad_media":
            resultado[
                "humedad_media"
            ],

        "viento_medio":
            resultado[
                "viento_medio"
            ],

        "vegetacion_cobertura":
            resultado[
                "vegetacion_cobertura"
            ],

        "incendios_historicos":
            resultado[
                "incendios_historicos"
            ],

        "factores_principales":
            resultado.get(
                "factores_principales",
                [],
            ),

    }


    # -----------------------------------------------------
    # CONSULTAR GEMINI
    # -----------------------------------------------------

    try:

        respuesta_ai = requests.post(

            f"{AI_SERVICE}/explicar",

            json=
                datos_explicacion,

            timeout=
                35,
        )


    except requests.RequestException:

        # La IA es complementaria.
        # El resultado preventivo debe seguir funcionando.

        return {

            **resultado,

            "explicacion":
                None,

            "explicacion_disponible":
                False,

        }


    # -----------------------------------------------------
    # SI GEMINI FALLA
    # -----------------------------------------------------

    if (
        respuesta_ai.status_code
        !=
        200
    ):

        return {

            **resultado,

            "explicacion":
                None,

            "explicacion_disponible":
                False,

        }


    # -----------------------------------------------------
    # RESPUESTA DE GEMINI
    # -----------------------------------------------------

    try:

        datos_ai = (
            respuesta_ai.json()
        )

    except ValueError:

        return {

            **resultado,

            "explicacion":
                None,

            "explicacion_disponible":
                False,

        }


    explicacion = (
        datos_ai.get(
            "explicacion"
        )
    )


    # -----------------------------------------------------
    # RESPUESTA FINAL
    # -----------------------------------------------------

    return {

        **resultado,

        "explicacion":
            explicacion,

        "explicacion_disponible":
            bool(
                explicacion
            ),

    }


# =========================================================
# CREAR REPORTE
# =========================================================

@app.post("/reportes")
async def crear_reporte_ciudadano(

    latitud: float = Form(...),

    longitud: float = Form(...),

    descripcion: str | None = Form(
        None
    ),

    precision_gps_m: float | None = Form(
        None
    ),

    imagen: UploadFile = File(...),

):

    try:

        contenido_imagen = (
            await imagen.read()
        )


        datos = {

            "latitud":
                str(
                    latitud
                ),

            "longitud":
                str(
                    longitud
                ),

        }


        if descripcion:

            datos[
                "descripcion"
            ] = descripcion


        if (
            precision_gps_m
            is not None
        ):

            datos[
                "precision_gps_m"
            ] = str(
                precision_gps_m
            )


        archivos = {

            "imagen": (
                imagen.filename,
                contenido_imagen,
                imagen.content_type,
            )

        }


        respuesta = requests.post(
            f"{REPORT_SERVICE}/reportes",

            data=
                datos,

            files=
                archivos,

            timeout=
                90,
        )


    except requests.RequestException:

        raise HTTPException(
            status_code=503,
            detail=(
                "Report Service no disponible"
            ),
        )


    try:

        contenido = (
            respuesta.json()
        )


    except ValueError:

        raise HTTPException(
            status_code=502,
            detail=(
                "Respuesta inválida "
                "de Report Service"
            ),
        )


    return JSONResponse(

        status_code=
            respuesta.status_code,

        content=
            contenido,

    )


# =========================================================
# CONFIRMADOS PÚBLICOS
# =========================================================

@app.get(
    "/reportes/confirmados"
)
def obtener_reportes_confirmados():

    try:

        respuesta = requests.get(

            f"{REPORT_SERVICE}"
            "/reportes/estado/"
            "confirmados",

            timeout=10,
        )


    except requests.RequestException:

        raise HTTPException(
            status_code=503,
            detail=(
                "Report Service no disponible"
            ),
        )


    if (
        respuesta.status_code
        !=
        200
    ):

        raise HTTPException(
            status_code=502,
            detail=(
                "Error al consultar "
                "Report Service"
            ),
        )


    return respuesta.json()


# =========================================================
# IMÁGENES
# =========================================================

@app.get(
    "/imagenes-reportes/"
    "{nombre_archivo}"
)
def obtener_imagen_reporte(
    nombre_archivo: str,
):

    try:

        respuesta = requests.get(

            f"{REPORT_SERVICE}"
            "/imagenes-reportes/"
            f"{nombre_archivo}",

            timeout=10,
        )


    except requests.RequestException:

        raise HTTPException(
            status_code=503,
            detail=(
                "Report Service no disponible"
            ),
        )


    if (
        respuesta.status_code
        ==
        404
    ):

        raise HTTPException(
            status_code=404,
            detail=(
                "Imagen no encontrada"
            ),
        )


    if (
        respuesta.status_code
        !=
        200
    ):

        raise HTTPException(
            status_code=502,
            detail=(
                "Error al obtener imagen"
            ),
        )


    return Response(

        content=
            respuesta.content,

        media_type=
            respuesta.headers.get(
                "content-type",
                "image/jpeg",
            ),

    )


# =========================================================
# ADMIN PENDIENTES
# =========================================================

@app.get(
    "/reportes/pendientes"
)
def obtener_reportes_pendientes(

    admin: AdminActual = Depends(
        obtener_admin_actual
    ),

):

    try:

        respuesta = requests.get(

            f"{REPORT_SERVICE}"
            "/reportes/estado/"
            "pendientes",

            timeout=10,
        )


    except requests.RequestException:

        raise HTTPException(
            status_code=503,
            detail=(
                "Report Service no disponible"
            ),
        )


    if (
        respuesta.status_code
        !=
        200
    ):

        raise HTTPException(
            status_code=502,
            detail=(
                "Error al consultar "
                "reportes pendientes"
            ),
        )


    return respuesta.json()


# =========================================================
# ADMIN ACTIVOS
# =========================================================

@app.get(
    "/admin/reportes/confirmados"
)
def obtener_reportes_activos_admin(

    admin: AdminActual = Depends(
        obtener_admin_actual
    ),

):

    try:

        respuesta = requests.get(

            f"{REPORT_SERVICE}"
            "/reportes/estado/"
            "confirmados",

            timeout=10,
        )


    except requests.RequestException:

        raise HTTPException(
            status_code=503,
            detail=(
                "Report Service no disponible"
            ),
        )


    if (
        respuesta.status_code
        !=
        200
    ):

        raise HTTPException(
            status_code=502,
            detail=(
                "Error al consultar "
                "reportes activos"
            ),
        )


    return respuesta.json()


# =========================================================
# ADMIN HISTORIAL
# =========================================================

@app.get(
    "/admin/reportes/historial"
)
def obtener_historial_reportes(

    admin: AdminActual = Depends(
        obtener_admin_actual
    ),

):

    try:

        respuesta = requests.get(
            f"{REPORT_SERVICE}/reportes",
            timeout=10,
        )


    except requests.RequestException:

        raise HTTPException(
            status_code=503,
            detail=(
                "Report Service no disponible"
            ),
        )


    if (
        respuesta.status_code
        !=
        200
    ):

        raise HTTPException(
            status_code=502,
            detail=(
                "Error al consultar "
                "el historial"
            ),
        )


    reportes = (
        respuesta.json()
    )


    historial = [

        reporte

        for reporte
        in reportes

        if reporte.get(
            "estado"
        ) in {
            "resuelto",
            "rechazado",
        }

    ]


    historial.sort(

        key=lambda reporte:
            (
                reporte.get(
                    "fecha_resolucion"
                )
                or
                reporte.get(
                    "fecha_reporte"
                )
                or
                ""
            ),

        reverse=True,

    )


    return historial


# =========================================================
# CONFIRMAR
# =========================================================

@app.patch(
    "/reportes/"
    "{id_reporte}/confirmar"
)
def confirmar_reporte(

    id_reporte: int,

    admin: AdminActual = Depends(
        obtener_admin_actual
    ),

):

    try:

        respuesta = requests.patch(

            f"{REPORT_SERVICE}"
            "/reportes/"
            f"{id_reporte}"
            "/confirmar",

            timeout=10,
        )


    except requests.RequestException:

        raise HTTPException(
            status_code=503,
            detail=(
                "Report Service no disponible"
            ),
        )


    return JSONResponse(
        status_code=
            respuesta.status_code,
        content=
            respuesta.json(),
    )


# =========================================================
# RECHAZAR
# =========================================================

@app.patch(
    "/reportes/"
    "{id_reporte}/rechazar"
)
def rechazar_reporte(

    id_reporte: int,

    admin: AdminActual = Depends(
        obtener_admin_actual
    ),

):

    try:

        respuesta = requests.patch(

            f"{REPORT_SERVICE}"
            "/reportes/"
            f"{id_reporte}"
            "/rechazar",

            timeout=10,
        )


    except requests.RequestException:

        raise HTTPException(
            status_code=503,
            detail=(
                "Report Service no disponible"
            ),
        )


    return JSONResponse(
        status_code=
            respuesta.status_code,
        content=
            respuesta.json(),
    )


# =========================================================
# RESOLVER
# =========================================================

@app.patch(
    "/reportes/"
    "{id_reporte}/resolver"
)
def resolver_reporte(

    id_reporte: int,

    admin: AdminActual = Depends(
        obtener_admin_actual
    ),

):

    try:

        respuesta = requests.patch(

            f"{REPORT_SERVICE}"
            "/reportes/"
            f"{id_reporte}"
            "/resolver",

            timeout=10,
        )


    except requests.RequestException:

        raise HTTPException(
            status_code=503,
            detail=(
                "Report Service no disponible"
            ),
        )


    return JSONResponse(
        status_code=
            respuesta.status_code,
        content=
            respuesta.json(),
    )