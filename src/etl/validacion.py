from integracion import integrar_todas_las_fuentes
from logger_config import obtener_logger


logger = obtener_logger("validacion", "validacion.log")

COLUMNAS_MODELO = [
    "temperatura",
    "humedad",
    "viento",
    "vegetacion_cobertura",
    "incendios_historicos",
    "ocurrencia_incendio"
]


def validar_duplicados(datos):
    duplicados = datos.duplicated(subset=["comuna", "periodo"]).sum()

    print("\n--- DUPLICADOS ---")
    print("Registros duplicados por comuna + periodo:", duplicados)

    logger.info("Registros duplicados por comuna + periodo: %s.", duplicados)
    return duplicados == 0


def validar_nulos(datos):
    nulos = datos[COLUMNAS_MODELO].isna().sum()

    print("\n--- VALORES NULOS ---")
    print(nulos)

    logger.info(
        "Nulos: temperatura=%s | humedad=%s | viento=%s | cobertura=%s | históricos=%s | ocurrencia=%s.",
        nulos["temperatura"],
        nulos["humedad"],
        nulos["viento"],
        nulos["vegetacion_cobertura"],
        nulos["incendios_historicos"],
        nulos["ocurrencia_incendio"]
    )

    return nulos


def validar_ocurrencia_incendio(datos):
    valores = sorted(datos["ocurrencia_incendio"].dropna().unique())
    correcto = set(valores).issubset({0, 1})

    print("\n--- OCURRENCIA DE INCENDIO ---")
    print("Valores encontrados:", valores)
    print("Variable de ocurrencia binaria válida:", correcto)

    logger.info("Valores de ocurrencia encontrados: %s | Variable binaria válida: %s.", valores, correcto)
    return correcto


def validar_incendios_historicos(datos):
    negativos = (datos["incendios_historicos"] < 0).sum()
    minimo = datos["incendios_historicos"].min()
    maximo = datos["incendios_historicos"].max()

    print("\n--- INCENDIOS HISTÓRICOS ---")
    print("Valores negativos:", negativos)
    print("Mínimo:", minimo)
    print("Máximo:", maximo)

    logger.info("Incendios históricos: mínimo=%s | máximo=%s | negativos=%s.", minimo, maximo, negativos)
    return negativos == 0


def validar_variables_meteorologicas(datos):
    print("\n--- VARIABLES METEOROLÓGICAS ---")

    for columna in ["temperatura", "humedad", "viento"]:
        minimo = datos[columna].min()
        maximo = datos[columna].max()
        promedio = round(datos[columna].mean(), 2)

        print(f"\n{columna}:")
        print("Mínimo:", minimo)
        print("Máximo:", maximo)
        print("Promedio:", promedio)

        logger.info("%s: mínimo=%.2f | máximo=%.2f | promedio=%.2f.", columna.capitalize(), minimo, maximo, promedio)

    humedad_invalida = ((datos["humedad"] < 0) | (datos["humedad"] > 100)).sum()
    viento_negativo = (datos["viento"] < 0).sum()

    print("\nHumedades fuera de 0-100:", humedad_invalida)
    print("Valores de viento negativos:", viento_negativo)

    logger.info("Humedades fuera de rango: %s | Valores de viento negativos: %s.", humedad_invalida, viento_negativo)

    return humedad_invalida == 0 and viento_negativo == 0


def validar_cobertura(datos):
    conteo = datos["vegetacion_cobertura"].value_counts(dropna=False)

    print("\n--- VEGETACIÓN / COBERTURA ---")
    print(conteo)

    logger.info("Categorías de cobertura encontradas: %s.", datos["vegetacion_cobertura"].nunique(dropna=True))
    return conteo


def validar_distancias_estaciones(datos):
    estaciones = datos[["comuna", "nombre_estacion", "distancia_estacion_km"]].drop_duplicates()

    promedio = round(estaciones["distancia_estacion_km"].mean(), 2)
    maxima = round(estaciones["distancia_estacion_km"].max(), 2)
    lejanas = estaciones[estaciones["distancia_estacion_km"] > 50]

    print("\n--- DISTANCIA A ESTACIÓN DMC ---")
    print("Distancia promedio:", promedio, "km")
    print("Distancia máxima:", maxima, "km")
    print("\nComunas a más de 50 km:")
    print(lejanas.to_string(index=False))

    logger.info("Distancia DMC promedio: %.2f km | Máxima: %.2f km | Comunas a más de 50 km: %s.",
                promedio, maxima, len(lejanas))

    if len(lejanas) > 0:
        logger.warning("Comunas a más de 50 km de su estación DMC: %s.", ", ".join(lejanas["comuna"].tolist()))

    return lejanas


def resumen_registros_completos(datos):
    completos = datos.dropna(subset=COLUMNAS_MODELO)
    porcentaje = len(completos) / len(datos) * 100

    print("\n--- REGISTROS COMPLETOS ---")
    print("Total integrado:", len(datos))
    print("Registros completos:", len(completos))
    print("Porcentaje completo:", round(porcentaje, 2), "%")
    print("Comunas con registros completos:", completos["comuna"].nunique())
    print("Rango temporal:", completos["periodo"].min(), "a", completos["periodo"].max())

    logger.info("Registros integrados: %s | Registros completos: %s | Completitud: %.2f%%.",
                len(datos), len(completos), porcentaje)
    logger.info("Comunas con registros completos: %s | Rango temporal: %s a %s.",
                completos["comuna"].nunique(), completos["periodo"].min(), completos["periodo"].max())

    return completos


def validar_dataset(datos):
    logger.info("Inicio de validación del dataset.")

    print("\nVALIDACIÓN DEL DATASET")

    duplicados_ok = validar_duplicados(datos)
    validar_nulos(datos)
    ocurrencia_ok = validar_ocurrencia_incendio(datos)
    historicos_ok = validar_incendios_historicos(datos)
    meteorologia_ok = validar_variables_meteorologicas(datos)
    validar_cobertura(datos)
    validar_distancias_estaciones(datos)

    completos = resumen_registros_completos(datos)

    errores = []
    if not duplicados_ok:
        errores.append("registros duplicados")
    if not ocurrencia_ok:
        errores.append("ocurrencia_incendio inválida")
    if not historicos_ok:
        errores.append("incendios_historicos negativos")
    if not meteorologia_ok:
        errores.append("variables meteorológicas fuera de rango")

    if errores:
        logger.error("Validación fallida: %s.", ", ".join(errores))
        raise ValueError("Validación del dataset fallida: " + ", ".join(errores))

    logger.info("Validación finalizada correctamente.")
    return completos


if __name__ == "__main__":
    try:
        datos = integrar_todas_las_fuentes()
        datos_completos = validar_dataset(datos)
    except Exception:
        logger.exception("Error durante la validación del dataset.")
        raise