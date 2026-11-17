from pathlib import Path
import logging

import numpy as np
import pandas as pd

from postgis import obtener_asignacion_estaciones_postgis


# ============================================================
# CONFIGURACIÓN
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]

PROCESSED = BASE_DIR / "data/processed"

LOGS = BASE_DIR / "logs"
LOGS.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("integracion")
logger.setLevel(logging.INFO)
logger.propagate = False

if not logger.handlers:
    fmt = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s"
    )

    fh = logging.FileHandler(
        LOGS / "integracion.log",
        encoding="utf-8",
    )

    sh = logging.StreamHandler()

    fh.setFormatter(fmt)
    sh.setFormatter(fmt)

    logger.addHandler(fh)
    logger.addHandler(sh)


# ============================================================
# PARÁMETROS
# ============================================================

FECHA_INICIO = pd.Timestamp("2019-06-02")
FECHA_FIN = pd.Timestamp("2025-05-30")
CORTE_HISTORICO = pd.Timestamp("2019-06-01")

UMBRAL_COBERTURA = 80

COD_TORQUEMADA = "320041"
COD_RESPALDO = "330006"

NOMBRE_RESPALDO = "Jardín Botánico (respaldo)"


# ============================================================
# NORMALIZACIÓN
# ============================================================

def normalizar_comuna(nombre):

    if pd.isna(nombre):
        return None

    nombre = str(nombre).strip()

    cambios = {
        "Calera": "La Calera",
        "Llay-Llay": "Llaillay",
        "Puchuncavi": "Puchuncaví",
    }

    return cambios.get(
        nombre,
        nombre,
    )


# ============================================================
# CARGA HISTÓRICA
# ============================================================

def cargar_datos():

    dmc = pd.read_csv(
        PROCESSED / "meteorologia_diaria.csv",
        parse_dates=["fecha"],
    )

    conaf = pd.read_csv(
        PROCESSED / "incendios_diarios.csv",
        parse_dates=["fecha"],
    )

    ide = pd.read_csv(
        PROCESSED / "vegetacion_comuna.csv"
    )

    dmc["codigo_estacion"] = (
        dmc["codigo_estacion"]
        .astype(str)
    )

    conaf["comuna"] = (
        conaf["comuna"]
        .apply(normalizar_comuna)
    )

    ide["comuna"] = (
        ide["comuna"]
        .apply(normalizar_comuna)
    )

    ide["anio_cobertura"] = (
        ide["anio_cobertura"]
        .astype(int)
    )

    logger.info(
        "Datos cargados | DMC=%s | CONAF=%s | IDE=%s.",
        len(dmc),
        len(conaf),
        len(ide),
    )

    return dmc, conaf, ide


# ============================================================
# ASIGNACIÓN ESPACIAL POSTGIS
# ============================================================

def asignar_estaciones(comunas):

    asignacion = (
        obtener_asignacion_estaciones_postgis()
    )

    asignacion["comuna"] = (
        asignacion["comuna"]
        .apply(normalizar_comuna)
    )

    asignacion = asignacion[
        asignacion["comuna"].isin(comunas)
    ].copy()

    if len(asignacion) != len(comunas):

        faltantes = sorted(
            set(comunas)
            - set(
                asignacion["comuna"]
            )
        )

        raise ValueError(
            "PostGIS no pudo asignar estación "
            f"a todas las comunas. Faltantes: {faltantes}"
        )

    if (
        asignacion[
            "codigo_estacion_principal"
        ]
        .eq(COD_RESPALDO)
        .any()
    ):
        raise RuntimeError(
            "Jardín Botánico fue asignado "
            "incorrectamente como estación principal."
        )

    asignacion.to_csv(
        PROCESSED / "asignacion_estaciones.csv",
        index=False,
        encoding="utf-8-sig",
    )

    logger.info(
        "Estaciones asignadas mediante PostGIS | "
        "Comunas=%s | Máxima distancia=%.2f km.",
        len(asignacion),
        asignacion[
            "distancia_estacion_km"
        ].max(),
    )

    return asignacion


# ============================================================
# PERFIL HISTÓRICO
# ============================================================

