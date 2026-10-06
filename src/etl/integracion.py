from pathlib import Path
import logging
import numpy as np
import pandas as pd
import geopandas as gpd

BASE_DIR = Path(__file__).resolve().parents[2]
PROCESSED = BASE_DIR / "data/processed"
RUTA_GEO = BASE_DIR / "data/raw/ide/cobertura_vegetacion_valparaiso/cut_2001_2023_R05.shp"
LOGS = BASE_DIR / "logs"
LOGS.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("integracion")
logger.setLevel(logging.INFO)
logger.propagate = False

if not logger.handlers:
    fmt = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    fh = logging.FileHandler(LOGS / "integracion.log", encoding="utf-8")
    sh = logging.StreamHandler()
    fh.setFormatter(fmt)
    sh.setFormatter(fmt)
    logger.addHandler(fh)
    logger.addHandler(sh)

FECHA_INICIO = pd.Timestamp("2019-06-02")
FECHA_FIN = pd.Timestamp("2025-05-30")
CORTE_HISTORICO = pd.Timestamp("2019-06-01")
UMBRAL_COBERTURA = 80

ESTACIONES = [
    ["320019", "San Felipe Escuela Agrícola", -32.755277, -70.706944],
    ["320041", "Viña del Mar Ad. (Torquemada)", -32.949444, -71.476110],
    ["330007", "Rodelillo, Ad.", -33.065277, -71.556388],
    ["330030", "Santo Domingo, Ad.", -33.656111, -71.613333]
]

COD_TORQUEMADA = "320041"
COD_RESPALDO = "330006"
NOMBRE_RESPALDO = "Jardín Botánico (respaldo)"

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

def cargar_datos():
    dmc = pd.read_csv(PROCESSED / "meteorologia_diaria.csv", parse_dates=["fecha"])
    conaf = pd.read_csv(PROCESSED / "incendios_diarios.csv", parse_dates=["fecha"])
    ide = pd.read_csv(PROCESSED / "vegetacion_comuna.csv")

    dmc["codigo_estacion"] = dmc["codigo_estacion"].astype(str)
    conaf["comuna"] = conaf["comuna"].apply(normalizar_comuna)
    ide["comuna"] = ide["comuna"].apply(normalizar_comuna)
    ide["anio_cobertura"] = ide["anio_cobertura"].astype(int)

    logger.info(
        "Datos cargados | DMC=%s | CONAF=%s | IDE=%s.",
        len(dmc), len(conaf), len(ide)
    )
    return dmc, conaf, ide

def asignar_estaciones(comunas):
    if not RUTA_GEO.exists():
        raise FileNotFoundError(f"No se encontró geometría comunal: {RUTA_GEO}")

    geo = gpd.read_file(RUTA_GEO)
    col_comuna = next((c for c in geo.columns if c.lower() == "nom_com"), None)

    if not col_comuna:
        raise ValueError("No se encontró la columna NOM_COM en el shapefile IDE.")

    geo = geo[[col_comuna, "geometry"]].rename(columns={col_comuna: "comuna"})
    geo["comuna"] = geo["comuna"].apply(normalizar_comuna)
    geo = geo[geo["comuna"].isin(comunas)].dissolve(by="comuna", as_index=False)

    estaciones = pd.DataFrame(
        ESTACIONES,
        columns=["codigo_estacion_principal", "nombre_estacion_principal", "latitud", "longitud"]
    )
    estaciones = gpd.GeoDataFrame(
        estaciones,
        geometry=gpd.points_from_xy(estaciones["longitud"], estaciones["latitud"]),
        crs="EPSG:4326"
    )

    crs = geo.estimate_utm_crs()
    geo = geo.to_crs(crs)
    estaciones = estaciones.to_crs(crs)
    geo["centroide"] = geo.geometry.centroid

    resultados = []

    for _, fila in geo.iterrows():
        distancias = estaciones.geometry.distance(fila["centroide"])
        idx = distancias.idxmin()
        est = estaciones.loc[idx]

        resultados.append({
            "comuna": fila["comuna"],
            "codigo_estacion_principal": est["codigo_estacion_principal"],
            "nombre_estacion_principal": est["nombre_estacion_principal"],
            "distancia_estacion_km": round(distancias.loc[idx] / 1000, 2)
        })

    asignacion = pd.DataFrame(resultados)
    asignacion.to_csv(
        PROCESSED / "asignacion_estaciones.csv",
        index=False,
        encoding="utf-8-sig"
    )

    logger.info(
        "Estaciones asignadas | Comunas=%s | Máxima distancia=%.2f km.",
        len(asignacion),
        asignacion["distancia_estacion_km"].max()
    )
    return asignacion

