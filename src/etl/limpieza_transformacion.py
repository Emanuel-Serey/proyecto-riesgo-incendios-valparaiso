from pathlib import Path
import json
import logging
import re
import pandas as pd
import geopandas as gpd

BASE_DIR = Path(__file__).resolve().parents[2]
RAW = BASE_DIR / "data/raw"
PROCESSED = BASE_DIR / "data/processed"
LOGS = BASE_DIR / "logs"

RUTA_DMC = RAW / "dmc/api"
RUTA_CONAF = RAW / "conaf/cobertura_incendios/II_FF.shp"
RUTA_IDE = RAW / "ide/cobertura_vegetacion_valparaiso/cut_2001_2023_R05.shp"

PROCESSED.mkdir(parents=True, exist_ok=True)
LOGS.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("limpieza_transformacion")
logger.setLevel(logging.INFO)
logger.propagate = False

if not logger.handlers:
    fmt = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    fh = logging.FileHandler(LOGS / "limpieza_transformacion.log", encoding="utf-8")
    sh = logging.StreamHandler()
    fh.setFormatter(fmt)
    sh.setFormatter(fmt)
    logger.addHandler(fh)
    logger.addHandler(sh)


# =========================
# GENERALES
# =========================

def extraer_numero(valor):
    if pd.isna(valor):
        return None
    match = re.search(r"-?\d+(?:[.,]\d+)?", str(valor))
    return float(match.group().replace(",", ".")) if match else None


def normalizar_comuna(nombre):
    if pd.isna(nombre):
        return None

    nombre = str(nombre).strip()

    cambios = {
        "Calera": "La Calera",
        "Llay-Llay": "Llaillay",
        "Puchuncavi": "Puchuncaví"
    }

    return cambios.get(nombre, nombre)


def buscar_columna(df, nombre):
    mapa = {c.lower(): c for c in df.columns}
    return mapa.get(nombre.lower())


# =========================
# DMC
# =========================

def leer_json_dmc(archivo):
    with open(archivo, "r", encoding="utf-8") as f:
        data = json.load(f)

    registros = (
        data.get("datosEstaciones", {}).get("datos", [])
        if isinstance(data, dict)
        else []
    )

    if not isinstance(registros, list) or not registros:
        return pd.DataFrame()

    df = pd.DataFrame(registros)
    df["codigo_estacion"] = archivo.parent.name
    return df


def procesar_dmc():
    logger.info("Inicio procesamiento DMC.")

    archivos = sorted(RUTA_DMC.glob("*/*.json"))
    logger.info(
        "DMC | Ruta=%s | Archivos JSON encontrados=%s.",
        RUTA_DMC,
        len(archivos)
    )

    if not archivos:
        raise ValueError("No se encontraron archivos JSON DMC.")

    dfs = []
    vacios = 0
    errores = 0

    for archivo in archivos:
        try:
            df = leer_json_dmc(archivo)

            if df.empty:
                vacios += 1
            else:
                dfs.append(df)

        except Exception as error:
            errores += 1
            logger.warning(
                "DMC | Error leyendo %s | %s",
                archivo.name,
                error
            )

    if not dfs:
        raise ValueError("No se encontraron datos DMC válidos.")

    dmc = pd.concat(dfs, ignore_index=True)

    necesarias = [
        "momento",
        "temperatura",
        "humedadRelativa",
        "fuerzaDelViento",
        "codigo_estacion"
    ]

    faltantes = [c for c in necesarias if c not in dmc.columns]

    if faltantes:
        raise ValueError(f"Faltan columnas DMC: {faltantes}")

    dmc = dmc[necesarias].copy()

    dmc["fecha_hora"] = pd.to_datetime(
        dmc["momento"],
        errors="coerce"
    )

    dmc["temperatura"] = dmc["temperatura"].apply(extraer_numero)
    dmc["humedad"] = dmc["humedadRelativa"].apply(extraer_numero)
    dmc["viento"] = dmc["fuerzaDelViento"].apply(extraer_numero)

    dmc = dmc.dropna(subset=["fecha_hora"])

    duplicados = dmc.duplicated(
        ["codigo_estacion", "fecha_hora"]
    ).sum()

    dmc = dmc.drop_duplicates(
        ["codigo_estacion", "fecha_hora"]
    )

    dmc["fecha"] = dmc["fecha_hora"].dt.normalize()

    dmc["completo"] = (
        dmc[["temperatura", "humedad", "viento"]]
        .notna()
        .all(axis=1)
        .astype(int)
    )

    diario = (
        dmc
        .groupby(["codigo_estacion", "fecha"], as_index=False)
        .agg(
            temperatura_media=("temperatura", "mean"),
            temperatura_max=("temperatura", "max"),
            humedad_media=("humedad", "mean"),
            humedad_min=("humedad", "min"),
            viento_medio=("viento", "mean"),
            viento_max=("viento", "max"),
            observaciones=("fecha_hora", "size"),
            observaciones_completas=("completo", "sum")
        )
    )

    diario["cobertura_pct"] = (
        diario["observaciones_completas"] / 96 * 100
    ).clip(upper=100)

    numericas = [
        "temperatura_media",
        "temperatura_max",
        "humedad_media",
        "humedad_min",
        "viento_medio",
        "viento_max",
        "cobertura_pct"
    ]

    diario[numericas] = diario[numericas].round(2)
    diario = diario.sort_values(["codigo_estacion", "fecha"])

    salida = PROCESSED / "meteorologia_diaria.csv"
    diario.to_csv(salida, index=False, encoding="utf-8-sig")

    logger.info(
        "DMC | Archivos=%s | Válidos=%s | Vacíos=%s | Errores=%s.",
        len(archivos),
        len(dfs),
        vacios,
        errores
    )

    logger.info(
        "DMC | Observaciones=%s | Duplicados eliminados=%s.",
        len(dmc),
        duplicados
    )

    logger.info(
        "DMC diario | Registros=%s | Días >=80%%=%s | Estaciones=%s | Rango=%s a %s.",
        len(diario),
        (diario["cobertura_pct"] >= 80).sum(),
        diario["codigo_estacion"].nunique(),
        diario["fecha"].min().date(),
        diario["fecha"].max().date()
    )

    logger.info("DMC guardado: %s", salida)
    return diario


