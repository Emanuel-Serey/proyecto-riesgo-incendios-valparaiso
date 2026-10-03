from pathlib import Path
import pandas as pd
import geopandas as gpd


RUTA_CONAF = Path("data/raw/conaf/cobertura_incendios/II_FF.shp")
RUTA_IDE = Path("data/raw/ide/cobertura_vegetacion_valparaiso/cut_2001_2023_R05.shp")
RUTA_DMC = Path("data/raw/dmc")


def cargar_conaf():
    datos = gpd.read_file(RUTA_CONAF)

    print("\n--- CONAF ---")
    print(f"Registros: {len(datos)}")
    print(f"Columnas: {len(datos.columns)}")
    print(datos.columns.tolist())

    return datos


def cargar_ide():
    datos = gpd.read_file(RUTA_IDE)

    print("\n--- IDE CHILE ---")
    print(f"Registros: {len(datos)}")
    print(f"Columnas: {len(datos.columns)}")
    print(datos.columns.tolist())

    return datos


def cargar_dmc():
    archivos = sorted(RUTA_DMC.rglob("*.csv"))

    print("\n--- DMC ---")
    print(f"Archivos CSV encontrados: {len(archivos)}")

    datos_dmc = {}

    for archivo in archivos:
        datos = pd.read_csv(archivo, sep=";")

        nombre = archivo.stem
        datos_dmc[nombre] = datos

        print(f"\nArchivo: {archivo}")
        print(f"Registros: {len(datos)}")
        print(f"Columnas: {datos.columns.tolist()}")
        print(datos.head(3))

    return datos_dmc


if __name__ == "__main__":
    conaf = cargar_conaf()
    ide = cargar_ide()
    dmc = cargar_dmc()