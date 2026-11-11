import io
import os
import uuid

from contextlib import asynccontextmanager
from pathlib import Path

import imagehash

from dotenv import load_dotenv

from fastapi import (
    FastAPI,
    File,
    Form,
    HTTPException,
    UploadFile,
)

from fastapi.staticfiles import StaticFiles

from huggingface_hub import hf_hub_download

from PIL import Image

from sqlalchemy import (
    create_engine,
    text,
)

from sqlalchemy.engine import URL

from sqlalchemy.exc import SQLAlchemyError

from ultralytics import YOLO


# =========================================================
# VARIABLES DE ENTORNO
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


# =========================================================
# RAÍZ DEL PROYECTO
# =========================================================

def obtener_project_root():

    archivo_actual = Path(
        __file__
    ).resolve()

    for carpeta in archivo_actual.parents:

        if (
            carpeta / ".env"
        ).exists():

            return carpeta

    return Path.cwd()


PROJECT_ROOT = (
    obtener_project_root()
)


# =========================================================
# BASE DE DATOS
# =========================================================

REPORT_DB_HOST = os.getenv(
    "REPORT_DB_HOST",
    "127.0.0.1",
)

REPORT_DB_PORT = int(
    os.getenv(
        "REPORT_DB_PORT",
        "5432",
    )
)

REPORT_DB_NAME = os.getenv(
    "REPORT_DB_NAME",
    "incendios_reportes_dev",
)

REPORT_DB_USER = os.getenv(
    "REPORT_DB_USER",
    "reportes_app",
)

REPORT_DB_PASSWORD = os.getenv(
    "REPORT_DB_PASSWORD",
    "",
)


DATABASE_URL = URL.create(

    drivername=
        "postgresql+psycopg2",

    username=
        REPORT_DB_USER,

    password=
        REPORT_DB_PASSWORD,

    host=
        REPORT_DB_HOST,

    port=
        REPORT_DB_PORT,

    database=
        REPORT_DB_NAME,
)


engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)


# =========================================================
# ARCHIVOS
# =========================================================

UPLOAD_DIR = (
    PROJECT_ROOT
    / "data"
    / "reportes"
)


UPLOAD_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


MAX_IMAGEN_MB = 10


FORMATOS_PERMITIDOS = {

    "JPEG":
        ".jpg",

    "PNG":
        ".png",

    "WEBP":
        ".webp",

}


# =========================================================
# REPORTES CERCANOS
# =========================================================

REPORTES_CERCANOS_RADIO_M = 500

REPORTES_CERCANOS_VENTANA_MINUTOS = 30

REPORTES_CERCANOS_VENTANA_SEGUNDOS = (
    REPORTES_CERCANOS_VENTANA_MINUTOS
    *
    60
)


# GPS con más de 500 metros de incertidumbre
# no se considera suficientemente preciso para
# corroborar automáticamente otro reporte.

MAX_PRECISION_GPS_CORROBORACION_M = 500


# =========================================================
# YOLO
# =========================================================

YOLO_REPO_ID = (
    "rabahdev/fire-smoke-yolov8n"
)

YOLO_FILENAME = (
    "best.pt"
)

YOLO_CONFIDENCE = float(
    os.getenv(
        "YOLO_CONFIDENCE",
        "0.25",
    )
)


modelo_yolo = None


def obtener_modelo_yolo():

    global modelo_yolo


    if (
        modelo_yolo
        is not None
    ):

        return modelo_yolo


    ruta_modelo = (
        hf_hub_download(

            repo_id=
                YOLO_REPO_ID,

            filename=
                YOLO_FILENAME,

        )
    )


    modelo_yolo = YOLO(
        ruta_modelo
    )


    return modelo_yolo


# =========================================================
# PHASH
# =========================================================

PHASH_DUPLICATE_MAX_DISTANCE = int(
    os.getenv(
        "PHASH_DUPLICATE_MAX_DISTANCE",
        "6",
    )
)


def calcular_phash_bytes(
    contenido: bytes,
) -> str:

    try:

        with Image.open(
            io.BytesIO(
                contenido
            )
        ) as imagen:

            imagen_rgb = (
                imagen.convert(
                    "RGB"
                )
            )


            return str(
                imagehash.phash(
                    imagen_rgb
                )
            )


    except Exception:

        raise HTTPException(
            status_code=400,
            detail=(
                "No fue posible analizar "
                "la fotografía"
            ),
        )


