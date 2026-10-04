from pathlib import Path
import pandas as pd
import geopandas as gpd


RUTA_DMC = Path("data/raw/dmc")
RUTA_IDE = Path("data/raw/ide/cobertura_vegetacion_valparaiso/cut_2001_2023_R05.shp")
RUTA_CONAF = Path("data/raw/conaf/cobertura_incendios/II_FF.shp")

# DMC
def limpiar_humedad(df):
    df = df.copy()

    df = df.rename(columns={
        "CodigoNacional": "codigo_estacion",
        "Instante": "fecha_hora",
        "HR": "humedad"
    })

    df["fecha_hora"] = pd.to_datetime(df["fecha_hora"])

    return df


def limpiar_temperatura(df):
    df = df.copy()

    df = df.rename(columns={
        "CodigoNacional": "codigo_estacion",
        "Instante": "fecha_hora",
        "Ts": "temperatura"
    })

    df["fecha_hora"] = pd.to_datetime(df["fecha_hora"])

    return df


def limpiar_viento(df):
    df = df.copy()

    df = df.rename(columns={
        "CodigoNacional": "codigo_estacion",
        "Instante": "fecha_hora",
        "ff": "viento"
    })

    df["fecha_hora"] = pd.to_datetime(df["fecha_hora"])

    return df[
        ["codigo_estacion", "fecha_hora", "viento"]
    ]


def agregar_periodo_mensual(df, columna_valor):
    df = df.copy()

    df["periodo"] = (
        df["fecha_hora"]
        .dt.to_period("M")
        .astype(str)
    )

    df_mensual = (
        df.groupby(
            ["codigo_estacion", "periodo"]
        )[columna_valor]
        .mean()
        .reset_index()
    )

    return df_mensual


def unir_variables_dmc(humedad, temperatura, viento):

    datos = temperatura.merge(
        humedad,
        on=["codigo_estacion", "periodo"],
        how="outer"
    )

    datos = datos.merge(
        viento,
        on=["codigo_estacion", "periodo"],
        how="outer"
    )

    return datos


def procesar_estacion_dmc(carpeta_estacion):

    carpeta = Path(carpeta_estacion)

    archivo_humedad = next(
        carpeta.glob("*Humedad*.csv")
    )

    archivo_temperatura = next(
        carpeta.glob("*Temperatura*.csv")
    )

    archivo_viento = next(
        carpeta.glob("*Viento*.csv")
    )

    humedad = pd.read_csv(
        archivo_humedad,
        sep=";"
    )

    temperatura = pd.read_csv(
        archivo_temperatura,
        sep=";"
    )

    viento = pd.read_csv(
        archivo_viento,
        sep=";"
    )

    humedad = limpiar_humedad(humedad)

    temperatura = limpiar_temperatura(
        temperatura
    )

    viento = limpiar_viento(viento)

    humedad = agregar_periodo_mensual(
        humedad,
        "humedad"
    )

    temperatura = agregar_periodo_mensual(
        temperatura,
        "temperatura"
    )

    viento = agregar_periodo_mensual(
        viento,
        "viento"
    )

    datos = unir_variables_dmc(
        humedad,
        temperatura,
        viento
    )

    return datos


def procesar_dmc():

    carpetas = [
        RUTA_DMC / "320019_san_felipe",
        RUTA_DMC / "320041_torquemada",
        RUTA_DMC / "330007_rodelillo",
        RUTA_DMC / "330030_santo_domingo"
    ]

    estaciones = []

    for carpeta in carpetas:

        datos = procesar_estacion_dmc(
            carpeta
        )

        estaciones.append(datos)

    dmc = pd.concat(
        estaciones,
        ignore_index=True
    )

    return dmc

# IDE CHILE
def revisar_ide():

    ide = gpd.read_file(RUTA_IDE)

    print("\n--- REVISIÓN IDE CHILE ---")

    columnas_relevantes = [
        "NOM_COM",
        "DES_USO_19",
        "DES_USO_21",
        "DES_USO_23"
    ]

    print("\nColumnas seleccionadas:")
    print(ide[columnas_relevantes].head(10))

    for columna in [
        "DES_USO_19",
        "DES_USO_21",
        "DES_USO_23"
    ]:
        print(f"\nValores distintos de {columna}:")
        print(ide[columna].value_counts().head(20))

    return ide

