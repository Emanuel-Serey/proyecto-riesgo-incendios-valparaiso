from pathlib import Path
from datetime import date, timedelta
import os
import json
import logging
import requests

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[2]

RAW = BASE_DIR / "data/raw"
RUTA_DMC = RAW / "dmc/api"
RUTA_CONAF = RAW / "conaf/cobertura_incendios/II_FF.shp"
RUTA_IDE = RAW / "ide/cobertura_vegetacion_valparaiso/cut_2001_2023_R05.shp"
LOGS = BASE_DIR / "logs"

RUTA_DMC.mkdir(parents=True, exist_ok=True)
LOGS.mkdir(parents=True, exist_ok=True)


load_dotenv(BASE_DIR / ".env")

DMC_USUARIO = os.getenv("DMC_USUARIO")
DMC_TOKEN = os.getenv("DMC_TOKEN")


logger = logging.getLogger("ingesta")
logger.setLevel(logging.INFO)
logger.propagate = False

if not logger.handlers:
    fmt = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s"
    )

    fh = logging.FileHandler(
        LOGS / "ingesta.log",
        encoding="utf-8"
    )

    sh = logging.StreamHandler()

    fh.setFormatter(fmt)
    sh.setFormatter(fmt)

    logger.addHandler(fh)
    logger.addHandler(sh)


BASE_DMC = (
    "https://climatologia.meteochile.gob.cl/"
    "application/servicios/getDatosRecientesEma"
)


ESTACIONES_DMC = {
    "320019": "San Felipe Escuela Agrícola",
    "320041": "Viña del Mar Ad. (Torquemada)",
    "330006": "Jardín Botánico (respaldo)",
    "330007": "Rodelillo, Ad.",
    "330030": "Santo Domingo, Ad."
}


# =========================
# SHAPEFILES
# =========================

def verificar_shapefile(ruta, nombre):

    obligatorios = [
        ruta,
        ruta.with_suffix(".dbf"),
        ruta.with_suffix(".shx")
    ]

    faltantes = [
        archivo.name
        for archivo in obligatorios
        if not archivo.exists()
    ]

    if faltantes:
        raise FileNotFoundError(
            f"{nombre}: faltan archivos del shapefile: {faltantes}"
        )

    if not ruta.with_suffix(".prj").exists():
        logger.warning(
            "%s | No se encontró archivo .prj.",
            nombre
        )

    logger.info(
        "%s verificado correctamente | %s.",
        nombre,
        ruta
    )


# =========================
# DMC
# =========================

def obtener_mes_dmc(codigo, anio, mes):

    if not DMC_USUARIO or not DMC_TOKEN:
        raise ValueError(
            "Faltan DMC_USUARIO o DMC_TOKEN en .env"
        )

    url = f"{BASE_DMC}/{codigo}/{anio}/{mes:02d}"

    respuesta = requests.get(
        url,
        params={
            "usuario": DMC_USUARIO,
            "token": DMC_TOKEN
        },
        timeout=60
    )

    respuesta.raise_for_status()

    if not respuesta.text.strip():
        return None

    try:
        datos = respuesta.json()

    except requests.exceptions.JSONDecodeError:
        return None

    registros = (
        datos
        .get("datosEstaciones", {})
        .get("datos", [])
        if isinstance(datos, dict)
        else []
    )

    return datos if registros else None


def guardar_mes_dmc(
    codigo,
    anio,
    mes,
    sobrescribir=False
):

    carpeta = RUTA_DMC / codigo
    carpeta.mkdir(
        parents=True,
        exist_ok=True
    )

    archivo = carpeta / f"{anio}-{mes:02d}.json"

    if archivo.exists() and not sobrescribir:
        return "existente"

    datos = obtener_mes_dmc(
        codigo,
        anio,
        mes
    )

    if datos is None:
        return "sin_datos"

    with open(
        archivo,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            datos,
            f,
            ensure_ascii=False,
            indent=2
        )

    return (
        "actualizado"
        if archivo.exists() and sobrescribir
        else "descargado"
    )


