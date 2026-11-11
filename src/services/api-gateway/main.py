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
# VARIABLES DE ENTORNO
# =========================================================

def cargar_variables_entorno():
    """
    Busca el archivo .env recorriendo las carpetas
    superiores desde este archivo.

    Esto permite ejecutar el API Gateway desde su
    propia carpeta y seguir utilizando el .env
    ubicado en la raíz del proyecto.
    """

    archivo_actual = Path(
        __file__
    ).resolve()

    for carpeta in archivo_actual.parents:
        archivo_env = carpeta / ".env"

        if archivo_env.exists():
            load_dotenv(
                archivo_env
            )

            return

    load_dotenv()


cargar_variables_entorno()


# =========================================================
# SERVICIOS
# =========================================================

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


# =========================================================
# CONFIGURACIÓN DE AUTENTICACIÓN
# =========================================================

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
    version="2.5",
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
# UTILIDADES DE AUTENTICACIÓN
# =========================================================

def verificar_configuracion_auth():
    """
    Comprueba que las variables necesarias para
    autenticación estén configuradas.
    """

    if (
        not ADMIN_USERNAME
        or not ADMIN_PASSWORD_HASH
        or not JWT_SECRET
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
    """
    Verifica la contraseña recibida contra
    el hash Argon2 guardado en .env.
    """

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
    """
    Comprueba usuario y contraseña.
    """

    verificar_configuracion_auth()

    usuario_correcto = (
        hmac.compare_digest(
            username,
            ADMIN_USERNAME,
        )
    )

    password_correcto = (
        verificar_password(
            password
        )
    )

    return (
        usuario_correcto
        and password_correcto
    )


def crear_access_token(
    username: str,
) -> str:
    """
    Genera JWT para el administrador.
    """

    ahora = datetime.now(
        timezone.utc
    )

    expiracion = (
        ahora
        + timedelta(
            minutes=(
                ACCESS_TOKEN_EXPIRE_MINUTES
            )
        )
    )

    payload = {
        "sub": username,
        "role": "admin",
        "iat": ahora,
        "exp": expiracion,
    }

    token = jwt.encode(
        payload,
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )

    return token


def obtener_admin_actual(
    token: str = Depends(
        oauth2_scheme
    ),
) -> AdminActual:
    """
    Valida el Bearer JWT enviado por el frontend.
    """

    verificar_configuracion_auth()

    excepcion_credenciales = (
        HTTPException(
            status_code=(
                status.HTTP_401_UNAUTHORIZED
            ),
            detail=(
                "Token inválido o expirado"
            ),
            headers={
                "WWW-Authenticate":
                    "Bearer"
            },
        )
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
            or role != "admin"
        ):
            raise excepcion_credenciales

        if not hmac.compare_digest(
            username,
            ADMIN_USERNAME,
        ):
            raise excepcion_credenciales

    except InvalidTokenError:
        raise excepcion_credenciales

    return AdminActual(
        username=username,
        role=role,
    )


# =========================================================
# AUTH - LOGIN
# =========================================================

@app.post(
    "/auth/token",
    response_model=TokenResponse,
)
def login_admin(
    form_data: OAuth2PasswordRequestForm = Depends(),
):
    """
    Login OAuth2.

    Recibe username/password y devuelve un JWT.
    """

    autenticado = autenticar_admin(
        form_data.username,
        form_data.password,
    )

    if not autenticado:
        raise HTTPException(
            status_code=(
                status.HTTP_401_UNAUTHORIZED
            ),
            detail=(
                "Usuario o contraseña incorrectos"
            ),
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
            ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


# =========================================================
# AUTH - USUARIO ACTUAL
# =========================================================

@app.get(
    "/auth/me",
    response_model=AdminActual,
)
def auth_me(
    admin: AdminActual = Depends(
        obtener_admin_actual
    ),
):
    """
    Permite al frontend verificar si el JWT
    todavía es válido.
    """

    return admin


# =========================================================
# HEALTH DEL API GATEWAY
# =========================================================

@app.get("/health")
def health():

    return {
        "status": "ok"
    }


# =========================================================
# ESTADO GENERAL DEL SISTEMA
# =========================================================

@app.get("/health/system")
def health_system():

    servicios = {

        "data_service": {
            "url":
                DATA_SERVICE,

            "status":
                "unavailable",
        },

        "risk_service": {
            "url":
                RISK_SERVICE,

            "status":
                "unavailable",
        },

    }


    # -----------------------------------------------------
    # DATA SERVICE
    # -----------------------------------------------------

    try:
        respuesta = requests.get(
            f"{DATA_SERVICE}/health",
            timeout=3,
        )

        if (
            respuesta.status_code
            == 200
        ):
            datos = respuesta.json()

            if (
                datos.get("status")
                == "ok"
            ):
                servicios[
                    "data_service"
                ]["status"] = "ok"

    except requests.RequestException:
        pass


    # -----------------------------------------------------
    # RISK SERVICE
    # -----------------------------------------------------

    try:
        respuesta = requests.get(
            f"{RISK_SERVICE}/health",
            timeout=3,
        )

        if (
            respuesta.status_code
            == 200
        ):
            datos = respuesta.json()

            if (
                datos.get("status")
                == "ok"
            ):
                servicios[
                    "risk_service"
                ]["status"] = "ok"

    except requests.RequestException:
        pass


    sistema_operativo = all(
        servicio["status"] == "ok"
        for servicio
        in servicios.values()
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
                ]["status"],

        },

    }


# =========================================================
# CONSULTA DE RIESGO
# =========================================================

@app.get("/riesgo/{comuna}")
def obtener_riesgo(
    comuna: str,
):

    comuna_url = quote(
        comuna,
        safe="",
    )


    # -----------------------------------------------------
    # OBTENER VARIABLES
    # -----------------------------------------------------

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
        == 404
    ):
        raise HTTPException(
            status_code=404,
            detail=(
                "Comuna no encontrada"
            ),
        )


    if (
        respuesta_datos.status_code
        != 200
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


    # -----------------------------------------------------
    # PREPARAR ENTRADA DEL MODELO
    # -----------------------------------------------------

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


    # -----------------------------------------------------
    # INFERENCIA + SHAP
    # -----------------------------------------------------

    try:
        respuesta_riesgo = requests.post(
            f"{RISK_SERVICE}/predecir",

            json=datos_modelo,

            timeout=15,
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
        != 200
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


# =========================================================
# REPORTES CIUDADANOS - CREAR
# PÚBLICO
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
                str(latitud),

            "longitud":
                str(longitud),
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

            data=datos,

            files=archivos,

            timeout=90,
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
        status_code=(
            respuesta.status_code
        ),

        content=contenido,
    )


# =========================================================
# REPORTES CONFIRMADOS - PÚBLICO
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
        != 200
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
# IMÁGENES DE REPORTES
# PÚBLICO
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
        == 404
    ):
        raise HTTPException(
            status_code=404,
            detail=(
                "Imagen no encontrada"
            ),
        )


    if (
        respuesta.status_code
        != 200
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
# ADMIN - REPORTES PENDIENTES
# PROTEGIDO CON JWT
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
        != 200
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
# ADMIN - CONFIRMAR REPORTE
# PROTEGIDO CON JWT
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
# ADMIN - RECHAZAR REPORTE
# PROTEGIDO CON JWT
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