def simplificar_cobertura(valor):

    if pd.isna(valor):
        return None

    # Nos quedamos con la categoría general
    categoria = str(valor).split(",")[0].strip()

    return categoria


def procesar_ide():

    ide = gpd.read_file(RUTA_IDE)

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

        datos = ide[
            ["NOM_COM", columna, "geometry"]
        ].copy()

        datos = datos.rename(columns={
            "NOM_COM": "comuna",
            columna: "vegetacion_cobertura"
        })

        datos["anio_cobertura"] = anio

        datos["vegetacion_cobertura"] = (
            datos["vegetacion_cobertura"]
            .apply(simplificar_cobertura)
        )

        # Calculamos superficie real de cada polígono
        datos["area"] = datos.geometry.area

        registros.append(datos)

    ide_largo = pd.concat(
        registros,
        ignore_index=True
    )

    return ide_largo

def obtener_cobertura_dominante(ide_largo):

    resumen = (
        ide_largo
        .dropna(subset=["vegetacion_cobertura"])
        .groupby(
            [
                "comuna",
                "anio_cobertura",
                "vegetacion_cobertura"
            ],
            as_index=False
        )["area"]
        .sum()
    )

    indice = (
        resumen
        .groupby(
            ["comuna", "anio_cobertura"]
        )["area"]
        .idxmax()
    )

    dominante = resumen.loc[indice].copy()

    dominante = dominante[
        [
            "comuna",
            "anio_cobertura",
            "vegetacion_cobertura"
        ]
    ]

    dominante = dominante.reset_index(drop=True)

    return dominante

# CONAF
def limpiar_fecha_conaf(serie):

    meses = {
        "ene": "Jan",
        "feb": "Feb",
        "mar": "Mar",
        "abr": "Apr",
        "may": "May",
        "jun": "Jun",
        "jul": "Jul",
        "ago": "Aug",
        "sep": "Sep",
        "oct": "Oct",
        "nov": "Nov",
        "dic": "Dec"
    }

    serie = serie.astype(str)

    for espanol, ingles in meses.items():
        serie = serie.str.replace(
            espanol,
            ingles,
            case=False,
            regex=False
        )

    return pd.to_datetime(
        serie,
        errors="coerce",
        dayfirst=True
    )

def normalizar_comuna(nombre):

    if pd.isna(nombre):
        return nombre

    nombre = str(nombre).strip()

    equivalencias = {
        "Calera": "La Calera",
        "Llay-Llay": "Llaillay",
        "Puchuncavi": "Puchuncaví"
    }

    return equivalencias.get(nombre, nombre)

def procesar_eventos_conaf():

    conaf = gpd.read_file(RUTA_CONAF)

    datos = conaf[
        [
            "Comuna",
            "Inicio",
            "Lat",
            "Lon",
            "Superficie",
            "geometry"
        ]
    ].copy()

    datos = datos.rename(columns={
        "Comuna": "comuna",
        "Inicio": "fecha_incendio",
        "Lat": "latitud",
        "Lon": "longitud",
        "Superficie": "superficie"
    })

    datos["comuna"] = (
        datos["comuna"]
        .apply(normalizar_comuna)
    )

    datos["fecha_incendio"] = limpiar_fecha_conaf(
        datos["fecha_incendio"]
    )

    datos = datos.dropna(subset=["comuna","fecha_incendio"])

    datos["periodo"] = (datos["fecha_incendio"].dt.to_period("M"))

    return datos