def ingestar_dmc_historico(
    anio_inicio=2019,
    mes_inicio=6,
    anio_fin=2025,
    mes_fin=5
):

    logger.info(
        "Inicio de ingesta DMC."
    )

    total_descargados = 0
    total_existentes = 0
    total_sin_datos = 0
    total_errores = 0

    for codigo, nombre in ESTACIONES_DMC.items():

        descargados = 0
        existentes = 0
        sin_datos = 0
        errores = 0

        for anio in range(
            anio_inicio,
            anio_fin + 1
        ):

            for mes in range(1, 13):

                if (
                    anio == anio_inicio
                    and mes < mes_inicio
                ):
                    continue

                if (
                    anio == anio_fin
                    and mes > mes_fin
                ):
                    continue

                try:

                    estado = guardar_mes_dmc(
                        codigo,
                        anio,
                        mes,
                        sobrescribir=False
                    )

                    if estado == "descargado":
                        descargados += 1

                    elif estado == "existente":
                        existentes += 1

                    else:
                        sin_datos += 1

                except Exception as error:

                    errores += 1

                    logger.warning(
                        "DMC %s | %04d-%02d | %s",
                        codigo,
                        anio,
                        mes,
                        error
                    )

        total_descargados += descargados
        total_existentes += existentes
        total_sin_datos += sin_datos
        total_errores += errores

        logger.info(
            "DMC %s - %s | Descargados=%s | "
            "Existentes=%s | Sin datos=%s | Errores=%s.",
            codigo,
            nombre,
            descargados,
            existentes,
            sin_datos,
            errores
        )

    logger.info(
        "DMC finalizado | "
        "Descargados=%s | Existentes=%s | "
        "Sin datos=%s | Errores=%s.",
        total_descargados,
        total_existentes,
        total_sin_datos,
        total_errores
    )


def ingestar_dmc_actual(
    fecha_meteorologia=None
):

    if fecha_meteorologia is None:
        fecha_meteorologia = (
            date.today() - timedelta(days=1)
        )

    anio = fecha_meteorologia.year
    mes = fecha_meteorologia.month

    logger.info(
        "Inicio ingesta DMC actual | "
        "Fecha meteorológica=%s | Mes=%04d-%02d.",
        fecha_meteorologia,
        anio,
        mes
    )

    actualizados = 0
    sin_datos = 0
    errores = 0

    for codigo, nombre in ESTACIONES_DMC.items():

        try:

            estado = guardar_mes_dmc(
                codigo,
                anio,
                mes,
                sobrescribir=True
            )

            if estado in {
                "actualizado",
                "descargado"
            }:

                actualizados += 1

                logger.info(
                    "DMC actualizado | %s - %s | %04d-%02d.",
                    codigo,
                    nombre,
                    anio,
                    mes
                )

            else:

                sin_datos += 1

                logger.warning(
                    "DMC sin datos | %s - %s | %04d-%02d.",
                    codigo,
                    nombre,
                    anio,
                    mes
                )

        except Exception as error:

            errores += 1

            logger.warning(
                "DMC error | %s - %s | %04d-%02d | %s",
                codigo,
                nombre,
                anio,
                mes,
                error
            )

    logger.info(
        "DMC actual finalizado | "
        "Actualizados=%s | Sin datos=%s | Errores=%s.",
        actualizados,
        sin_datos,
        errores
    )


# =========================
# EJECUCIÓN
# =========================

def ejecutar_ingesta(
    modo="historico",
    fecha_meteorologia=None
):

    logger.info(
        "Inicio de ingesta ETL V2 "
    )

    try:

        # Estas fuentes siguen siendo necesarias
        # para el histórico y las variables territoriales.
        verificar_shapefile(
            RUTA_CONAF,
            "CONAF"
        )

        verificar_shapefile(
            RUTA_IDE,
            "IDE Chile"
        )

        if modo == "historico":

            ingestar_dmc_historico()

        elif modo == "actual":

            ingestar_dmc_actual(
                fecha_meteorologia
            )

        else:

            raise ValueError(
                "modo debe ser 'historico' o 'actual'"
            )

        logger.info(
            "Ingesta finalizada correctamente"
        )

    except Exception as error:

        logger.exception(
            "Error crítico durante la ingesta: %s",
            error
        )

        raise


if __name__ == "__main__":
    ejecutar_ingesta()