# =========================
# CONAF
# =========================

def limpiar_fecha_conaf(serie):
    fechas = serie.astype(str).str.lower().str.strip()

    meses = {
        "ene": "jan",
        "feb": "feb",
        "mar": "mar",
        "abr": "apr",
        "may": "may",
        "jun": "jun",
        "jul": "jul",
        "ago": "aug",
        "sep": "sep",
        "oct": "oct",
        "nov": "nov",
        "dic": "dec"
    }

    for esp, eng in meses.items():
        fechas = fechas.str.replace(esp, eng, regex=False)

    return pd.to_datetime(
        fechas,
        format="mixed",
        dayfirst=True,
        errors="coerce"
    )


def procesar_conaf():
    logger.info("Inicio procesamiento CONAF.")

    conaf = gpd.read_file(RUTA_CONAF)
    total = len(conaf)

    datos = conaf[
        ["Comuna", "Inicio", "Superficie"]
    ].copy()

    datos.columns = [
        "comuna",
        "fecha_inicio",
        "superficie"
    ]

    datos["comuna"] = datos["comuna"].apply(normalizar_comuna)
    datos["fecha_inicio"] = limpiar_fecha_conaf(datos["fecha_inicio"])
    datos["superficie"] = pd.to_numeric(
        datos["superficie"],
        errors="coerce"
    )

    fechas_nulas = datos["fecha_inicio"].isna().sum()
    comunas_nulas = datos["comuna"].isna().sum()

    datos = datos.dropna(
        subset=["comuna", "fecha_inicio"]
    )

    datos["fecha"] = datos["fecha_inicio"].dt.normalize()

    diario = (
        datos
        .groupby(["comuna", "fecha"], as_index=False)
        .agg(
            cantidad_incendios=("fecha_inicio", "size"),
            superficie_afectada=("superficie", "sum")
        )
    )

    diario["ocurrencia_incendio"] = 1
    diario["superficie_afectada"] = diario["superficie_afectada"].round(4)
    diario = diario.sort_values(["comuna", "fecha"])

    salida = PROCESSED / "incendios_diarios.csv"
    diario.to_csv(salida, index=False, encoding="utf-8-sig")

    logger.info(
        "CONAF | Eventos originales=%s | Fechas nulas=%s | Comunas nulas=%s.",
        total,
        fechas_nulas,
        comunas_nulas
    )

    logger.info(
        "CONAF diario | Comuna+día positivos=%s | Comunas=%s | Rango=%s a %s.",
        len(diario),
        diario["comuna"].nunique(),
        diario["fecha"].min().date(),
        diario["fecha"].max().date()
    )

    logger.info("CONAF guardado: %s", salida)
    return diario


# =========================
# IDE CHILE
# =========================

