from pathlib import Path

from integracion import integrar_todas_las_fuentes
from validacion import validar_dataset
from carga import cargar_postgresql
from logger_config import obtener_logger


logger = obtener_logger("pipeline", "pipeline.log")

RUTA_PROCESSED = Path("data/processed")


def ejecutar_pipeline():
    logger.info("Inicio del pipeline ETL.")

    try:
        print("\nPIPELINE ETL - RIESGO DE INCENDIOS")

        # 1. Integración
        print("\n1. Procesando e integrando fuentes...")
        datos_integrados = integrar_todas_las_fuentes()

        print("Integración finalizada.")
        print("Registros integrados:", len(datos_integrados))

        logger.info("Integración finalizada: %s registros.", len(datos_integrados))

        # 2. Validación
        print("\n2. Validando dataset...")
        datos_completos = validar_dataset(datos_integrados)

        print("Validación finalizada.")
        logger.info("Validación finalizada: %s registros completos.", len(datos_completos))

        # 3. Archivos procesados
        print("\n3. Generando archivos procesados...")
        RUTA_PROCESSED.mkdir(parents=True, exist_ok=True)

        ruta_integrado = RUTA_PROCESSED / "dataset_integrado.csv"
        datos_integrados.to_csv(ruta_integrado, index=False, encoding="utf-8-sig")

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

        dataset_modelo = datos_completos[columnas_dataset_modelo].copy()

        ruta_modelo = RUTA_PROCESSED / "dataset_modelo.csv"
        dataset_modelo.to_csv(ruta_modelo, index=False, encoding="utf-8-sig")

        print("Dataset integrado guardado:", ruta_integrado)
        print("Dataset para ML guardado:", ruta_modelo)

        logger.info("Dataset integrado generado: %s registros.", len(datos_integrados))
        logger.info("Dataset para Machine Learning generado: %s registros.", len(dataset_modelo))

        # 4. Carga a PostgreSQL
        print("\n4. Cargando datos a PostgreSQL...")
        logger.info("Inicio de carga incremental a PostgreSQL.")

        cargar_postgresql(datos_integrados)

        logger.info("Carga a PostgreSQL finalizada correctamente.")

        # Resumen
        print("\nPIPELINE ETL FINALIZADO")
        print("Registros integrados:", len(datos_integrados))
        print("Registros para Machine Learning:", len(dataset_modelo))

        print("\nDistribución de ocurrencia de incendio:")
        print(dataset_modelo["ocurrencia_incendio"].value_counts().sort_index())

        print("\nNulos en variables del modelo:")
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
            ].isna().sum()
        )

        logger.info(
            "Pipeline finalizado correctamente: %s registros integrados | %s registros para ML.",
            len(datos_integrados),
            len(dataset_modelo)
        )

        return datos_integrados, dataset_modelo

    except Exception:
        logger.exception("Error durante la ejecución del pipeline ETL.")
        raise


if __name__ == "__main__":
    ejecutar_pipeline()