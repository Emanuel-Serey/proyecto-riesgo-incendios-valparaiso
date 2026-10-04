import os
import pandas as pd

from dotenv import load_dotenv
from sqlalchemy import create_engine, text, URL


load_dotenv()


def crear_conexion():

    url = URL.create(
        drivername="postgresql+psycopg2",
        username=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", 5432)),
        database=os.getenv("DB_NAME")
    )

    return create_engine(url)


def crear_estructura_bd(engine):

    sql = """
    CREATE TABLE IF NOT EXISTS observaciones_incendios (

        id BIGSERIAL PRIMARY KEY,

        comuna VARCHAR(100) NOT NULL,
        periodo DATE NOT NULL,

        temperatura DOUBLE PRECISION,
        humedad DOUBLE PRECISION,
        viento DOUBLE PRECISION,

        vegetacion_cobertura VARCHAR(100) NOT NULL,

        incendios_historicos INTEGER NOT NULL,
        ocurrencia_incendio SMALLINT NOT NULL,

        codigo_estacion VARCHAR(20),
        nombre_estacion VARCHAR(150),
        distancia_estacion_km DOUBLE PRECISION,

        anio_cobertura INTEGER,

        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

        CONSTRAINT uq_observacion_comuna_periodo
        UNIQUE (comuna, periodo),

        CONSTRAINT chk_ocurrencia_incendio
        CHECK (ocurrencia_incendio IN (0, 1)),

        CONSTRAINT chk_humedad
        CHECK (
            humedad IS NULL
            OR humedad BETWEEN 0 AND 100
        ),

        CONSTRAINT chk_viento
        CHECK (
            viento IS NULL
            OR viento >= 0
        ),

        CONSTRAINT chk_incendios_historicos
        CHECK (
            incendios_historicos >= 0
        )
    );


    CREATE INDEX IF NOT EXISTS idx_observaciones_periodo
    ON observaciones_incendios(periodo);


    CREATE INDEX IF NOT EXISTS idx_observaciones_comuna
    ON observaciones_incendios(comuna);


    CREATE INDEX IF NOT EXISTS idx_observaciones_ocurrencia_incendio
    ON observaciones_incendios(ocurrencia_incendio);


    CREATE INDEX IF NOT EXISTS idx_observaciones_estacion
    ON observaciones_incendios(codigo_estacion);


    CREATE OR REPLACE VIEW dataset_modelo AS

    SELECT
        comuna,
        periodo,
        temperatura,
        humedad,
        viento,
        vegetacion_cobertura,
        incendios_historicos,
        ocurrencia_incendio,
        codigo_estacion,
        nombre_estacion,
        distancia_estacion_km,
        anio_cobertura

    FROM observaciones_incendios

    WHERE temperatura IS NOT NULL
      AND humedad IS NOT NULL
      AND viento IS NOT NULL
      AND vegetacion_cobertura IS NOT NULL
      AND incendios_historicos IS NOT NULL
      AND ocurrencia_incendio IS NOT NULL;
    """

    with engine.begin() as conexion:

        for sentencia in sql.split(";"):

            if sentencia.strip():
                conexion.execute(
                    text(sentencia)
                )


def preparar_datos(datos):

    datos = datos.copy()

    # YYYY-MM -> DATE
    datos["periodo"] = pd.to_datetime(
        datos["periodo"] + "-01"
    )

    columnas = [
        "comuna",
        "periodo",
        "temperatura",
        "humedad",
        "viento",
        "vegetacion_cobertura",
        "incendios_historicos",
        "ocurrencia_incendio",
        "codigo_estacion",
        "nombre_estacion",
        "distancia_estacion_km",
        "anio_cobertura"
    ]

    return datos[columnas]


def cargar_postgresql(datos):

    print(
        "\nCargando datos a PostgreSQL..."
    )

    engine = crear_conexion()

    with engine.connect() as conexion:
        conexion.execute(
            text("SELECT 1")
        )

    print(
        "Conexión a PostgreSQL correcta."
    )

    crear_estructura_bd(
        engine
    )

    datos = preparar_datos(
        datos
    )

    # Tabla temporal de staging
    with engine.begin() as conexion:

        datos.to_sql(
            name="stg_observaciones_incendios",
            con=conexion,
            if_exists="replace",
            index=False,
            method="multi",
            chunksize=500
        )

        sql_upsert = """
        INSERT INTO observaciones_incendios (

            comuna,
            periodo,
            temperatura,
            humedad,
            viento,
            vegetacion_cobertura,
            incendios_historicos,
            ocurrencia_incendio,
            codigo_estacion,
            nombre_estacion,
            distancia_estacion_km,
            anio_cobertura
        )

        SELECT

            comuna,
            periodo,
            temperatura,
            humedad,
            viento,
            vegetacion_cobertura,
            incendios_historicos,
            ocurrencia_incendio,
            codigo_estacion,
            nombre_estacion,
            distancia_estacion_km,
            anio_cobertura

        FROM stg_observaciones_incendios

        ON CONFLICT (comuna, periodo)

        DO UPDATE SET

            temperatura =
                EXCLUDED.temperatura,

            humedad =
                EXCLUDED.humedad,

            viento =
                EXCLUDED.viento,

            vegetacion_cobertura =
                EXCLUDED.vegetacion_cobertura,

            incendios_historicos =
                EXCLUDED.incendios_historicos,

            ocurrencia_incendio =
                EXCLUDED.ocurrencia_incendio,

            codigo_estacion =
                EXCLUDED.codigo_estacion,

            nombre_estacion =
                EXCLUDED.nombre_estacion,

            distancia_estacion_km =
                EXCLUDED.distancia_estacion_km,

            anio_cobertura =
                EXCLUDED.anio_cobertura,

            updated_at =
                NOW();
        """

        conexion.execute(
            text(sql_upsert)
        )

        conexion.execute(
            text(
                "DROP TABLE stg_observaciones_incendios;"
            )
        )

    print(
        "Carga incremental terminada."
    )

    print(
        "Registros procesados:",
        len(datos)
    )


if __name__ == "__main__":

    from integracion import integrar_todas_las_fuentes

    datos = integrar_todas_las_fuentes()

    cargar_postgresql(
        datos
    )