def construir_perfil_historico(conaf, comunas):
    hist = conaf[conaf["fecha"] < CORTE_HISTORICO].copy()

    if hist.empty:
        raise ValueError("No existen incendios anteriores al período del modelo.")

    inicio = hist["fecha"].min()
    fin = CORTE_HISTORICO - pd.Timedelta(days=1)
    anios = ((fin - inicio).days + 1) / 365.25

    perfil = (
        hist.groupby("comuna", as_index=False)["cantidad_incendios"]
        .sum()
        .rename(columns={"cantidad_incendios": "incendios_historicos_total"})
    )

    base = pd.DataFrame({"comuna": comunas})
    perfil = base.merge(perfil, on="comuna", how="left")
    perfil["incendios_historicos_total"] = perfil["incendios_historicos_total"].fillna(0)
    perfil["incendios_historicos"] = (
        perfil["incendios_historicos_total"] / anios
    ).round(2)

    perfil.to_csv(
        PROCESSED / "perfil_incendios_historicos.csv",
        index=False,
        encoding="utf-8-sig"
    )

    logger.info(
        "Perfil histórico | Rango=%s a %s | %.2f años | Comunas=%s.",
        inicio.date(), fin.date(), anios, len(perfil)
    )
    return perfil

def construir_panel(comunas, conaf):
    fechas = pd.date_range(FECHA_INICIO, FECHA_FIN, freq="D")

    panel = (
        pd.MultiIndex.from_product(
            [comunas, fechas],
            names=["comuna", "fecha_objetivo"]
        )
        .to_frame(index=False)
    )

    incendios = conaf.rename(columns={"fecha": "fecha_objetivo"})
    panel = panel.merge(
        incendios[
            [
                "comuna",
                "fecha_objetivo",
                "cantidad_incendios",
                "superficie_afectada",
                "ocurrencia_incendio"
            ]
        ],
        on=["comuna", "fecha_objetivo"],
        how="left"
    )

    panel["cantidad_incendios"] = panel["cantidad_incendios"].fillna(0).astype(int)
    panel["superficie_afectada"] = panel["superficie_afectada"].fillna(0)
    panel["ocurrencia_incendio"] = panel["ocurrencia_incendio"].fillna(0).astype(int)

    logger.info(
        "Panel diario | Registros=%s | Comunas=%s | Rango=%s a %s | Positivos=%s.",
        len(panel),
        len(comunas),
        FECHA_INICIO.date(),
        FECHA_FIN.date(),
        panel["ocurrencia_incendio"].sum()
    )
    return panel

def agregar_vegetacion(panel, ide):
    panel = panel.copy()
    panel["anio"] = panel["fecha_objetivo"].dt.year

    anios_ide = sorted(ide["anio_cobertura"].unique())
    mapa = {
        anio: max([x for x in anios_ide if x <= anio], default=np.nan)
        for anio in panel["anio"].unique()
    }

    panel["anio_cobertura"] = panel["anio"].map(mapa)
    panel = panel.merge(
        ide,
        on=["comuna", "anio_cobertura"],
        how="left"
    )

    logger.info(
        "IDE integrado | Coberturas nulas=%s.",
        panel["vegetacion_cobertura"].isna().sum()
    )
    return panel