def construir_perfil_historico(
    conaf,
    comunas,
):

    hist = conaf[
        conaf["fecha"] < CORTE_HISTORICO
    ].copy()

    if hist.empty:
        raise ValueError(
            "No existen incendios anteriores "
            "al período del modelo."
        )

    inicio = hist["fecha"].min()

    fin = (
        CORTE_HISTORICO
        - pd.Timedelta(days=1)
    )

    anios = (
        ((fin - inicio).days + 1)
        / 365.25
    )

    perfil = (
        hist
        .groupby(
            "comuna",
            as_index=False,
        )["cantidad_incendios"]
        .sum()
        .rename(
            columns={
                "cantidad_incendios":
                    "incendios_historicos_total"
            }
        )
    )

    base = pd.DataFrame(
        {
            "comuna": comunas
        }
    )

    perfil = base.merge(
        perfil,
        on="comuna",
        how="left",
    )

    perfil[
        "incendios_historicos_total"
    ] = (
        perfil[
            "incendios_historicos_total"
        ]
        .fillna(0)
    )

    perfil[
        "incendios_historicos"
    ] = (
        perfil[
            "incendios_historicos_total"
        ]
        / anios
    ).round(2)

    perfil.to_csv(
        PROCESSED
        / "perfil_incendios_historicos.csv",
        index=False,
        encoding="utf-8-sig",
    )

    logger.info(
        "Perfil histórico | "
        "Rango=%s a %s | %.2f años | Comunas=%s.",
        inicio.date(),
        fin.date(),
        anios,
        len(perfil),
    )

    return perfil


# ============================================================
# PANEL HISTÓRICO
# ============================================================

def construir_panel(
    comunas,
    conaf,
):

    fechas = pd.date_range(
        FECHA_INICIO,
        FECHA_FIN,
        freq="D",
    )

    panel = (
        pd.MultiIndex
        .from_product(
            [
                comunas,
                fechas,
            ],
            names=[
                "comuna",
                "fecha_objetivo",
            ],
        )
        .to_frame(index=False)
    )

    incendios = conaf.rename(
        columns={
            "fecha": "fecha_objetivo"
        }
    )

    panel = panel.merge(
        incendios[
            [
                "comuna",
                "fecha_objetivo",
                "cantidad_incendios",
                "superficie_afectada",
                "ocurrencia_incendio",
            ]
        ],
        on=[
            "comuna",
            "fecha_objetivo",
        ],
        how="left",
    )

    panel[
        "cantidad_incendios"
    ] = (
        panel[
            "cantidad_incendios"
        ]
        .fillna(0)
        .astype(int)
    )

    panel[
        "superficie_afectada"
    ] = (
        panel[
            "superficie_afectada"
        ]
        .fillna(0)
    )

    panel[
        "ocurrencia_incendio"
    ] = (
        panel[
            "ocurrencia_incendio"
        ]
        .fillna(0)
        .astype(int)
    )

    logger.info(
        "Panel diario | "
        "Registros=%s | Comunas=%s | "
        "Rango=%s a %s | Positivos=%s.",
        len(panel),
        len(comunas),
        FECHA_INICIO.date(),
        FECHA_FIN.date(),
        panel[
            "ocurrencia_incendio"
        ].sum(),
    )

    return panel


# ============================================================
# VEGETACIÓN HISTÓRICA
# ============================================================

def agregar_vegetacion(
    panel,
    ide,
):

    panel = panel.copy()

    panel["anio"] = (
        panel[
            "fecha_objetivo"
        ]
        .dt.year
    )

    anios_ide = sorted(
        ide[
            "anio_cobertura"
        ].unique()
    )

    mapa = {
        anio: max(
            [
                x
                for x in anios_ide
                if x <= anio
            ],
            default=np.nan,
        )
        for anio
        in panel["anio"].unique()
    }

    panel[
        "anio_cobertura"
    ] = (
        panel["anio"]
        .map(mapa)
    )

    panel = panel.merge(
        ide,
        on=[
            "comuna",
            "anio_cobertura",
        ],
        how="left",
    )

    logger.info(
        "IDE integrado | "
        "Coberturas nulas=%s.",
        panel[
            "vegetacion_cobertura"
        ].isna().sum(),
    )

    return panel


# ============================================================
# METEOROLOGÍA HISTÓRICA
# ============================================================