def calcular_phash_archivo(
    ruta: Path,
) -> str | None:

    try:

        with Image.open(
            ruta
        ) as imagen:

            imagen_rgb = (
                imagen.convert(
                    "RGB"
                )
            )


            return str(
                imagehash.phash(
                    imagen_rgb
                )
            )


    except Exception:

        return None


def buscar_imagen_duplicada(
    nuevo_hash: str,
):

    mejor_id = None

    mejor_distancia = None


    nuevo = (
        imagehash.hex_to_hash(
            nuevo_hash
        )
    )


    with engine.connect() as conexion:

        filas = conexion.execute(
            text(
                """
                SELECT
                    id_reporte,
                    imagen_phash

                FROM public.reportes_ciudadanos

                WHERE imagen_phash IS NOT NULL

                ORDER BY
                    id_reporte DESC
                """
            )
        ).mappings().all()


    for fila in filas:

        try:

            hash_anterior = (
                imagehash.hex_to_hash(
                    fila[
                        "imagen_phash"
                    ]
                )
            )


            distancia = (
                nuevo
                -
                hash_anterior
            )


        except Exception:

            continue


        if (
            mejor_distancia is None
            or
            distancia <
            mejor_distancia
        ):

            mejor_distancia = (
                distancia
            )


            mejor_id = int(
                fila[
                    "id_reporte"
                ]
            )


    if (
        mejor_distancia
        is not None
        and
        mejor_distancia
        <=
        PHASH_DUPLICATE_MAX_DISTANCE
    ):

        return {

            "posible_duplicado":
                True,

            "reporte_duplicado_id":
                mejor_id,

            "distancia_phash":
                int(
                    mejor_distancia
                ),

        }


    return {

        "posible_duplicado":
            False,

        "reporte_duplicado_id":
            None,

        "distancia_phash":
            (
                int(
                    mejor_distancia
                )

                if
                mejor_distancia
                is not None

                else None
            ),

    }


# =========================================================
# COMPLETAR PHASH DE REPORTES ANTIGUOS
# =========================================================

def completar_hashes_existentes():

    try:

        with engine.connect() as conexion:

            filas = conexion.execute(
                text(
                    """
                    SELECT
                        id_reporte,
                        imagen_url

                    FROM public.reportes_ciudadanos

                    WHERE imagen_phash IS NULL
                      AND imagen_url IS NOT NULL
                    """
                )
            ).mappings().all()


        if not filas:

            return


        actualizaciones = []


        for fila in filas:

            imagen_url = (
                fila[
                    "imagen_url"
                ]
            )


            if not imagen_url:

                continue


            nombre_archivo = (
                Path(
                    imagen_url
                ).name
            )


            ruta = (
                UPLOAD_DIR
                /
                nombre_archivo
            )


            if not ruta.exists():

                continue


            hash_imagen = (
                calcular_phash_archivo(
                    ruta
                )
            )


            if not hash_imagen:

                continue


            actualizaciones.append(
                {

                    "id_reporte":
                        fila[
                            "id_reporte"
                        ],

                    "imagen_phash":
                        hash_imagen,

                }
            )


        if not actualizaciones:

            return


        with engine.begin() as conexion:

            for item in actualizaciones:

                conexion.execute(
                    text(
                        """
                        UPDATE
                            public.reportes_ciudadanos

                        SET
                            imagen_phash =
                            :imagen_phash

                        WHERE
                            id_reporte =
                            :id_reporte
                        """
                    ),
                    item,
                )


        print(
            "[Report Service] "
            f"{len(actualizaciones)} "
            "hashes de imágenes existentes "
            "fueron calculados."
        )


    except SQLAlchemyError as error:

        print(
            "[Report Service] "
            "No fue posible completar "
            "los hashes existentes:"
        )

        print(
            error
        )


# =========================================================
# LIFESPAN
# =========================================================

@asynccontextmanager
async def lifespan(
    app: FastAPI,
):

    completar_hashes_existentes()

    yield


# =========================================================
# APP
# =========================================================

