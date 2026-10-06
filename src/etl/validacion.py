from pathlib import Path
import logging
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[2]
PROCESSED = BASE_DIR / "data/processed"
LOGS = BASE_DIR / "logs"

RUTA_DATASET = PROCESSED / "dataset_modelo_diario.csv"
RUTA_PANEL = PROCESSED / "panel_diario_integrado.csv"
RUTA_ASIGNACION = PROCESSED / "asignacion_estaciones.csv"

logger = logging.getLogger("validacion")
logger.setLevel(logging.INFO)
logger.propagate = False

if not logger.handlers:
    fmt = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    fh = logging.FileHandler(LOGS / "validacion.log", encoding="utf-8")
    sh = logging.StreamHandler()
    fh.setFormatter(fmt)
    sh.setFormatter(fmt)
    logger.addHandler(fh)
    logger.addHandler(sh)

def validar():
    logger.info("Inicio de validación del dataset V2.")

    df = pd.read_csv(
        RUTA_DATASET,
        parse_dates=["fecha_objetivo", "fecha_meteorologica"]
    )

    panel = pd.read_csv(
        RUTA_PANEL,
        parse_dates=["fecha_objetivo", "fecha_meteorologica"]
    )

    asignacion = pd.read_csv(RUTA_ASIGNACION)

    # Duplicados
    duplicados = df.duplicated(["comuna", "fecha_objetivo"]).sum()
    logger.info(
        "Registros duplicados por comuna + fecha: %s.",
        duplicados
    )

    # Comunas y rango
    logger.info(
        "Registros=%s | Comunas=%s | Rango=%s a %s.",
        len(df),
        df["comuna"].nunique(),
        df["fecha_objetivo"].min().date(),
        df["fecha_objetivo"].max().date()
    )

    # Target
    valores_target = sorted(df["ocurrencia_incendio"].dropna().unique())
    target_valido = set(valores_target).issubset({0, 1})

    logger.info(
        "Target | Valores=%s | Binario válido=%s | Positivos=%s | Negativos=%s.",
        valores_target,
        target_valido,
        (df["ocurrencia_incendio"] == 1).sum(),
        (df["ocurrencia_incendio"] == 0).sum()
    )

    # Positivos eliminados por falta de variables
    positivos_panel = panel["ocurrencia_incendio"].sum()
    positivos_final = df["ocurrencia_incendio"].sum()

    logger.info(
        "Positivos | Panel=%s | Dataset final=%s | Excluidos=%s.",
        positivos_panel,
        positivos_final,
        positivos_panel - positivos_final
    )

    # D-1
    diferencia = (
        df["fecha_objetivo"] - df["fecha_meteorologica"]
    ).dt.days

    errores_d1 = (diferencia != 1).sum()

    logger.info(
        "Temporalidad DMC | Filas que no cumplen D-1=%s.",
        errores_d1
    )

    # Nulos
    variables = [
        "temperatura_media",
        "temperatura_max",
        "humedad_media",
        "humedad_min",
        "viento_medio",
        "viento_max",
        "vegetacion_cobertura",
        "anio_cobertura",
        "incendios_historicos"
    ]

    nulos = df[variables].isna().sum()
    logger.info(
        "Nulos variables principales: %s.",
        nulos.to_dict()
    )

    # Cobertura DMC
    cobertura_mala = (df["cobertura_pct"] < 80).sum()

    logger.info(
        "Cobertura DMC | Filas <80%%=%s | Mínima=%.2f | Promedio=%.2f.",
        cobertura_mala,
        df["cobertura_pct"].min(),
        df["cobertura_pct"].mean()
    )

    # Rangos meteorológicos
    temp_fuera = (
        (df["temperatura_media"] < -20)
        | (df["temperatura_max"] > 50)
    ).sum()

    humedad_fuera = (
        (df["humedad_min"] < 0)
        | (df["humedad_media"] > 100)
    ).sum()

    viento_negativo = (
        (df["viento_medio"] < 0)
        | (df["viento_max"] < 0)
    ).sum()

    logger.info(
        "Meteorología | Temperatura fuera de rango=%s | Humedad fuera de rango=%s | Viento negativo=%s.",
        temp_fuera,
        humedad_fuera,
        viento_negativo
    )

    # IDE temporal
    ide_futuro = (
        df["anio_cobertura"]
        > df["fecha_objetivo"].dt.year
    ).sum()

    anios_ide = sorted(
        df["anio_cobertura"].dropna().unique()
    )

    logger.info(
        "IDE | Cobertura futura=%s | Años utilizados=%s | Categorías=%s.",
        ide_futuro,
        anios_ide,
        df["vegetacion_cobertura"].nunique()
    )

    # Perfil histórico
    historicos_negativos = (
        df["incendios_historicos"] < 0
    ).sum()

    variacion_hist = (
        df.groupby("comuna")["incendios_historicos"]
        .nunique()
    )

    logger.info(
        "Incendios históricos | Negativos=%s | Comunas con valor no constante=%s.",
        historicos_negativos,
        (variacion_hist > 1).sum()
    )

    # Respaldo
    respaldo = df[df["uso_respaldo"] == True]

    respaldo_incorrecto = (
        (respaldo["codigo_estacion_principal"].astype(str) != "320041")
        | (respaldo["codigo_estacion_usada"].astype(str) != "330006")
    ).sum()

    logger.info(
        "Respaldo DMC | Filas=%s | Uso incorrecto=%s.",
        len(respaldo),
        respaldo_incorrecto
    )

    # Distancias
    max_distancia = asignacion["distancia_estacion_km"].max()
    lejanas = asignacion[
        asignacion["distancia_estacion_km"] > 50
    ]

    logger.info(
        "Distancia DMC | Promedio=%.2f km | Máxima=%.2f km | Comunas >50 km=%s.",
        asignacion["distancia_estacion_km"].mean(),
        max_distancia,
        len(lejanas)
    )

    if not lejanas.empty:
        logger.warning(
            "Comunas a más de 50 km de su estación: %s.",
            ", ".join(
                lejanas.sort_values(
                    "distancia_estacion_km",
                    ascending=False
                )["comuna"].tolist()
            )
        )

    # Islas fuera del alcance
    islas = df[
        df["comuna"].isin(["Isla de Pascua", "Juan Fernández"])
    ]

    logger.info(
        "Comunas insulares presentes en dataset: %s.",
        islas["comuna"].nunique()
    )

    errores = (
        duplicados
        + errores_d1
        + cobertura_mala
        + ide_futuro
        + historicos_negativos
        + respaldo_incorrecto
    )

    if errores == 0:
        logger.info("Validación finalizada correctamente.")
    else:
        logger.warning(
            "Validación finalizada con %s inconsistencias críticas.",
            errores
        )

    return df

if __name__ == "__main__":
    validar()