def agregar_meteorologia(
    panel,
    dmc,
):

    vars_meteo = [
        "temperatura_media",
        "temperatura_max",
        "humedad_media",
        "humedad_min",
        "viento_medio",
        "viento_max",
        "observaciones",
        "observaciones_completas",
        "cobertura_pct",
    ]

    # --------------------------------------------------------
    # ESTACIÓN PRINCIPAL
    # --------------------------------------------------------

    principal = dmc.copy()

    principal[
        "fecha_objetivo"
    ] = (
        principal["fecha"]
        + pd.Timedelta(days=1)
    )

    principal = principal.rename(
        columns={
            "codigo_estacion":
                "codigo_estacion_principal"
        }
    )

    panel = panel.merge(
        principal[
            [
                "codigo_estacion_principal",
                "fecha_objetivo",
                *vars_meteo,
            ]
        ],
        on=[
            "codigo_estacion_principal",
            "fecha_objetivo",
        ],
        how="left",
    )

    # --------------------------------------------------------
    # RESPALDO JARDÍN BOTÁNICO
    # --------------------------------------------------------

    backup = dmc[
        dmc[
            "codigo_estacion"
        ].eq(
            COD_RESPALDO
        )
    ].copy()

    backup[
        "fecha_objetivo"
    ] = (
        backup["fecha"]
        + pd.Timedelta(days=1)
    )

    backup = backup[
        [
            "fecha_objetivo",
            *vars_meteo,
        ]
    ].rename(
        columns={
            columna:
                f"{columna}_backup"
            for columna
            in vars_meteo
        }
    )

    panel = panel.merge(
        backup,
        on="fecha_objetivo",
        how="left",
    )

    valida_principal = (
        panel[
            "cobertura_pct"
        ].ge(UMBRAL_COBERTURA)
        &
        panel[
            "temperatura_media"
        ].notna()
        &
        panel[
            "humedad_media"
        ].notna()
        &
        panel[
            "viento_medio"
        ].notna()
    )

    valida_backup = (
        panel[
            "cobertura_pct_backup"
        ].ge(UMBRAL_COBERTURA)
        &
        panel[
            "temperatura_media_backup"
        ].notna()
        &
        panel[
            "humedad_media_backup"
        ].notna()
        &
        panel[
            "viento_medio_backup"
        ].notna()
    )

    usar_backup = (
        panel[
            "codigo_estacion_principal"
        ].eq(COD_TORQUEMADA)
        &
        ~valida_principal
        &
        valida_backup
    )

    for columna in vars_meteo:

        panel.loc[
            usar_backup,
            columna,
        ] = panel.loc[
            usar_backup,
            f"{columna}_backup",
        ]

    panel[
        "uso_respaldo"
    ] = usar_backup

    panel[
        "codigo_estacion_usada"
    ] = (
        panel[
            "codigo_estacion_principal"
        ]
    )

    panel[
        "nombre_estacion_usada"
    ] = (
        panel[
            "nombre_estacion_principal"
        ]
    )

    panel.loc[
        usar_backup,
        "codigo_estacion_usada",
    ] = COD_RESPALDO

    panel.loc[
        usar_backup,
        "nombre_estacion_usada",
    ] = NOMBRE_RESPALDO

    panel[
        "meteo_valida"
    ] = (
        panel[
            "cobertura_pct"
        ].ge(UMBRAL_COBERTURA)
        &
        panel[
            "temperatura_media"
        ].notna()
        &
        panel[
            "humedad_media"
        ].notna()
        &
        panel[
            "viento_medio"
        ].notna()
    )

    panel[
        "fecha_meteorologica"
    ] = (
        panel[
            "fecha_objetivo"
        ]
        - pd.Timedelta(days=1)
    )

    panel = panel.drop(
        columns=[
            f"{columna}_backup"
            for columna
            in vars_meteo
        ]
    )

    logger.info(
        "DMC integrado | "
        "Filas con respaldo=%s | "
        "Filas meteorológicas inválidas=%s.",
        panel[
            "uso_respaldo"
        ].sum(),
        (
            ~panel[
                "meteo_valida"
            ]
        ).sum(),
    )

    return panel


# ============================================================
# INTEGRACIÓN HISTÓRICA
# ============================================================

