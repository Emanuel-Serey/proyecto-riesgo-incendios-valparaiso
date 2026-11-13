from pathlib import Path
from datetime import date, timedelta

import logging
import time

from sqlalchemy import text


from ingesta import ejecutar_ingesta

from limpieza_transformacion import (
    ejecutar_transformacion
)

from integracion import (
    integrar,
    integrar_actual,
)

from validacion import (
    validar,
    validar_variables_actuales,
)

from carga import (
    obtener_engine,
    crear_estructura_dataset,
    crear_estructura_operacional,
    crear_vista,
    cargar,
    cargar_variables_actuales,
)


# =========================================================
# CONFIGURACIÓN
# =========================================================

BASE_DIR = (
    Path(__file__)
    .resolve()
    .parents[2]
)


LOGS = (
    BASE_DIR
    / "logs"
)


LOGS.mkdir(
    parents=True,
    exist_ok=True,
)


logger = logging.getLogger(
    "pipeline"
)


logger.setLevel(
    logging.INFO
)


logger.propagate = False


if not logger.handlers:

    fmt = logging.Formatter(
        "%(asctime)s - "
        "%(levelname)s - "
        "%(message)s"
    )


    fh = logging.FileHandler(
        LOGS / "pipeline.log",
        encoding="utf-8",
    )


    sh = logging.StreamHandler()


    fh.setFormatter(
        fmt
    )


    sh.setFormatter(
        fmt
    )


    logger.addHandler(
        fh
    )


    logger.addHandler(
        sh
    )


# =========================================================
# EJECUTAR ETAPA
# =========================================================

def ejecutar_etapa(
    nombre,
    funcion,
    *args,
    **kwargs,
):

    logger.info(
        "Iniciando etapa: %s.",
        nombre,
    )


    inicio = (
        time.perf_counter()
    )


    try:

        resultado = funcion(
            *args,
            **kwargs,
        )


        logger.info(
            "Etapa finalizada: %s | "
            "Tiempo=%.2f s.",
            nombre,
            (
                time.perf_counter()
                -
                inicio
            ),
        )


        return resultado


    except Exception:

        logger.exception(
            "Falló la etapa: %s.",
            nombre,
        )


        raise


# =========================================================
# PREPARAR POSTGRESQL
# =========================================================

def preparar_postgresql():

    engine = (
        obtener_engine()
    )


    try:

        with engine.begin() as conn:

            bd = conn.execute(
                text(
                    """
                    SELECT
                        current_database();
                    """
                )
            ).scalar()


            crear_estructura_dataset(
                conn
            )


            crear_vista(
                conn
            )


            crear_estructura_operacional(
                conn
            )


            estado = conn.execute(
                text(
                    """
                    SELECT

                        COUNT(*)
                            AS registros,

                        COUNT(
                            DISTINCT comuna
                        )
                            AS comunas,

                        MIN(
                            fecha_objetivo
                        )
                            AS fecha_min,

                        MAX(
                            fecha_objetivo
                        )
                            AS fecha_max

                    FROM
                        public.observaciones_incendios_diarias;
                    """
                )
            ).mappings().one()


        historico_completo = (

            estado[
                "registros"
            ]
            >
            0

            and

            estado[
                "comunas"
            ]
            ==
            36

            and

            estado[
                "fecha_min"
            ]
            is not None

            and

            estado[
                "fecha_max"
            ]
            is not None

            and

            str(
                estado[
                    "fecha_min"
                ]
            )
            <=
            "2019-06-02"

            and

            str(
                estado[
                    "fecha_max"
                ]
            )
            >=
            "2025-05-30"

        )


        logger.info(
            "PostgreSQL preparado | "
            "Base=%s | "
            "Histórico=%s registros | "
            "Comunas=%s | "
            "Rango=%s a %s.",
            bd,
            estado[
                "registros"
            ],
            estado[
                "comunas"
            ],
            estado[
                "fecha_min"
            ],
            estado[
                "fecha_max"
            ],
        )


        return (
            historico_completo
        )


    finally:

        engine.dispose()


# =========================================================
# COMPROBAR SI EL DÍA YA ESTÁ CARGADO
# =========================================================

def variables_del_dia_completas(
    fecha_prediccion,
):

    engine = (
        obtener_engine()
    )


    try:

        with engine.connect() as conn:

            estado = conn.execute(

                text(
                    """
                    SELECT

                        COUNT(*)
                            AS registros,

                        COUNT(
                            DISTINCT comuna
                        )
                            AS comunas

                    FROM
                        public.variables_actuales

                    WHERE
                        fecha_prediccion =
                        :fecha_prediccion;
                    """
                ),

                {
                    "fecha_prediccion":
                        fecha_prediccion,
                },

            ).mappings().one()


        registros = int(
            estado[
                "registros"
            ]
            or
            0
        )


        comunas = int(
            estado[
                "comunas"
            ]
            or
            0
        )


        logger.info(
            "Estado variables actuales | "
            "Fecha=%s | "
            "Registros=%s | "
            "Comunas=%s.",
            fecha_prediccion,
            registros,
            comunas,
        )


        return (
            registros == 36
            and
            comunas == 36
        )


    finally:

        engine.dispose()


