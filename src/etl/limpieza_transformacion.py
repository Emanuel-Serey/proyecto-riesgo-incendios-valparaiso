import pandas as pd

from ingesta import cargar_conaf, cargar_ide, cargar_estacion_dmc, CARPETAS_DMC, RUTA_IDE
from logger_config import obtener_logger


logger = obtener_logger("limpieza_transformacion", "limpieza_transformacion.log")


# DMC

def limpiar_humedad(df):
    df = df.copy()
    df = df.rename(columns={"CodigoNacional": "codigo_estacion", "Instante": "fecha_hora", "HR": "humedad"})
    df["fecha_hora"] = pd.to_datetime(df["fecha_hora"])
    return df


def limpiar_temperatura(df):
    df = df.copy()
    df = df.rename(columns={"CodigoNacional": "codigo_estacion", "Instante": "fecha_hora", "Ts": "temperatura"})
    df["fecha_hora"] = pd.to_datetime(df["fecha_hora"])
    return df


def limpiar_viento(df):
    df = df.copy()
    df = df.rename(columns={"CodigoNacional": "codigo_estacion", "Instante": "fecha_hora", "ff": "viento"})
    df["fecha_hora"] = pd.to_datetime(df["fecha_hora"])
    return df[["codigo_estacion", "fecha_hora", "viento"]]


def agregar_periodo_mensual(df, columna_valor):
    df = df.copy()
    df["periodo"] = df["fecha_hora"].dt.to_period("M").astype(str)
    return df.groupby(["codigo_estacion", "periodo"])[columna_valor].mean().reset_index()


def unir_variables_dmc(humedad, temperatura, viento):
    datos = temperatura.merge(humedad, on=["codigo_estacion", "periodo"], how="outer")
    return datos.merge(viento, on=["codigo_estacion", "periodo"], how="outer")


def procesar_estacion_dmc(carpeta):
    humedad, temperatura, viento = cargar_estacion_dmc(carpeta)

    humedad = agregar_periodo_mensual(limpiar_humedad(humedad), "humedad")
    temperatura = agregar_periodo_mensual(limpiar_temperatura(temperatura), "temperatura")
    viento = agregar_periodo_mensual(limpiar_viento(viento), "viento")

    datos = unir_variables_dmc(humedad, temperatura, viento)

    logger.info("Estación DMC procesada: %s | Registros mensuales: %s.", carpeta.name, len(datos))
    return datos


def procesar_dmc():
    logger.info("Inicio de limpieza y transformación DMC.")

    estaciones = [procesar_estacion_dmc(carpeta) for carpeta in CARPETAS_DMC]
    dmc = pd.concat(estaciones, ignore_index=True)
    completos = dmc.dropna(subset=["temperatura", "humedad", "viento"])

    logger.info(
        "DMC procesado: %s registros mensuales | Registros con las 3 variables completas: %s.",
        len(dmc), len(completos)
    )

    return dmc


# IDE Chile

def revisar_ide():
    ide = cargar_ide()

    print("\n--- REVISIÓN IDE CHILE ---")

    columnas = ["NOM_COM", "DES_USO_19", "DES_USO_21", "DES_USO_23"]
    print("\nColumnas seleccionadas:")
    print(ide[columnas].head(10))

    for columna in ["DES_USO_19", "DES_USO_21", "DES_USO_23"]:
        print(f"\nValores distintos de {columna}:")
        print(ide[columna].value_counts().head(20))

    logger.info("Revisión IDE realizada: %s registros | %s columnas.", len(ide), len(ide.columns))
    return ide


def simplificar_cobertura(valor):
    if pd.isna(valor):
        return None

    return str(valor).split(",")[0].strip()