def integrar():

    logger.info(
        "Inicio de integración ETL V2 "
        "con PostgreSQL/PostGIS."
    )

    dmc, conaf, ide = (
        cargar_datos()
    )

    comunas = sorted(
        ide[
            "comuna"
        ]
        .dropna()
        .unique()
    )

    if len(comunas) != 36:
        logger.warning(
            "Se esperaban 36 comunas "
            "y se encontraron %s.",
            len(comunas),
        )

    asignacion = (
        asignar_estaciones(
            comunas
        )
    )

    perfil = (
        construir_perfil_historico(
            conaf,
            comunas,
        )
    )

    panel = construir_panel(
        comunas,
        conaf,
    )

    panel = panel.merge(
        asignacion,
        on="comuna",
        how="left",
    )

    panel = panel.merge(
        perfil[
            [
                "comuna",
                "incendios_historicos",
            ]
        ],
        on="comuna",
        how="left",
    )

    panel = agregar_vegetacion(
        panel,
        ide,
    )

    panel = agregar_meteorologia(
        panel,
        dmc,
    )

    panel.to_csv(
        PROCESSED
        / "panel_diario_integrado.csv",
        index=False,
        encoding="utf-8-sig",
    )

    dataset = panel[
        panel["meteo_valida"]
        &
        panel[
            "vegetacion_cobertura"
        ].notna()
        &
        panel[
            "incendios_historicos"
        ].notna()
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
        "ocurrencia_incendio",
    ]

    dataset = (
        dataset[
            columnas
        ]
        .sort_values(
            [
                "fecha_objetivo",
                "comuna",
            ]
        )
    )

    dataset.to_csv(
        PROCESSED
        / "dataset_modelo_diario.csv",
        index=False,
        encoding="utf-8-sig",
    )

    logger.info(
        "Dataset final | "
        "Registros=%s | Comunas=%s | "
        "Positivos=%s | Respaldo=%s.",
        len(dataset),
        dataset[
            "comuna"
        ].nunique(),
        dataset[
            "ocurrencia_incendio"
        ].sum(),
        dataset[
            "uso_respaldo"
        ].sum(),
    )

    logger.info(
        "Rango final=%s a %s.",
        dataset[
            "fecha_objetivo"
        ].min().date(),
        dataset[
            "fecha_objetivo"
        ].max().date(),
    )

    logger.info(
        "Integración histórica finalizada correctamente."
    )

    return dataset


# ============================================================
# CARGA DE DATOS ACTUALES
# ============================================================

def cargar_datos_actuales():

    ruta_meteo = (
        PROCESSED
        / "meteorologia_actual.csv"
    )

    ruta_ide = (
        PROCESSED
        / "vegetacion_comuna.csv"
    )

    ruta_perfil = (
        PROCESSED
        / "perfil_incendios_historicos.csv"
    )

    for ruta in [
        ruta_meteo,
        ruta_ide,
        ruta_perfil,
    ]:

        if not ruta.exists():
            raise FileNotFoundError(
                f"No existe archivo requerido: {ruta}"
            )

    meteorologia = pd.read_csv(
        ruta_meteo,
        parse_dates=["fecha"],
    )

    ide = pd.read_csv(
        ruta_ide
    )

    perfil = pd.read_csv(
        ruta_perfil
    )

    meteorologia[
        "codigo_estacion"
    ] = (
        meteorologia[
            "codigo_estacion"
        ]
        .astype(str)
    )

    ide["comuna"] = (
        ide["comuna"]
        .apply(normalizar_comuna)
    )

    perfil["comuna"] = (
        perfil["comuna"]
        .apply(normalizar_comuna)
    )

    ide[
        "anio_cobertura"
    ] = (
        ide[
            "anio_cobertura"
        ]
        .astype(int)
    )

    return (
        meteorologia,
        ide,
        perfil,
    )


# ============================================================
# INTEGRACIÓN ACTUAL / PRODUCCIÓN
# ============================================================