def construir_panel_conaf(eventos):

    # Cantidad de incendios registrados
    # en cada comuna y mes
    ocurrencias = (eventos.groupby(["comuna", "periodo"]).size().reset_index(name="ocurrencias_mes"))

    # Todas las comunas disponibles en CONAF
    comunas = sorted(eventos["comuna"].unique())

    # Todos los meses existentes en la fuente
    periodo_minimo = eventos["periodo"].min()
    periodo_maximo = eventos["periodo"].max()

    periodos = pd.period_range(
        start=periodo_minimo,
        end=periodo_maximo,
        freq="M"
    )

    # Creamos todas las combinaciones:
    # comuna x mes
    indice = pd.MultiIndex.from_product(
        [
            comunas,
            periodos
        ],
        names=[
            "comuna",
            "periodo"
        ]
    )

    panel = (
        indice
        .to_frame(index=False)
        .merge(
            ocurrencias,
            on=[
                "comuna",
                "periodo"
            ],
            how="left"
        )
    )

    # Si no apareció un incendio en ese mes,
    # entonces hubo 0 ocurrencias
    panel["ocurrencias_mes"] = (panel["ocurrencias_mes"].fillna(0).astype(int))

    # Target binario
    # Ocurrencia binaria de incendio
    panel["ocurrencia_incendio"] = (panel["ocurrencias_mes"] > 0).astype(int)

    panel = panel.sort_values(
        [
            "comuna",
            "periodo"
        ]
    )

    # Incendios de los 12 meses PREVIOS.
    # shift(1) evita usar incendios del mes objetivo.
    panel["incendios_historicos"] = (
        panel
        .groupby("comuna")[
            "ocurrencias_mes"
        ]
        .transform(
            lambda serie:
            serie
            .shift(1)
            .rolling(
                window=12,
                min_periods=1
            )
            .sum()
        )
        .fillna(0)
        .astype(int)
    )

    panel["periodo"] = (panel["periodo"].astype(str))

    return panel

if __name__ == "__main__":

    # =========================
    # PROCESAMIENTO DMC
    # =========================

    dmc = procesar_dmc()

    print("\n--- DMC PROCESADO ---")

    print("\nPrimeros registros:")
    print(dmc.head(10))

    print("\nCantidad total de registros:")
    print(len(dmc))

    print("\nValores nulos:")
    print(dmc.isnull().sum())

    completos = dmc.dropna(
        subset=[
            "temperatura",
            "humedad",
            "viento"
        ]
    )

    print("\nCantidad de registros completos:")
    print(len(completos))

    print("\nRango temporal por estación:")

    resumen_dmc = (
        completos
        .groupby("codigo_estacion")["periodo"]
        .agg(["min", "max", "count"])
    )

    print(resumen_dmc)


    # =========================
    # PROCESAMIENTO IDE CHILE
    # =========================

    ide_largo = procesar_ide()

    cobertura_dominante = obtener_cobertura_dominante(
        ide_largo
    )

    print("\n--- IDE PROCESADO ---")

    print("\nPrimeros registros:")
    print(cobertura_dominante.head(30))

    print("\nCantidad de registros:")
    print(len(cobertura_dominante))

    print("\nCategorías de cobertura:")

    print(
        cobertura_dominante[
            "vegetacion_cobertura"
        ].value_counts()
    )

        # =========================
    # PROCESAMIENTO CONAF
    # =========================

    eventos_conaf = procesar_eventos_conaf()

    panel_conaf = construir_panel_conaf(
        eventos_conaf
    )

    print("\n--- CONAF PROCESADO ---")

    print("\nPrimeros eventos:")
    print(
        eventos_conaf[
            [
                "comuna",
                "fecha_incendio",
                "periodo"
            ]
        ].head(10)
    )

    print("\nPanel mensual:")
    print(panel_conaf.head(30))

    print("\nCantidad de registros:")
    print(len(panel_conaf))

    print("\nDistribución del target:")
    print(
        panel_conaf[
            "target"
        ].value_counts()
    )

    print("\nRango temporal:")
    print(
        panel_conaf["periodo"].min(),
        "a",
        panel_conaf["periodo"].max()
    )

    print("\nCantidad de comunas:")
    print(
        panel_conaf["comuna"].nunique()
    )

    comunas_conaf = set(
    panel_conaf["comuna"].unique()
    )

    comunas_ide = set(
        cobertura_dominante["comuna"].unique()
    )

    print("\nComunas CONAF que no aparecen en IDE:")
    print(sorted(comunas_conaf - comunas_ide))

    print("\nComunas IDE que no aparecen en CONAF:")
    print(sorted(comunas_ide - comunas_conaf))