app = FastAPI(

    title=(
        "Report Service - "
        "Reportes Ciudadanos"
    ),

    version="1.5",

    lifespan=
        lifespan,

)


app.mount(

    "/imagenes-reportes",

    StaticFiles(
        directory=str(
            UPLOAD_DIR
        )
    ),

    name=
        "imagenes-reportes",

)


# =========================================================
# VALIDAR IMAGEN
# =========================================================

def validar_imagen(
    contenido: bytes,
):

    if not contenido:

        raise HTTPException(
            status_code=400,
            detail=(
                "La fotografía está vacía"
            ),
        )


    limite_bytes = (
        MAX_IMAGEN_MB
        *
        1024
        *
        1024
    )


    if (
        len(
            contenido
        )
        >
        limite_bytes
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                f"La fotografía supera "
                f"el máximo de "
                f"{MAX_IMAGEN_MB} MB"
            ),
        )


    try:

        with Image.open(
            io.BytesIO(
                contenido
            )
        ) as imagen:

            formato = (
                imagen.format
            )


            imagen.verify()


    except Exception:

        raise HTTPException(
            status_code=400,
            detail=(
                "El archivo enviado "
                "no es una imagen válida"
            ),
        )


    if (
        formato
        not in
        FORMATOS_PERMITIDOS
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "Formato no permitido. "
                "Utiliza JPG, PNG o WebP"
            ),
        )


    return formato


# =========================================================
# GUARDAR IMAGEN
# =========================================================

def guardar_imagen(
    contenido: bytes,
    formato: str,
):

    extension = (
        FORMATOS_PERMITIDOS[
            formato
        ]
    )


    nombre = (
        f"{uuid.uuid4().hex}"
        f"{extension}"
    )


    ruta = (
        UPLOAD_DIR
        /
        nombre
    )


    ruta.write_bytes(
        contenido
    )


    return (
        nombre,
        ruta,
    )


# =========================================================
# YOLO
# =========================================================

def analizar_imagen_yolo(
    ruta_imagen: Path,
):

    modelo = (
        obtener_modelo_yolo()
    )


    try:

        resultados = (
            modelo.predict(

                source=
                    str(
                        ruta_imagen
                    ),

                conf=
                    YOLO_CONFIDENCE,

                verbose=
                    False,

            )
        )


    except Exception as error:

        print(
            "[Report Service] "
            "Error ejecutando YOLO:"
        )


        print(
            error
        )


        raise HTTPException(
            status_code=500,
            detail=(
                "No fue posible analizar "
                "la fotografía"
            ),
        )


    mejor_clase = None

    mejor_confianza = None


    for resultado in resultados:

        if (
            resultado.boxes
            is None
        ):

            continue


        for caja in resultado.boxes:

            confianza = float(
                caja.conf[
                    0
                ]
            )


            clase_id = int(
                caja.cls[
                    0
                ]
            )


            nombre_clase = str(
                resultado.names[
                    clase_id
                ]
            ).lower()


            if (
                nombre_clase
                not in {
                    "fire",
                    "smoke",
                }
            ):

                continue


            if (
                mejor_confianza is None
                or
                confianza >
                mejor_confianza
            ):

                mejor_confianza = (
                    confianza
                )


                mejor_clase = (
                    nombre_clase
                )


    if (
        mejor_clase
        is None
    ):

        return {

            "detectado":
                False,

            "clase":
                None,

            "confianza":
                None,

        }


    return {

        "detectado":
            True,

        "clase":
            mejor_clase,

        "confianza":
            round(
                mejor_confianza,
                4,
            ),

    }


# =========================================================
# SELECT BASE
# =========================================================