ANIOS_IDE = {
    "DES_USO_01": 2001,
    "DES_USO_13": 2013,
    "DES_USO_16": 2016,
    "DES_USO_17": 2017,
    "DES_USO_19": 2019,
    "DES_USO_21": 2021,
    "DES_USO_23": 2023
}


def simplificar_cobertura(valor):
    if pd.isna(valor):
        return None

    valor = str(valor).strip()

    if not valor or valor.lower() in {"nan", "none"}:
        return None

    return valor.split(",")[0].strip()


def procesar_ide():
    logger.info("Inicio procesamiento IDE Chile.")

    ide = gpd.read_file(RUTA_IDE)

    col_comuna = buscar_columna(ide, "NOM_COM")

    if col_comuna is None:
        raise ValueError("IDE: no se encontró la columna NOM_COM.")

    columnas = {}

    for nombre, anio in ANIOS_IDE.items():
        real = buscar_columna(ide, nombre)

        if real is None:
            raise ValueError(
                f"IDE: no se encontró la columna {nombre}."
            )

        columnas[real] = anio

    if ide.crs is None:
        raise ValueError("IDE no posee sistema de coordenadas definido.")

    ide_metric = ide.to_crs(
        ide.estimate_utm_crs()
    )

    ide["superficie_ha"] = (
        ide_metric.geometry.area / 10000
    )

    registros = []

    for columna, anio in columnas.items():
        df = ide[
            [
                col_comuna,
                columna,
                "superficie_ha"
            ]
        ].copy()

        df.columns = [
            "comuna",
            "vegetacion_cobertura",
            "superficie_ha"
        ]

        df["comuna"] = df["comuna"].apply(normalizar_comuna)

        df["vegetacion_cobertura"] = (
            df["vegetacion_cobertura"]
            .apply(simplificar_cobertura)
        )

        df["anio_cobertura"] = anio

        df = df.dropna(
            subset=[
                "comuna",
                "vegetacion_cobertura",
                "superficie_ha"
            ]
        )

        registros.append(df)

    largo = pd.concat(
        registros,
        ignore_index=True
    )

    resumen = (
        largo
        .groupby(
            [
                "comuna",
                "anio_cobertura",
                "vegetacion_cobertura"
            ],
            as_index=False
        )["superficie_ha"]
        .sum()
    )

    totales = (
        resumen
        .groupby(
            ["comuna", "anio_cobertura"],
            as_index=False
        )["superficie_ha"]
        .sum()
        .rename(
            columns={
                "superficie_ha": "superficie_total_ha"
            }
        )
    )

    idx = (
        resumen
        .groupby(
            ["comuna", "anio_cobertura"]
        )["superficie_ha"]
        .idxmax()
    )

    dominante = (
        resumen
        .loc[idx]
        .copy()
        .rename(
            columns={
                "superficie_ha":
                "superficie_dominante_ha"
            }
        )
    )

    dominante = dominante.merge(
        totales,
        on=["comuna", "anio_cobertura"],
        how="left"
    )

    dominante["porcentaje_cobertura"] = (
        dominante["superficie_dominante_ha"]
        / dominante["superficie_total_ha"]
        * 100
    ).round(2)

    dominante = dominante[
        [
            "comuna",
            "anio_cobertura",
            "vegetacion_cobertura",
            "superficie_dominante_ha",
            "porcentaje_cobertura"
        ]
    ].sort_values(
        ["comuna", "anio_cobertura"]
    )

    salida = PROCESSED / "vegetacion_comuna.csv"

    dominante.to_csv(
        salida,
        index=False,
        encoding="utf-8-sig"
    )

    logger.info(
        "IDE | Polígonos=%s | Comunas=%s | CRS=%s.",
        len(ide),
        ide[col_comuna].nunique(),
        ide.crs
    )

    logger.info(
        "IDE procesado | Registros comuna+año=%s | Comunas=%s | Años=%s.",
        len(dominante),
        dominante["comuna"].nunique(),
        sorted(dominante["anio_cobertura"].unique())
    )

    logger.info("IDE guardado: %s", salida)
    return dominante


# =========================
# EJECUCIÓN
# =========================

def ejecutar_transformacion():
    logger.info(
        "Inicio de limpieza y transformación ETL V2."
    )

    try:
        procesar_dmc()
        procesar_conaf()
        procesar_ide()

        logger.info(
            "Limpieza y transformación finalizada correctamente."
        )

    except Exception as error:
        logger.exception(
            "Error durante limpieza y transformación: %s",
            error
        )
        raise


if __name__ == "__main__":
    ejecutar_transformacion()