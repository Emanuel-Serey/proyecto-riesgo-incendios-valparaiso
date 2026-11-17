from pathlib import Path
import os

import geopandas as gpd
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text


# ============================================================
# CONFIGURACIÓN
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]

load_dotenv(BASE_DIR / ".env")

GEOJSON_COMUNAS = (
    BASE_DIR
    / "frontend"
    / "public"
    / "data"
    / "comunas_valparaiso.geojson"
)

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "incendios_valparaiso")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD")

TABLA_COMUNAS = "comunas_geometrias"
TABLA_ESTACIONES = "estaciones_meteorologicas"

# Mismo CRS métrico utilizado conceptualmente por GeoPandas
# para la Región de Valparaíso.
CRS_METRICO = 32719


# ============================================================
# ESTACIONES DMC
# ============================================================
#
# IMPORTANTE:
#
# El sistema utiliza 5 estaciones en total.
#
# 4 son estaciones PRINCIPALES y participan en la asignación
# espacial comuna -> estación.
#
# 330006 Jardín Botánico NO es una estación principal.
# Se utiliza únicamente como RESPALDO de Torquemada cuando
# esta última no posee meteorología válida.
#
# Esto mantiene exactamente la arquitectura del ETL actual.
# ============================================================

ESTACIONES_DMC = [
    {
        "codigo_estacion": "320019",
        "nombre": "San Felipe Escuela Agrícola",
        "latitud": -32.755277,
        "longitud": -70.706944,
        "es_principal": True,
        "es_respaldo": False,
    },
    {
        "codigo_estacion": "320041",
        "nombre": "Viña del Mar Ad. (Torquemada)",
        "latitud": -32.949444,
        "longitud": -71.476110,
        "es_principal": True,
        "es_respaldo": False,
    },
    {
        "codigo_estacion": "330006",
        "nombre": "Jardín Botánico (ex Parque Fauna), Viña del Mar",
        "latitud": -33.044999,
        "longitud": -71.501944,
        "es_principal": False,
        "es_respaldo": True,
    },
    {
        "codigo_estacion": "330007",
        "nombre": "Rodelillo, Ad.",
        "latitud": -33.065277,
        "longitud": -71.556388,
        "es_principal": True,
        "es_respaldo": False,
    },
    {
        "codigo_estacion": "330030",
        "nombre": "Santo Domingo, Ad.",
        "latitud": -33.656111,
        "longitud": -71.613333,
        "es_principal": True,
        "es_respaldo": False,
    },
]


# ============================================================
# CONEXIÓN
# ============================================================

def crear_engine_postgis():
    if not DB_PASSWORD:
        raise ValueError(
            "No se encontró DB_PASSWORD en el archivo .env."
        )

    url = (
        f"postgresql+psycopg://{DB_USER}:{DB_PASSWORD}"
        f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )

    return create_engine(
        url,
        pool_pre_ping=True,
    )


# ============================================================
# POSTGIS
# ============================================================