SELECT_REPORTE = f"""
SELECT

    r.id_reporte,

    r.fecha_reporte,

    r.descripcion,

    r.estado,


    ST_Y(
        r.ubicacion::geometry
    ) AS latitud,


    ST_X(
        r.ubicacion::geometry
    ) AS longitud,


    r.precision_gps_m,

    r.origen_ubicacion,

    r.imagen_url,


    r.yolo_detectado,

    r.yolo_clase,

    r.yolo_confianza,


    r.imagen_phash,

    r.posible_duplicado,

    r.reporte_duplicado_id,

    r.distancia_phash,


    r.fecha_creacion,


    COALESCE(
        cercania.reportes_cercanos_count,
        0
    ) AS reportes_cercanos_count,


    cercania.reportes_cercanos_ids,


    cercania.distancia_reporte_cercano_m


FROM public.reportes_ciudadanos AS r


LEFT JOIN LATERAL
(
    SELECT

        COUNT(*)::INTEGER
        AS reportes_cercanos_count,


        ARRAY_AGG(
            r2.id_reporte

            ORDER BY
                ST_Distance(
                    r2.ubicacion,
                    r.ubicacion
                )
        )
        AS reportes_cercanos_ids,


        MIN(
            ST_Distance(
                r2.ubicacion,
                r.ubicacion
            )
        )
        AS distancia_reporte_cercano_m


    FROM public.reportes_ciudadanos AS r2


    WHERE

        r2.id_reporte <>
        r.id_reporte


        -- ===============================================
        -- SOLO REPORTES ACTIVOS
        -- ===============================================

        AND
        r2.estado IN (
            'pendiente',
            'confirmado'
        )


        -- ===============================================
        -- EL REPORTE PRINCIPAL NO PUEDE SER DUPLICADO
        -- ===============================================

        AND
        COALESCE(
            r.posible_duplicado,
            FALSE
        ) = FALSE


        -- ===============================================
        -- EL REPORTE RELACIONADO TAMPOCO
        -- ===============================================

        AND
        COALESCE(
            r2.posible_duplicado,
            FALSE
        ) = FALSE


        -- ===============================================
        -- SOLO GPS REAL EN EL REPORTE PRINCIPAL
        -- ===============================================

        AND
        r.origen_ubicacion =
        'gps'


        AND
        r.precision_gps_m
        IS NOT NULL


        AND
        r.precision_gps_m
        <=
        {MAX_PRECISION_GPS_CORROBORACION_M}


        -- ===============================================
        -- SOLO GPS REAL EN EL REPORTE RELACIONADO
        -- ===============================================

        AND
        r2.origen_ubicacion =
        'gps'


        AND
        r2.precision_gps_m
        IS NOT NULL


        AND
        r2.precision_gps_m
        <=
        {MAX_PRECISION_GPS_CORROBORACION_M}


        -- ===============================================
        -- VENTANA TEMPORAL
        -- ===============================================

        AND
        ABS(
            EXTRACT(
                EPOCH FROM (
                    r2.fecha_reporte
                    -
                    r.fecha_reporte
                )
            )
        )
        <=
        {REPORTES_CERCANOS_VENTANA_SEGUNDOS}


        -- ===============================================
        -- RADIO GEOGRÁFICO
        -- ===============================================

        AND
        ST_DWithin(
            r2.ubicacion,
            r.ubicacion,
            {REPORTES_CERCANOS_RADIO_M}
        )


        -- ===============================================
        -- MISMA FOTO NO CUENTA COMO CORROBORACIÓN
        -- ===============================================

        AND NOT
        (
            r.imagen_phash
            IS NOT NULL

            AND

            r2.imagen_phash
            IS NOT NULL

            AND

            r.imagen_phash =
            r2.imagen_phash
        )


) AS cercania

ON TRUE
"""


# =========================================================
# NORMALIZAR REPORTE
# =========================================================