def agregar_meteorologia(panel, dmc):
    vars_meteo = [
        "temperatura_media", "temperatura_max",
        "humedad_media", "humedad_min",
        "viento_medio", "viento_max",
        "observaciones", "observaciones_completas",
        "cobertura_pct"
    ]

    principal = dmc.copy()
    principal["fecha_objetivo"] = principal["fecha"] + pd.Timedelta(days=1)
    principal = principal.rename(columns={"codigo_estacion": "codigo_estacion_principal"})

    panel = panel.merge(
        principal[["codigo_estacion_principal", "fecha_objetivo", *vars_meteo]],
        on=["codigo_estacion_principal", "fecha_objetivo"],
        how="left"
    )

    backup = dmc[dmc["codigo_estacion"] == COD_RESPALDO].copy()
    backup["fecha_objetivo"] = backup["fecha"] + pd.Timedelta(days=1)
    backup = backup[["fecha_objetivo", *vars_meteo]].rename(
        columns={c: f"{c}_backup" for c in vars_meteo}
    )
    panel = panel.merge(backup, on="fecha_objetivo", how="left")

    valida_principal = (
        panel["cobertura_pct"].ge(UMBRAL_COBERTURA)
        & panel["temperatura_media"].notna()
        & panel["humedad_media"].notna()
        & panel["viento_medio"].notna()
    )

    valida_backup = (
        panel["cobertura_pct_backup"].ge(UMBRAL_COBERTURA)
        & panel["temperatura_media_backup"].notna()
        & panel["humedad_media_backup"].notna()
        & panel["viento_medio_backup"].notna()
    )

    usar_backup = (
        panel["codigo_estacion_principal"].eq(COD_TORQUEMADA)
        & ~valida_principal
        & valida_backup
    )

    for col in vars_meteo:
        panel.loc[usar_backup, col] = panel.loc[usar_backup, f"{col}_backup"]

    panel["uso_respaldo"] = usar_backup
    panel["codigo_estacion_usada"] = panel["codigo_estacion_principal"]
    panel["nombre_estacion_usada"] = panel["nombre_estacion_principal"]

    panel.loc[usar_backup, "codigo_estacion_usada"] = COD_RESPALDO
    panel.loc[usar_backup, "nombre_estacion_usada"] = NOMBRE_RESPALDO

    panel["meteo_valida"] = (
        panel["cobertura_pct"].ge(UMBRAL_COBERTURA)
        & panel["temperatura_media"].notna()
        & panel["humedad_media"].notna()
        & panel["viento_medio"].notna()
    )

    panel["fecha_meteorologica"] = (
        panel["fecha_objetivo"] - pd.Timedelta(days=1)
    )

    panel = panel.drop(
        columns=[f"{c}_backup" for c in vars_meteo]
    )

    logger.info(
        "DMC integrado | Filas con respaldo=%s | Filas meteorológicas inválidas=%s.",
        panel["uso_respaldo"].sum(),
        (~panel["meteo_valida"]).sum()
    )
    return panel

def integrar():
    logger.info("Inicio de integración ETL V2.")
    dmc, conaf, ide = cargar_datos()

    comunas = sorted(ide["comuna"].dropna().unique())
    if len(comunas) != 36:
        logger.warning("Se esperaban 36 comunas y se encontraron %s.", len(comunas))

    asignacion = asignar_estaciones(comunas)
    perfil = construir_perfil_historico(conaf, comunas)
    panel = construir_panel(comunas, conaf)

    panel = panel.merge(asignacion, on="comuna", how="left")
    panel = panel.merge(
        perfil[["comuna", "incendios_historicos"]],
        on="comuna",
        how="left"
    )

    panel = agregar_vegetacion(panel, ide)
    panel = agregar_meteorologia(panel, dmc)

    panel.to_csv(
        PROCESSED / "panel_diario_integrado.csv",
        index=False,
        encoding="utf-8-sig"
    )

    dataset = panel[
        panel["meteo_valida"]
        & panel["vegetacion_cobertura"].notna()
        & panel["incendios_historicos"].notna()
    ].copy()

    columnas = [
        "comuna",
        "fecha_objetivo",
        "fecha_meteorologica",
        "codigo_estacion_principal",
        "codigo_estacion_usada",
        "nombre_estacion_usada",
        "uso_respaldo",
        "distancia_estacion_km",
        "temperatura_media",
        "temperatura_max",
        "humedad_media",
        "humedad_min",
        "viento_medio",
        "viento_max",
        "cobertura_pct",
        "vegetacion_cobertura",
        "anio_cobertura",
        "incendios_historicos",
        "cantidad_incendios",
        "superficie_afectada",
        "ocurrencia_incendio"
    ]

    dataset = dataset[columnas].sort_values(["fecha_objetivo", "comuna"])
    dataset.to_csv(
        PROCESSED / "dataset_modelo_diario.csv",
        index=False,
        encoding="utf-8-sig"
    )

    logger.info(
        "Dataset final | Registros=%s | Comunas=%s | Positivos=%s | Respaldo=%s.",
        len(dataset),
        dataset["comuna"].nunique(),
        dataset["ocurrencia_incendio"].sum(),
        dataset["uso_respaldo"].sum()
    )
    logger.info(
        "Rango final=%s a %s.",
        dataset["fecha_objetivo"].min().date(),
        dataset["fecha_objetivo"].max().date()
    )
    logger.info("Integración finalizada correctamente.")
    return dataset

if __name__ == "__main__":
    integrar()