def integrar_actual(
    fecha_prediccion=None,
):

    logger.info(
        "Inicio de integración de variables actuales "
        "con PostgreSQL/PostGIS."
    )

    meteorologia, ide, perfil = (
        cargar_datos_actuales()
    )

    # --------------------------------------------------------
    # FECHA METEOROLÓGICA
    # --------------------------------------------------------

    fechas_meteo = (
        meteorologia[
            "fecha"
        ]
        .dropna()
        .dt.normalize()
        .unique()
    )

    if len(fechas_meteo) != 1:
        raise ValueError(
            "meteorologia_actual.csv debe contener "
            "exactamente un día meteorológico. "
            f"Se encontraron {len(fechas_meteo)}."
        )

    fecha_meteorologia = pd.Timestamp(
        fechas_meteo[0]
    )

    if fecha_prediccion is None:

        fecha_prediccion = (
            fecha_meteorologia
            +
            pd.Timedelta(days=1)
        )

    else:

        fecha_prediccion = (
            pd.Timestamp(
                fecha_prediccion
            )
            .normalize()
        )


    if (
        fecha_meteorologia
        >=
        fecha_prediccion
    ):

        raise ValueError(
            "La fecha meteorológica debe ser "
            "anterior a la fecha de predicción."
        )

    # --------------------------------------------------------
    # COMUNAS Y ASIGNACIÓN POSTGIS
    # --------------------------------------------------------

    comunas = sorted(
        ide[
            "comuna"
        ]
        .dropna()
        .unique()
    )

    if len(comunas) != 36:
        raise ValueError(
            f"Se esperaban 36 comunas y se encontraron "
            f"{len(comunas)}."
        )

    variables = (
        asignar_estaciones(
            comunas
        )
    )

    # --------------------------------------------------------
    # PERFIL HISTÓRICO
    # --------------------------------------------------------

    variables = variables.merge(
        perfil[
            [
                "comuna",
                "incendios_historicos",
            ]
        ],
        on="comuna",
        how="left",
    )

    # --------------------------------------------------------
    # VEGETACIÓN
    # --------------------------------------------------------

    anio_prediccion = (
        fecha_prediccion.year
    )

    ide_actual = ide[
        ide[
            "anio_cobertura"
        ]
        <= anio_prediccion
    ].copy()

    ide_actual = (
        ide_actual
        .sort_values(
            [
                "comuna",
                "anio_cobertura",
            ]
        )
        .drop_duplicates(
            subset=["comuna"],
            keep="last",
        )
    )

    variables = variables.merge(
        ide_actual[
            [
                "comuna",
                "anio_cobertura",
                "vegetacion_cobertura",
            ]
        ],
        on="comuna",
        how="left",
    )

    # --------------------------------------------------------
    # VARIABLES METEOROLÓGICAS
    # --------------------------------------------------------

    vars_meteo = [
        "temperatura_media",
        "temperatura_max",
        "humedad_media",
        "humedad_min",
        "viento_medio",
        "viento_max",
        "cobertura_pct",
    ]

    principal = meteorologia[
        [
            "codigo_estacion",
            *vars_meteo,
        ]
    ].copy()

    principal = principal.rename(
        columns={
            "codigo_estacion":
                "codigo_estacion_principal"
        }
    )

    variables = variables.merge(
        principal,
        on="codigo_estacion_principal",
        how="left",
    )

    # --------------------------------------------------------
    # RESPALDO JARDÍN BOTÁNICO
    # --------------------------------------------------------

    backup = meteorologia[
        meteorologia[
            "codigo_estacion"
        ].eq(
            COD_RESPALDO
        )
    ].copy()

    if len(backup) > 1:
        raise ValueError(
            "Se encontró más de un registro diario "
            "para Jardín Botánico."
        )

    for columna in vars_meteo:

        if backup.empty:
            variables[
                f"{columna}_backup"
            ] = np.nan

        else:
            variables[
                f"{columna}_backup"
            ] = backup.iloc[0][
                columna
            ]

    # --------------------------------------------------------
    # VALIDACIÓN ESTACIÓN PRINCIPAL
    # --------------------------------------------------------

    valida_principal = (
        variables[
            "cobertura_pct"
        ].ge(
            UMBRAL_COBERTURA
        )
        &
        variables[
            "temperatura_media"
        ].notna()
        &
        variables[
            "humedad_media"
        ].notna()
        &
        variables[
            "viento_medio"
        ].notna()
    )

    # --------------------------------------------------------
    # VALIDACIÓN RESPALDO
    # --------------------------------------------------------

    valida_backup = (
        variables[
            "cobertura_pct_backup"
        ].ge(
            UMBRAL_COBERTURA
        )
        &
        variables[
            "temperatura_media_backup"
        ].notna()
        &
        variables[
            "humedad_media_backup"
        ].notna()
        &
        variables[
            "viento_medio_backup"
        ].notna()
    )

    usar_backup = (
        variables[
            "codigo_estacion_principal"
        ].eq(
            COD_TORQUEMADA
        )
        &
        ~valida_principal
        &
        valida_backup
    )

    for columna in vars_meteo:

        variables.loc[
            usar_backup,
            columna,
        ] = variables.loc[
            usar_backup,
            f"{columna}_backup",
        ]

    variables[
        "uso_respaldo"
    ] = usar_backup

    variables[
        "codigo_estacion_usada"
    ] = (
        variables[
            "codigo_estacion_principal"
        ]
    )

    variables[
        "nombre_estacion_usada"
    ] = (
        variables[
            "nombre_estacion_principal"
        ]
    )

    variables.loc[
        usar_backup,
        "codigo_estacion_usada",
    ] = COD_RESPALDO

    variables.loc[
        usar_backup,
        "nombre_estacion_usada",
    ] = NOMBRE_RESPALDO

    # --------------------------------------------------------
    # VALIDACIÓN METEOROLOGÍA FINAL
    # --------------------------------------------------------

    variables[
        "meteo_valida"
    ] = (
        variables[
            "cobertura_pct"
        ].ge(
            UMBRAL_COBERTURA
        )
        &
        variables[
            "temperatura_media"
        ].notna()
        &
        variables[
            "humedad_media"
        ].notna()
        &
        variables[
            "viento_medio"
        ].notna()
    )

    # --------------------------------------------------------
    # FECHAS
    # --------------------------------------------------------

    variables[
        "fecha_prediccion"
    ] = fecha_prediccion

    variables[
        "fecha_meteorologia"
    ] = fecha_meteorologia

    # --------------------------------------------------------
    # LIMPIEZA COLUMNAS TEMPORALES BACKUP
    # --------------------------------------------------------

    variables = variables.drop(
        columns=[
            f"{columna}_backup"
            for columna
            in vars_meteo
        ]
    )

    # --------------------------------------------------------
    # VALIDACIONES OPERATIVAS
    # --------------------------------------------------------

    if len(variables) != 36:
        raise ValueError(
            f"Se esperaban 36 filas actuales y se obtuvieron "
            f"{len(variables)}."
        )

    if (
        variables[
            "vegetacion_cobertura"
        ]
        .isna()
        .any()
    ):
        raise ValueError(
            "Existen comunas sin cobertura vegetal."
        )

    if (
        variables[
            "incendios_historicos"
        ]
        .isna()
        .any()
    ):
        raise ValueError(
            "Existen comunas sin perfil histórico."
        )

    invalidas = int(
        (
            ~variables[
                "meteo_valida"
            ]
        ).sum()
    )

    if invalidas > 0:
        logger.warning(
            "Variables actuales con meteorología inválida=%s.",
            invalidas,
        )

    # --------------------------------------------------------
    # COLUMNAS FINALES
    # ============================================================

    columnas = [
        "comuna",
        "fecha_prediccion",
        "fecha_meteorologia",
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
    ]

    variables = (
        variables[
            columnas
        ]
        .sort_values(
            "comuna"
        )
        .reset_index(
            drop=True
        )
    )

    salida = (
        PROCESSED
        / "variables_actuales.csv"
    )

    variables.to_csv(
        salida,
        index=False,
        encoding="utf-8-sig",
    )

    logger.info(
        "Variables actuales generadas | "
        "Fecha meteorología=%s | "
        "Fecha predicción=%s | "
        "Comunas=%s | "
        "Respaldo=%s.",
        fecha_meteorologia.date(),
        fecha_prediccion.date(),
        len(variables),
        variables[
            "uso_respaldo"
        ].sum(),
    )

    logger.info(
        "Variables actuales guardadas: %s",
        salida,
    )

    return variables


# ============================================================
# EJECUCIÓN DIRECTA
# ============================================================

if __name__ == "__main__":
    integrar()