def normalizar_reporte(
    fila,
):

    if (
        fila is None
    ):

        return None


    precision = (

        float(
            fila[
                "precision_gps_m"
            ]
        )

        if
        fila[
            "precision_gps_m"
        ]
        is not None

        else None

    )


    confianza = (

        float(
            fila[
                "yolo_confianza"
            ]
        )

        if
        fila[
            "yolo_confianza"
        ]
        is not None

        else None

    )


    distancia_cercana = (

        float(
            fila[
                "distancia_reporte_cercano_m"
            ]
        )

        if
        fila[
            "distancia_reporte_cercano_m"
        ]
        is not None

        else None

    )


    ids_cercanos = (
        fila[
            "reportes_cercanos_ids"
        ]
        or []
    )


    origen = (
        fila[
            "origen_ubicacion"
        ]
        or
        "gps"
    )


    # =====================================================
    # UBICACIÓN APTA PARA CORROBORACIÓN AUTOMÁTICA
    # =====================================================

    ubicacion_utilizable = (

        origen ==
        "gps"

        and

        precision
        is not None

        and

        precision
        <=
        MAX_PRECISION_GPS_CORROBORACION_M

    )


    return {

        "id_reporte":
            int(
                fila[
                    "id_reporte"
                ]
            ),


        "fecha_reporte":
            fila[
                "fecha_reporte"
            ],


        "descripcion":
            fila[
                "descripcion"
            ],


        "estado":
            fila[
                "estado"
            ],


        "latitud":
            float(
                fila[
                    "latitud"
                ]
            ),


        "longitud":
            float(
                fila[
                    "longitud"
                ]
            ),


        "precision_gps_m":
            precision,


        "origen_ubicacion":
            origen,


        "ubicacion_utilizable_cercania":
            ubicacion_utilizable,


        "imagen_url":
            fila[
                "imagen_url"
            ],


        "yolo_detectado":
            fila[
                "yolo_detectado"
            ],


        "yolo_clase":
            fila[
                "yolo_clase"
            ],


        "yolo_confianza":
            confianza,


        "imagen_phash":
            fila[
                "imagen_phash"
            ],


        "posible_duplicado":
            bool(
                fila[
                    "posible_duplicado"
                ]
            ),


        "reporte_duplicado_id":
            (
                int(
                    fila[
                        "reporte_duplicado_id"
                    ]
                )

                if
                fila[
                    "reporte_duplicado_id"
                ]
                is not None

                else None
            ),


        "distancia_phash":
            (
                int(
                    fila[
                        "distancia_phash"
                    ]
                )

                if
                fila[
                    "distancia_phash"
                ]
                is not None

                else None
            ),


        "reportes_cercanos_count":
            int(
                fila[
                    "reportes_cercanos_count"
                ]
                or
                0
            ),


        "reportes_cercanos_ids":
            [
                int(
                    reporte_id
                )

                for reporte_id
                in ids_cercanos
            ],


        "distancia_reporte_cercano_m":
            distancia_cercana,


        "radio_cercania_m":
            REPORTES_CERCANOS_RADIO_M,


        "ventana_cercania_min":
            REPORTES_CERCANOS_VENTANA_MINUTOS,


        "posible_mismo_evento":
            (
                int(
                    fila[
                        "reportes_cercanos_count"
                    ]
                    or
                    0
                )
                >
                0
            ),


        "fecha_creacion":
            fila[
                "fecha_creacion"
            ],

    }


# =========================================================
# OBTENER REPORTE DE DB
# =========================================================

def obtener_reporte_db(
    id_reporte: int,
):

    with engine.connect() as conexion:

        fila = conexion.execute(

            text(
                SELECT_REPORTE
                +
                """
                WHERE
                    r.id_reporte =
                    :id_reporte
                """
            ),

            {
                "id_reporte":
                    id_reporte,
            },

        ).mappings().first()


    return normalizar_reporte(
        fila
    )


# =========================================================
# HEALTH
# =========================================================

@app.get("/health")
def health():

    return {
        "status":
            "ok"
    }


@app.get("/db-health")
def db_health():

    try:

        with engine.connect() as conexion:

            version = (
                conexion.execute(
                    text(
                        """
                        SELECT
                            PostGIS_Version()
                        """
                    )
                ).scalar_one()
            )


        return {

            "status":
                "ok",

            "database":
                REPORT_DB_NAME,

            "postgis_version":
                version,

        }


    except SQLAlchemyError:

        raise HTTPException(
            status_code=503,
            detail=(
                "Base de datos "
                "de reportes no disponible"
            ),
        )


# =========================================================
# CREAR REPORTE
# =========================================================

