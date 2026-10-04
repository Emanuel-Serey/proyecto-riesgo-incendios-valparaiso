from pathlib import Path
import pandas as pd
import geopandas as gpd

from logger_config import obtener_logger


logger = obtener_logger("ingesta", "ingesta.log")

RUTA_CONAF = Path("data/raw/conaf/cobertura_incendios/II_FF.shp")
RUTA_IDE = Path("data/raw/ide/cobertura_vegetacion_valparaiso/cut_2001_2023_R05.shp")
RUTA_DMC = Path("data/raw/dmc")


def cargar_conaf():
    try:
        datos = gpd.read_file(RUTA_CONAF)

        print("\n--- CONAF ---")
        print(f"Registros: {len(datos)}")
        print(f"Columnas: {len(datos.columns)}")
        print(datos.columns.tolist())

        logger.info(f"CONAF cargado correctamente: {len(datos)} registros y {len(datos.columns)} columnas.")
        return datos

    except Exception:
        logger.exception("Error durante la ingesta de CONAF.")
        raise


def cargar_ide():
    try:
        datos = gpd.read_file(RUTA_IDE)

        print("\n--- IDE CHILE ---")
        print(f"Registros: {len(datos)}")
        print(f"Columnas: {len(datos.columns)}")
        print(datos.columns.tolist())

        logger.info(f"IDE Chile cargado correctamente: {len(datos)} registros y {len(datos.columns)} columnas.")
        return datos

    except Exception:
        logger.exception("Error durante la ingesta de IDE Chile.")
        raise


def cargar_dmc():
    try:
        archivos = sorted(RUTA_DMC.rglob("*.csv"))

        print("\n--- DMC ---")
        print(f"Archivos CSV encontrados: {len(archivos)}")

        logger.info(f"Archivos DMC encontrados: {len(archivos)}.")

        datos_dmc = {}

        for archivo in archivos:
            datos = pd.read_csv(archivo, sep=";")
            datos_dmc[archivo.stem] = datos

            print(f"\nArchivo: {archivo}")
            print(f"Registros: {len(datos)}")
            print(f"Columnas: {datos.columns.tolist()}")
            print(datos.head(3))

            logger.info(f"DMC cargado: {archivo.name} - {len(datos)} registros.")

        logger.info(f"Ingesta DMC finalizada correctamente: {len(datos_dmc)} archivos procesados.")
        return datos_dmc

    except Exception:
        logger.exception("Error durante la ingesta de DMC.")
        raise


if __name__ == "__main__":
    try:
        logger.info("Inicio de ingesta de datos.")
        conaf = cargar_conaf()
        ide = cargar_ide()
        dmc = cargar_dmc()
        logger.info("Ingesta de datos finalizada correctamente.")

    except Exception:
        logger.exception("La ejecución de ingesta finalizó con errores.")
        raise