# =========================================================
# CARGA HISTÓRICA
# =========================================================

def cargar_historico_inicial():

    logger.info(
        "No existe un histórico completo "
        "en PostgreSQL. "
        "Se realizará la carga inicial."
    )


    ejecutar_etapa(
        "Ingesta histórica inicial",
        ejecutar_ingesta,
    )


    ejecutar_etapa(
        "Limpieza y transformación histórica",
        ejecutar_transformacion,
    )


    ejecutar_etapa(
        "Integración histórica",
        integrar,
    )


    ejecutar_etapa(
        "Validación histórica",
        validar,
    )


    ejecutar_etapa(
        "Carga histórica PostgreSQL",
        cargar,
    )


    logger.info(
        "Carga histórica inicial "
        "finalizada correctamente."
    )


# =========================================================
# ACTUALIZACIÓN DIARIA
# =========================================================

def actualizar_datos(
    fecha_prediccion,
):

    fecha_meteorologia = (
        fecha_prediccion
        -
        timedelta(
            days=1
        )
    )


    logger.info(
        "Actualización diaria | "
        "Fecha predicción=%s | "
        "Fecha meteorología=%s.",
        fecha_prediccion,
        fecha_meteorologia,
    )


    ejecutar_etapa(
        "Ingesta de datos nuevos",
        ejecutar_ingesta,
        modo="actual",
        fecha_meteorologia=
            fecha_meteorologia,
    )


    ejecutar_etapa(
        "Limpieza y transformación",
        ejecutar_transformacion,
        modo="actual",
        fecha_meteorologia=
            fecha_meteorologia,
    )


    ejecutar_etapa(
        "Integración",
        integrar_actual,
    )


    ejecutar_etapa(
        "Validación",
        validar_variables_actuales,
    )


    ejecutar_etapa(
        "Carga PostgreSQL",
        cargar_variables_actuales,
    )


# =========================================================
# PIPELINE PRINCIPAL
# =========================================================

def ejecutar_pipeline():

    logger.info(
        "=" * 55
    )


    logger.info(
        "Inicio del pipeline ETL V2."
    )


    logger.info(
        "=" * 55
    )


    inicio = (
        time.perf_counter()
    )


    try:

        historico_completo = (
            ejecutar_etapa(
                "Preparación PostgreSQL",
                preparar_postgresql,
            )
        )


        if historico_completo:

            logger.info(
                "Dataset histórico ya disponible "
                "en PostgreSQL. "
                "No es necesario reconstruirlo."
            )


        else:

            cargar_historico_inicial()


        # -------------------------------------------------
        # FECHA OBJETIVO
        # -------------------------------------------------

        fecha_prediccion = (
            date.today()
        )


        # -------------------------------------------------
        # EVITAR REPETIR EL ETL DEL MISMO DÍA
        # -------------------------------------------------

        if variables_del_dia_completas(
            fecha_prediccion
        ):

            logger.info(
                "El ETL diario ya se encuentra "
                "completo para %s. "
                "Existen las 36 comunas. "
                "No se realizará una nueva ingesta.",
                fecha_prediccion,
            )


            logger.info(
                "=" * 55
            )


            logger.info(
                "Pipeline ETL finalizado "
                "sin cambios | "
                "Tiempo total=%.2f s.",
                (
                    time.perf_counter()
                    -
                    inicio
                ),
            )


            logger.info(
                "=" * 55
            )


            return


        # -------------------------------------------------
        # NO EXISTEN LAS 36 COMUNAS → INTENTAR DMC
        # -------------------------------------------------

        logger.info(
            "No existen las 36 variables "
            "para %s. "
            "Se intentará obtener la "
            "meteorología del día anterior.",
            fecha_prediccion,
        )


        actualizar_datos(
            fecha_prediccion
        )


        # -------------------------------------------------
        # VERIFICACIÓN FINAL
        # -------------------------------------------------

        if not variables_del_dia_completas(
            fecha_prediccion
        ):

            raise RuntimeError(
                "El pipeline terminó, pero no "
                "existen las 36 comunas para "
                f"{fecha_prediccion}."
            )


        logger.info(
            "=" * 55
        )


        logger.info(
            "Pipeline ETL V2 "
            "finalizado correctamente | "
            "Fecha=%s | "
            "Tiempo total=%.2f s.",
            fecha_prediccion,
            (
                time.perf_counter()
                -
                inicio
            ),
        )


        logger.info(
            "=" * 55
        )


    except Exception:

        logger.exception(
            "Pipeline ETL V2 detenido "
            "por error | "
            "Tiempo=%.2f s.",
            (
                time.perf_counter()
                -
                inicio
            ),
        )


        raise


if __name__ == "__main__":

    ejecutar_pipeline()