@app.post("/reportes")
async def crear_reporte(

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

    # =====================================================
    # VALIDAR COORDENADAS
    # =====================================================

    if not (
        -90
        <=
        latitud
        <=
        90
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "Latitud inválida"
            ),
        )


    if not (
        -180
        <=
        longitud
        <=
        180
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "Longitud inválida"
            ),
        )


    if (
        precision_gps_m
        is not None
        and
        precision_gps_m
        < 0
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "Precisión GPS inválida"
            ),
        )


    # =====================================================
    # ORIGEN DE UBICACIÓN
    # =====================================================

    # Si el frontend envía precisión GPS:
    # origen = gps.
    #
    # Si no envía precisión:
    # origen = manual.

    origen_ubicacion = (

        "gps"

        if
        precision_gps_m
        is not None

        else
        "manual"

    )


    # =====================================================
    # DESCRIPCIÓN
    # =====================================================

    if descripcion:

        descripcion = (
            descripcion.strip()
        )


        if (
            len(
                descripcion
            )
            >
            500
        ):

            raise HTTPException(
                status_code=400,
                detail=(
                    "La descripción supera "
                    "los 500 caracteres"
                ),
            )


        if not descripcion:

            descripcion = None


    # =====================================================
    # LEER IMAGEN
    # =====================================================

    contenido = (
        await imagen.read()
    )


    formato = (
        validar_imagen(
            contenido
        )
    )


    # =====================================================
    # PHASH
    # =====================================================

    imagen_phash = (
        calcular_phash_bytes(
            contenido
        )
    )


    duplicado = (
        buscar_imagen_duplicada(
            imagen_phash
        )
    )


    # =====================================================
    # GUARDAR IMAGEN
    # =====================================================

    ruta_imagen = None


    try:

        (
            nombre_archivo,
            ruta_imagen,
        ) = guardar_imagen(
            contenido,
            formato,
        )


        imagen_url = (
            "/imagenes-reportes/"
            f"{nombre_archivo}"
        )


        # =================================================
        # YOLO
        # =================================================

        resultado_yolo = (
            analizar_imagen_yolo(
                ruta_imagen
            )
        )


        estado = (

            "pendiente"

            if
            resultado_yolo[
                "detectado"
            ]

            else
            "rechazado"

        )


        # =================================================
        # INSERT
        # =================================================

        with engine.begin() as conexion:

            id_reporte = (
                conexion.execute(

                    text(
                        """
                        INSERT INTO
                            public.reportes_ciudadanos
                        (
                            descripcion,

                            estado,

                            ubicacion,

                            precision_gps_m,

                            origen_ubicacion,

                            imagen_url,

                            yolo_detectado,

                            yolo_clase,

                            yolo_confianza,

                            imagen_phash,

                            posible_duplicado,

                            reporte_duplicado_id,

                            distancia_phash
                        )

                        VALUES
                        (
                            :descripcion,

                            :estado,

                            ST_SetSRID(
                                ST_MakePoint(
                                    :longitud,
                                    :latitud
                                ),
                                4326
                            )::geography,

                            :precision_gps_m,

                            :origen_ubicacion,

                            :imagen_url,

                            :yolo_detectado,

                            :yolo_clase,

                            :yolo_confianza,

                            :imagen_phash,

                            :posible_duplicado,

                            :reporte_duplicado_id,

                            :distancia_phash
                        )

                        RETURNING
                            id_reporte
                        """
                    ),

                    {

                        "descripcion":
                            descripcion,

                        "estado":
                            estado,

                        "longitud":
                            longitud,

                        "latitud":
                            latitud,

                        "precision_gps_m":
                            precision_gps_m,

                        "origen_ubicacion":
                            origen_ubicacion,

                        "imagen_url":
                            imagen_url,

                        "yolo_detectado":
                            resultado_yolo[
                                "detectado"
                            ],

                        "yolo_clase":
                            resultado_yolo[
                                "clase"
                            ],

                        "yolo_confianza":
                            resultado_yolo[
                                "confianza"
                            ],

                        "imagen_phash":
                            imagen_phash,

                        "posible_duplicado":
                            duplicado[
                                "posible_duplicado"
                            ],

                        "reporte_duplicado_id":
                            duplicado[
                                "reporte_duplicado_id"
                            ],

                        "distancia_phash":
                            duplicado[
                                "distancia_phash"
                            ],

                    },

                ).scalar_one()
            )


    except Exception:

        if (
            ruta_imagen
            is not None
            and
            ruta_imagen.exists()
        ):

            try:

                ruta_imagen.unlink()

            except OSError:

                pass


        raise


    return obtener_reporte_db(
        id_reporte
    )