def procesar_ide():
    logger.info("Inicio de transformación IDE Chile.")

    ide = cargar_ide()

    if ide.crs is None:
        raise ValueError("La capa IDE no tiene un CRS definido.")

    if ide.crs.is_geographic:
        crs_proyectado = ide.estimate_utm_crs()
        logger.info("IDE reproyectado a %s para calcular superficies.", crs_proyectado)
        ide = ide.to_crs(crs_proyectado)

    columnas_periodos = {
        "DES_USO_01": "2001",
        "DES_USO_13": "2013",
        "DES_USO_16": "2016",
        "DES_USO_17": "2017",
        "DES_USO_19": "2019",
        "DES_USO_21": "2021",
        "DES_USO_23": "2023"
    }

    registros = []

    for columna, anio in columnas_periodos.items():
        datos = ide[["NOM_COM", columna, "geometry"]].copy()
        datos = datos.rename(columns={"NOM_COM": "comuna", columna: "vegetacion_cobertura"})
        datos["anio_cobertura"] = anio
        datos["vegetacion_cobertura"] = datos["vegetacion_cobertura"].apply(simplificar_cobertura)
        datos["area"] = datos.geometry.area
        registros.append(datos)

    ide_largo = pd.concat(registros, ignore_index=True)

    logger.info("IDE transformado: %s registros | Años de cobertura: %s.", len(ide_largo), len(columnas_periodos))
    return ide_largo


def obtener_cobertura_dominante(ide_largo):
    resumen = (
        ide_largo.dropna(subset=["vegetacion_cobertura"])
        .groupby(["comuna", "anio_cobertura", "vegetacion_cobertura"], as_index=False)["area"]
        .sum()
    )

    indice = resumen.groupby(["comuna", "anio_cobertura"])["area"].idxmax()

    dominante = resumen.loc[
        indice,
        ["comuna", "anio_cobertura", "vegetacion_cobertura"]
    ].reset_index(drop=True)

    logger.info("Cobertura dominante calculada: %s registros | Comunas: %s.",
                len(dominante), dominante["comuna"].nunique())

    return dominante


# CONAF

def limpiar_fecha_conaf(serie):
    meses = {
        "ene": "Jan", "feb": "Feb", "mar": "Mar", "abr": "Apr",
        "may": "May", "jun": "Jun", "jul": "Jul", "ago": "Aug",
        "sep": "Sep", "oct": "Oct", "nov": "Nov", "dic": "Dec"
    }

    serie = serie.astype(str)

    for espanol, ingles in meses.items():
        serie = serie.str.replace(espanol, ingles, case=False, regex=False)

    return pd.to_datetime(serie, errors="coerce", dayfirst=True)


def normalizar_comuna(nombre):
    if pd.isna(nombre):
        return nombre

    equivalencias = {
        "Calera": "La Calera",
        "Llay-Llay": "Llaillay",
        "Puchuncavi": "Puchuncaví"
    }

    nombre = str(nombre).strip()
    return equivalencias.get(nombre, nombre)


def procesar_eventos_conaf():
    logger.info("Inicio de limpieza y transformación CONAF.")

    conaf = cargar_conaf()
    datos = conaf[["Comuna", "Inicio", "Lat", "Lon", "Superficie", "geometry"]].copy()

    datos = datos.rename(columns={
        "Comuna": "comuna",
        "Inicio": "fecha_incendio",
        "Lat": "latitud",
        "Lon": "longitud",
        "Superficie": "superficie"
    })

    datos["comuna"] = datos["comuna"].apply(normalizar_comuna)
    datos["fecha_incendio"] = limpiar_fecha_conaf(datos["fecha_incendio"])

    fechas_invalidas = datos["fecha_incendio"].isna().sum()

    if fechas_invalidas > 0:
        logger.warning("Registros CONAF con fecha no válida: %s.", fechas_invalidas)

    datos = datos.dropna(subset=["comuna", "fecha_incendio"])
    datos["periodo"] = datos["fecha_incendio"].dt.to_period("M")

    logger.info("CONAF procesado: %s eventos válidos | Comunas: %s.",
                len(datos), datos["comuna"].nunique())

    return datos