def verificar_postgis(engine):
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE EXTENSION IF NOT EXISTS postgis;
                """
            )
        )

        version = connection.execute(
            text(
                """
                SELECT PostGIS_Version();
                """
            )
        ).scalar()

    if not version:
        raise RuntimeError(
            "PostGIS no se encuentra disponible."
        )

    return version


# ============================================================
# UTILIDADES
# ============================================================

def tabla_existe(engine, tabla):
    inspector = inspect(engine)

    return inspector.has_table(
        tabla,
        schema="public",
    )


def columnas_tabla(engine, tabla):
    inspector = inspect(engine)

    if not inspector.has_table(
        tabla,
        schema="public",
    ):
        return []

    return [
        columna["name"]
        for columna in inspector.get_columns(
            tabla,
            schema="public",
        )
    ]


def contar_registros(engine, tabla):
    with engine.connect() as connection:
        total = connection.execute(
            text(
                f"""
                SELECT COUNT(*)
                FROM {tabla};
                """
            )
        ).scalar()

    return int(total)


# ============================================================
# COMUNAS
# ============================================================

def cargar_comunas_postgis(engine):
    """
    Carga los mismos 36 polígonos utilizados por el sistema.
    """

    if not GEOJSON_COMUNAS.exists():
        raise FileNotFoundError(
            f"No existe el GeoJSON: {GEOJSON_COMUNAS}"
        )

    comunas = gpd.read_file(
        GEOJSON_COMUNAS
    )

    if "comuna" not in comunas.columns:
        raise ValueError(
            "El GeoJSON no contiene la columna 'comuna'."
        )

    comunas = comunas[
        [
            "comuna",
            "geometry",
        ]
    ].copy()

    comunas["comuna"] = (
        comunas["comuna"]
        .astype(str)
        .str.strip()
    )

    if comunas.crs is None:
        raise ValueError(
            "El GeoJSON no posee CRS."
        )

    if comunas.crs.to_epsg() != 4326:
        comunas = comunas.to_crs(
            epsg=4326
        )

    if len(comunas) != 36:
        raise ValueError(
            f"Se esperaban 36 comunas y se encontraron "
            f"{len(comunas)}."
        )

    if comunas["comuna"].duplicated().any():
        raise ValueError(
            "Existen comunas duplicadas."
        )

    if comunas.geometry.isna().any():
        raise ValueError(
            "Existen comunas sin geometría."
        )

    if (~comunas.geometry.is_valid).any():
        invalidas = comunas.loc[
            ~comunas.geometry.is_valid,
            "comuna",
        ].tolist()

        raise ValueError(
            f"Geometrías inválidas: {invalidas}"
        )

    comunas = comunas.rename_geometry(
        "geom"
    )

    comunas.to_postgis(
        name=TABLA_COMUNAS,
        con=engine,
        if_exists="replace",
        index=False,
    )

    with engine.begin() as connection:
        connection.execute(
            text(
                f"""
                ALTER TABLE {TABLA_COMUNAS}
                ADD COLUMN id SERIAL;
                """
            )
        )

        connection.execute(
            text(
                f"""
                ALTER TABLE {TABLA_COMUNAS}
                ADD CONSTRAINT
                {TABLA_COMUNAS}_pkey
                PRIMARY KEY (id);
                """
            )
        )

        connection.execute(
            text(
                f"""
                ALTER TABLE {TABLA_COMUNAS}
                ADD CONSTRAINT
                {TABLA_COMUNAS}_comuna_unique
                UNIQUE (comuna);
                """
            )
        )

        connection.execute(
            text(
                f"""
                CREATE INDEX IF NOT EXISTS
                idx_{TABLA_COMUNAS}_geom
                ON {TABLA_COMUNAS}
                USING GIST (geom);
                """
            )
        )

    return len(comunas)


# ============================================================
# ESTACIONES
# ============================================================

def cargar_estaciones_postgis(engine):
    """
    Carga las 5 estaciones y almacena explícitamente
    cuál es principal y cuál corresponde a respaldo.
    """

    df = pd.DataFrame(
        ESTACIONES_DMC
    )

    if len(df) != 5:
        raise ValueError(
            "Se esperaban 5 estaciones."
        )

    if df["es_principal"].sum() != 4:
        raise ValueError(
            "Deben existir exactamente 4 estaciones principales."
        )

    if df["es_respaldo"].sum() != 1:
        raise ValueError(
            "Debe existir exactamente 1 estación de respaldo."
        )

    estaciones = gpd.GeoDataFrame(
        df,
        geometry=gpd.points_from_xy(
            df["longitud"],
            df["latitud"],
        ),
        crs="EPSG:4326",
    )

    estaciones = estaciones.rename_geometry(
        "geom"
    )

    if estaciones[
        "codigo_estacion"
    ].duplicated().any():
        raise ValueError(
            "Existen códigos de estación duplicados."
        )

    if estaciones["geom"].isna().any():
        raise ValueError(
            "Existen estaciones sin geometría."
        )

    estaciones.to_postgis(
        name=TABLA_ESTACIONES,
        con=engine,
        if_exists="replace",
        index=False,
    )

    with engine.begin() as connection:
        connection.execute(
            text(
                f"""
                ALTER TABLE {TABLA_ESTACIONES}
                ADD CONSTRAINT
                {TABLA_ESTACIONES}_pkey
                PRIMARY KEY (codigo_estacion);
                """
            )
        )

        connection.execute(
            text(
                f"""
                CREATE INDEX IF NOT EXISTS
                idx_{TABLA_ESTACIONES}_geom
                ON {TABLA_ESTACIONES}
                USING GIST (geom);
                """
            )
        )

    return len(estaciones)


# ============================================================
# VALIDACIÓN
# ============================================================

def catalogos_postgis_validos(engine):
    if not tabla_existe(
        engine,
        TABLA_COMUNAS,
    ):
        return False

    if not tabla_existe(
        engine,
        TABLA_ESTACIONES,
    ):
        return False

    columnas_estaciones = columnas_tabla(
        engine,
        TABLA_ESTACIONES,
    )

    columnas_necesarias = {
        "codigo_estacion",
        "nombre",
        "latitud",
        "longitud",
        "es_principal",
        "es_respaldo",
        "geom",
    }

    if not columnas_necesarias.issubset(
        set(columnas_estaciones)
    ):
        return False

    if contar_registros(
        engine,
        TABLA_COMUNAS,
    ) != 36:
        return False

    if contar_registros(
        engine,
        TABLA_ESTACIONES,
    ) != 5:
        return False

    with engine.connect() as connection:
        principales = connection.execute(
            text(
                f"""
                SELECT COUNT(*)
                FROM {TABLA_ESTACIONES}
                WHERE es_principal = TRUE;
                """
            )
        ).scalar()

        respaldos = connection.execute(
            text(
                f"""
                SELECT COUNT(*)
                FROM {TABLA_ESTACIONES}
                WHERE es_respaldo = TRUE;
                """
            )
        ).scalar()

        jardin_es_principal = connection.execute(
            text(
                f"""
                SELECT es_principal
                FROM {TABLA_ESTACIONES}
                WHERE codigo_estacion = '330006';
                """
            )
        ).scalar()

        invalidas_comunas = connection.execute(
            text(
                f"""
                SELECT COUNT(*)
                FROM {TABLA_COMUNAS}
                WHERE
                    geom IS NULL
                    OR NOT ST_IsValid(geom)
                    OR ST_SRID(geom) <> 4326;
                """
            )
        ).scalar()

        invalidas_estaciones = connection.execute(
            text(
                f"""
                SELECT COUNT(*)
                FROM {TABLA_ESTACIONES}
                WHERE
                    geom IS NULL
                    OR NOT ST_IsValid(geom)
                    OR ST_SRID(geom) <> 4326;
                """
            )
        ).scalar()

    return (
        int(principales) == 4
        and int(respaldos) == 1
        and jardin_es_principal is False
        and int(invalidas_comunas) == 0
        and int(invalidas_estaciones) == 0
    )


# ============================================================
# SINCRONIZACIÓN
# ============================================================

def asegurar_catalogos_postgis(
    forzar=False,
):
    engine = crear_engine_postgis()

    try:
        version = verificar_postgis(
            engine
        )

        print(
            f"PostGIS activo: {version}"
        )

        if (
            not forzar
            and catalogos_postgis_validos(
                engine
            )
        ):
            print(
                "Catálogos PostGIS ya están "
                "cargados y son válidos."
            )

            return {
                "postgis": version,
                "comunas": 36,
                "estaciones": 5,
                "principales": 4,
                "respaldos": 1,
                "recargado": False,
            }

        print(
            "Sincronizando catálogos "
            "geoespaciales..."
        )

        total_comunas = (
            cargar_comunas_postgis(
                engine
            )
        )

        total_estaciones = (
            cargar_estaciones_postgis(
                engine
            )
        )

        if not catalogos_postgis_validos(
            engine
        ):
            raise RuntimeError(
                "Falló la validación de los "
                "catálogos PostGIS."
            )

        return {
            "postgis": version,
            "comunas": total_comunas,
            "estaciones": total_estaciones,
            "principales": 4,
            "respaldos": 1,
            "recargado": True,
        }

    finally:
        engine.dispose()


# ============================================================
# ASIGNACIÓN COMUNA -> ESTACIÓN PRINCIPAL
# ============================================================

def obtener_asignacion_estaciones_postgis():
    """
    Asigna cada comuna únicamente entre las 4 estaciones
    PRINCIPALES.

    Jardín Botánico (330006) queda fuera de esta selección
    y continúa utilizándose únicamente como respaldo
    meteorológico de Torquemada.
    """

    asegurar_catalogos_postgis()

    engine = crear_engine_postgis()

    try:
        consulta = text(
            f"""
            SELECT
                c.comuna,

                e.codigo_estacion
                    AS codigo_estacion_principal,

                e.nombre
                    AS nombre_estacion_principal,

                ROUND(
                    (
                        ST_Distance(
                            ST_Centroid(
                                ST_Transform(
                                    c.geom,
                                    {CRS_METRICO}
                                )
                            ),
                            ST_Transform(
                                e.geom,
                                {CRS_METRICO}
                            )
                        )
                        / 1000
                    )::numeric,
                    2
                )::double precision
                    AS distancia_estacion_km

            FROM {TABLA_COMUNAS} c

            CROSS JOIN LATERAL (
                SELECT
                    codigo_estacion,
                    nombre,
                    geom

                FROM {TABLA_ESTACIONES} e

                WHERE
                    e.es_principal = TRUE

                ORDER BY
                    ST_Distance(
                        ST_Centroid(
                            ST_Transform(
                                c.geom,
                                {CRS_METRICO}
                            )
                        ),
                        ST_Transform(
                            e.geom,
                            {CRS_METRICO}
                        )
                    )

                LIMIT 1
            ) e

            ORDER BY c.comuna;
            """
        )

        asignacion = pd.read_sql(
            consulta,
            engine,
        )

        if len(asignacion) != 36:
            raise ValueError(
                "PostGIS no devolvió asignación "
                "para las 36 comunas."
            )

        if asignacion[
            "codigo_estacion_principal"
        ].isna().any():
            raise ValueError(
                "Existen comunas sin estación principal."
            )

        asignacion[
            "codigo_estacion_principal"
        ] = (
            asignacion[
                "codigo_estacion_principal"
            ]
            .astype(str)
        )

        # Jardín Botánico jamás debe aparecer
        # como estación principal.
        if (
            asignacion[
                "codigo_estacion_principal"
            ]
            .eq("330006")
            .any()
        ):
            raise RuntimeError(
                "Error de arquitectura: Jardín Botánico "
                "fue asignado como estación principal."
            )

        return asignacion

    finally:
        engine.dispose()


# ============================================================
# PRUEBA DIRECTA
# ============================================================

if __name__ == "__main__":
    print(
        "=============================================="
    )
    print(
        "MÓDULO POSTGIS DEL ETL"
    )
    print(
        "=============================================="
    )

    estado = asegurar_catalogos_postgis()

    print("\nEstado:")
    print(estado)

    asignacion = (
        obtener_asignacion_estaciones_postgis()
    )

    print(
        "\nAsignación de estaciones PRINCIPALES:"
    )

    print(
        asignacion.to_string(
            index=False
        )
    )

    print(
        "\nEstaciones principales utilizadas:"
    )

    print(
        asignacion[
            [
                "codigo_estacion_principal",
                "nombre_estacion_principal",
            ]
        ]
        .drop_duplicates()
        .sort_values(
            "codigo_estacion_principal"
        )
        .to_string(index=False)
    )

    print(
        "\n=============================================="
    )
    print(
        "PostGIS listo para ser utilizado por el ETL."
    )
    print(
        "330006 permanece como estación de respaldo."
    )
    print(
        "=============================================="
    )