# =========================================================
# LISTAR TODOS LOS REPORTES
# =========================================================

@app.get("/reportes")
def listar_reportes():

    with engine.connect() as conexion:

        filas = conexion.execute(
            text(
                SELECT_REPORTE
                +
                """
                ORDER BY
                    r.fecha_reporte DESC
                """
            )
        ).mappings().all()


    return [

        normalizar_reporte(
            fila
        )

        for fila
        in filas

    ]


# =========================================================
# REPORTES PENDIENTES
# =========================================================

@app.get(
    "/reportes/estado/pendientes"
)
def listar_pendientes():

    with engine.connect() as conexion:

        filas = conexion.execute(
            text(
                SELECT_REPORTE
                +
                """
                WHERE
                    r.estado =
                    'pendiente'

                ORDER BY
                    r.fecha_reporte DESC
                """
            )
        ).mappings().all()


    return [

        normalizar_reporte(
            fila
        )

        for fila
        in filas

    ]


# =========================================================
# REPORTES CONFIRMADOS
# =========================================================

@app.get(
    "/reportes/estado/confirmados"
)
def listar_confirmados():

    with engine.connect() as conexion:

        filas = conexion.execute(
            text(
                SELECT_REPORTE
                +
                """
                WHERE
                    r.estado =
                    'confirmado'

                ORDER BY
                    r.fecha_reporte DESC
                """
            )
        ).mappings().all()


    return [

        normalizar_reporte(
            fila
        )

        for fila
        in filas

    ]


# =========================================================
# OBTENER UN REPORTE
# =========================================================

@app.get(
    "/reportes/{id_reporte}"
)
def obtener_reporte(
    id_reporte: int,
):

    reporte = (
        obtener_reporte_db(
            id_reporte
        )
    )


    if (
        reporte
        is None
    ):

        raise HTTPException(
            status_code=404,
            detail=(
                "Reporte no encontrado"
            ),
        )


    return reporte


# =========================================================
# CONFIRMAR REPORTE
# =========================================================

@app.patch(
    "/reportes/{id_reporte}/confirmar"
)
def confirmar_reporte(
    id_reporte: int,
):

    with engine.begin() as conexion:

        actualizado = (
            conexion.execute(

                text(
                    """
                    UPDATE
                        public.reportes_ciudadanos

                    SET
                        estado =
                        'confirmado'

                    WHERE
                        id_reporte =
                        :id_reporte

                    AND
                        estado =
                        'pendiente'

                    RETURNING
                        id_reporte
                    """
                ),

                {
                    "id_reporte":
                        id_reporte,
                },

            ).scalar_one_or_none()
        )


    if (
        actualizado
        is None
    ):

        existente = (
            obtener_reporte_db(
                id_reporte
            )
        )


        if (
            existente
            is None
        ):

            raise HTTPException(
                status_code=404,
                detail=(
                    "Reporte no encontrado"
                ),
            )


        raise HTTPException(
            status_code=409,
            detail=(
                "El reporte ya fue procesado"
            ),
        )


    return obtener_reporte_db(
        id_reporte
    )


# =========================================================
# RECHAZAR REPORTE
# =========================================================

@app.patch(
    "/reportes/{id_reporte}/rechazar"
)
def rechazar_reporte(
    id_reporte: int,
):

    with engine.begin() as conexion:

        actualizado = (
            conexion.execute(

                text(
                    """
                    UPDATE
                        public.reportes_ciudadanos

                    SET
                        estado =
                        'rechazado'

                    WHERE
                        id_reporte =
                        :id_reporte

                    AND
                        estado =
                        'pendiente'

                    RETURNING
                        id_reporte
                    """
                ),

                {
                    "id_reporte":
                        id_reporte,
                },

            ).scalar_one_or_none()
        )


    if (
        actualizado
        is None
    ):

        existente = (
            obtener_reporte_db(
                id_reporte
            )
        )


        if (
            existente
            is None
        ):

            raise HTTPException(
                status_code=404,
                detail=(
                    "Reporte no encontrado"
                ),
            )


        raise HTTPException(
            status_code=409,
            detail=(
                "El reporte ya fue procesado"
            ),
        )


    return obtener_reporte_db(
        id_reporte
    )