def construir_panel_conaf(eventos):
    ocurrencias = eventos.groupby(["comuna", "periodo"]).size().reset_index(name="ocurrencias_mes")
    comunas = sorted(eventos["comuna"].unique())

    periodos = pd.period_range(
        start=eventos["periodo"].min(),
        end=eventos["periodo"].max(),
        freq="M"
    )

    indice = pd.MultiIndex.from_product([comunas, periodos], names=["comuna", "periodo"])

    panel = indice.to_frame(index=False).merge(
        ocurrencias,
        on=["comuna", "periodo"],
        how="left"
    )

    panel["ocurrencias_mes"] = panel["ocurrencias_mes"].fillna(0).astype(int)
    panel["ocurrencia_incendio"] = (panel["ocurrencias_mes"] > 0).astype(int)
    panel = panel.sort_values(["comuna", "periodo"])

    panel["incendios_historicos"] = (
        panel.groupby("comuna")["ocurrencias_mes"]
        .transform(lambda serie: serie.shift(1).rolling(window=12, min_periods=1).sum())
        .fillna(0)
        .astype(int)
    )

    panel["periodo"] = panel["periodo"].astype(str)

    logger.info("Panel CONAF generado: %s registros | Comunas: %s | Rango: %s a %s.",
                len(panel), panel["comuna"].nunique(), panel["periodo"].min(), panel["periodo"].max())

    logger.info("Ocurrencia de incendio: 0=%s | 1=%s.",
                (panel["ocurrencia_incendio"] == 0).sum(),
                (panel["ocurrencia_incendio"] == 1).sum())

    return panel


# Ejecución directa

if __name__ == "__main__":
    try:
        logger.info("Inicio de limpieza y transformación de datos.")

        dmc = procesar_dmc()

        print("\n--- DMC PROCESADO ---")
        print(dmc.head(10))
        print("\nCantidad total:", len(dmc))
        print("\nValores nulos:")
        print(dmc.isnull().sum())

        completos = dmc.dropna(subset=["temperatura", "humedad", "viento"])

        print("\nRegistros completos:", len(completos))
        print("\nRango temporal por estación:")
        print(completos.groupby("codigo_estacion")["periodo"].agg(["min", "max", "count"]))

        ide_largo = procesar_ide()
        cobertura_dominante = obtener_cobertura_dominante(ide_largo)

        print("\n--- IDE PROCESADO ---")
        print(cobertura_dominante.head(30))
        print("\nCantidad de registros:", len(cobertura_dominante))
        print("\nCategorías:")
        print(cobertura_dominante["vegetacion_cobertura"].value_counts())

        eventos_conaf = procesar_eventos_conaf()
        panel_conaf = construir_panel_conaf(eventos_conaf)

        print("\n--- CONAF PROCESADO ---")
        print(eventos_conaf[["comuna", "fecha_incendio", "periodo"]].head(10))
        print("\nCantidad de registros:", len(panel_conaf))
        print("\nDistribución de ocurrencia:")
        print(panel_conaf["ocurrencia_incendio"].value_counts())
        print("\nRango temporal:", panel_conaf["periodo"].min(), "a", panel_conaf["periodo"].max())
        print("\nCantidad de comunas:", panel_conaf["comuna"].nunique())

        comunas_conaf = set(panel_conaf["comuna"].unique())
        comunas_ide = set(cobertura_dominante["comuna"].unique())

        print("\nComunas CONAF que no aparecen en IDE:")
        print(sorted(comunas_conaf - comunas_ide))

        print("\nComunas IDE que no aparecen en CONAF:")
        print(sorted(comunas_ide - comunas_conaf))

        logger.info("Limpieza y transformación finalizada correctamente.")

    except Exception:
        logger.exception("Error durante la limpieza y transformación de datos.")
        raise