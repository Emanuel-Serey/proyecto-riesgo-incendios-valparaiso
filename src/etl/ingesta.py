from pathlib import Path
import pandas as pd
import geopandas as gpd

from logger_config import obtener_logger


logger = obtener_logger("ingesta", "ingesta.log")

RUTA_CONAF = Path("data/raw/conaf/cobertura_incendios/II_FF.shp")
RUTA_IDE = Path("data/raw/ide/cobertura_vegetacion_valparaiso/cut_2001_2023_R05.shp")
RUTA_DMC = Path("data/raw/dmc")

CARPETAS_DMC = [
    RUTA_DMC / "320019_san_felipe",
    RUTA_DMC / "320041_torquemada",
    RUTA_DMC / "330007_rodelillo",
    RUTA_DMC / "330030_santo_domingo"
]


def cargar_conaf():
    try:
        datos = gpd.read_file(RUTA_CONAF)
        logger.info("CONAF cargado correctamente: %s registros | %s columnas.", len(datos), len(datos.columns))
        return datos
    except Exception:
        logger.exception("Error durante la ingesta de CONAF.")
        raise


def cargar_ide():
    try:
        datos = gpd.read_file(RUTA_IDE)
        logger.info("IDE Chile cargado correctamente: %s registros | %s columnas.", len(datos), len(datos.columns))
        return datos
    except Exception:
        logger.exception("Error durante la ingesta de IDE Chile.")
        raise


def cargar_estacion_dmc(carpeta_estacion):
    try:
        carpeta = Path(carpeta_estacion)

        archivo_humedad = next(carpeta.glob("*Humedad*.csv"))
        archivo_temperatura = next(carpeta.glob("*Temperatura*.csv"))
        archivo_viento = next(carpeta.glob("*Viento*.csv"))

        humedad = pd.read_csv(archivo_humedad, sep=";")
        temperatura = pd.read_csv(archivo_temperatura, sep=";")
        viento = pd.read_csv(archivo_viento, sep=";")

        logger.info(
            "DMC cargado: %s | Humedad=%s | Temperatura=%s | Viento=%s registros.",
            carpeta.name, len(humedad), len(temperatura), len(viento)
        )

        return humedad, temperatura, viento

    except Exception:
        logger.exception("Error durante la ingesta DMC de %s.", carpeta_estacion)
        raise


if __name__ == "__main__":
    try:
        logger.info("Inicio de ingesta de datos.")

        conaf = cargar_conaf()
        ide = cargar_ide()

        for carpeta in CARPETAS_DMC:
            cargar_estacion_dmc(carpeta)

        print("\nIngesta finalizada correctamente.")
        print("CONAF:", len(conaf), "registros")
        print("IDE:", len(ide), "registros")
        print("Estaciones DMC:", len(CARPETAS_DMC))

        logger.info("Ingesta de datos finalizada correctamente.")

    except Exception:
        logger.exception("La ejecución de ingesta finalizó con errores.")
        raise