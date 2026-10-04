from pathlib import Path

from integracion import integrar_todas_las_fuentes
from validacion import validar_dataset
from carga import cargar_postgresql


RUTA_PROCESSED = Path(
    "data/processed"
)


def ejecutar_pipeline():

    print("\n====================================")
    print("PIPELINE ETL - RIESGO DE INCENDIOS")
    print("====================================")

    # ======================================================
    # 1. INTEGRACIÓN
    # ======================================================

    print("\n1. Procesando e integrando fuentes...")

    datos_integrados = (
        integrar_todas_las_fuentes()
    )

    print(
        "Integración finalizada."
    )

    print(
        "Registros integrados:",
        len(datos_integrados)
    )

    # ======================================================
    # 2. VALIDACIÓN
    # ======================================================

    print("\n2. Validando dataset...")

    datos_completos = validar_dataset(
        datos_integrados
    )

    print(
        "\nValidación finalizada."
    )

    # ======================================================
    # 3. CREAR CARPETA PROCESSED
    # ======================================================

    print(
        "\n3. Preparando archivos procesados..."
    )

    RUTA_PROCESSED.mkdir(
        parents=True,
        exist_ok=True
    )

    # ======================================================
    # 4. GUARDAR DATASET INTEGRADO
    # ======================================================

    ruta_integrado = (
        RUTA_PROCESSED
        / "dataset_integrado.csv"
    )

    datos_integrados.to_csv(
        ruta_integrado,
        index=False,
        encoding="utf-8-sig"
    )

    print(
        "Dataset integrado guardado:"
    )

    print(
        ruta_integrado
    )

    # ======================================================
    # 5. GENERAR DATASET PARA ML
    # ======================================================

    columnas_dataset_modelo = [
        "comuna",
        "periodo",
        "temperatura",
        "humedad",
        "viento",
        "vegetacion_cobertura",
        "incendios_historicos",
        "ocurrencia_incendio",
        "codigo_estacion",
        "nombre_estacion",
        "distancia_estacion_km",
        "anio_cobertura"
    ]

    dataset_modelo = (
        datos_completos[
            columnas_dataset_modelo
        ]
        .copy()
    )

    ruta_modelo = (
        RUTA_PROCESSED
        / "dataset_modelo.csv"
    )

    dataset_modelo.to_csv(
        ruta_modelo,
        index=False,
        encoding="utf-8-sig"
    )

    print(
        "\nDataset para Machine Learning guardado:"
    )

    print(
        ruta_modelo
    )

    # ======================================================
    # 6. CARGA A POSTGRESQL
    # ======================================================

    print(
        "\n4. Cargando datos a PostgreSQL..."
    )

    # IMPORTANTE:
    # Se cargan TODOS los registros integrados válidos.
    #
    # La VIEW dataset_modelo en PostgreSQL
    # seleccionará solamente los registros
    # completos para Machine Learning.

    cargar_postgresql(
        datos_integrados
    )

    # ======================================================
    # 7. RESUMEN FINAL
    # ======================================================

    print("\n====================================")
    print("PIPELINE ETL FINALIZADO")
    print("====================================")

    print(
        "\nDataset integrado:"
    )

    print(
        "Registros:",
        len(datos_integrados)
    )

    print(
        "Archivo:",
        ruta_integrado
    )

    print(
        "\nDataset para Machine Learning:"
    )

    print(
        "Registros:",
        len(dataset_modelo)
    )

    print(
        "Archivo:",
        ruta_modelo
    )

    print(
        "\nDistribución de ocurrencia de incendio:"
    )

    print(
        dataset_modelo[
            "ocurrencia_incendio"
        ]
        .value_counts()
        .sort_index()
    )

    print(
        "\nNulos en variables del modelo:"
    )

    print(
        dataset_modelo[
            [
                "temperatura",
                "humedad",
                "viento",
                "vegetacion_cobertura",
                "incendios_historicos",
                "ocurrencia_incendio"
            ]
        ]
        .isna()
        .sum()
    )

    print(
        "\nPipeline ejecutado correctamente."
    )

    return (
        datos_integrados,
        dataset_modelo
    )


if __name__ == "__main__":

    ejecutar_pipeline()