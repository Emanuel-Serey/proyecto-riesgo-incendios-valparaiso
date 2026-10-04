from integracion import integrar_todas_las_fuentes


def validar_duplicados(datos):

    duplicados = datos.duplicated(
        subset=[
            "comuna",
            "periodo"
        ]
    ).sum()

    print("\n--- DUPLICADOS ---")
    print(
        "Registros duplicados por comuna + periodo:",
        duplicados
    )

    return duplicados == 0


def validar_nulos(datos):

    columnas_modelo = [
        "temperatura",
        "humedad",
        "viento",
        "vegetacion_cobertura",
        "incendios_historicos",
        "ocurrencia_incendio"
    ]

    print("\n--- VALORES NULOS ---")

    print(
        datos[
            columnas_modelo
        ]
        .isna()
        .sum()
    )


def validar_ocurrencia_incendio(datos):

    valores = sorted(
        datos["ocurrencia_incendio"]
        .dropna()
        .unique()
    )

    print("\n--- OCURRENCIA DE INCENDIO ---")
    print("Valores encontrados:", valores)

    correcto = set(valores).issubset(
        {0, 1}
    )

    print(
        " Variable de ocurrencia binaria válida",
        correcto
    )

    return correcto


def validar_incendios_historicos(datos):

    negativos = (
        datos["incendios_historicos"] < 0
    ).sum()

    print(
        "\n--- INCENDIOS HISTÓRICOS ---"
    )

    print(
        "Valores negativos:",
        negativos
    )

    print(
        "Mínimo:",
        datos["incendios_historicos"].min()
    )

    print(
        "Máximo:",
        datos["incendios_historicos"].max()
    )

    return negativos == 0


def validar_variables_meteorologicas(datos):

    print(
        "\n--- VARIABLES METEOROLÓGICAS ---"
    )

    for columna in [
        "temperatura",
        "humedad",
        "viento"
    ]:

        print(
            f"\n{columna}:"
        )

        print(
            "Mínimo:",
            datos[columna].min()
        )

        print(
            "Máximo:",
            datos[columna].max()
        )

        print(
            "Promedio:",
            round(
                datos[columna].mean(),
                2
            )
        )

    # Humedad debe estar entre 0 y 100
    humedad_invalida = (
        (
            datos["humedad"] < 0
        )
        |
        (
            datos["humedad"] > 100
        )
    ).sum()

    print(
        "\nHumedades fuera de 0-100:",
        humedad_invalida
    )

    # El viento no debería ser negativo
    viento_negativo = (
        datos["viento"] < 0
    ).sum()

    print(
        "Valores de viento negativos:",
        viento_negativo
    )


def validar_cobertura(datos):

    print(
        "\n--- VEGETACIÓN / COBERTURA ---"
    )

    print(
        datos[
            "vegetacion_cobertura"
        ]
        .value_counts(
            dropna=False
        )
    )


def validar_distancias_estaciones(datos):

    estaciones = (
        datos[
            [
                "comuna",
                "nombre_estacion",
                "distancia_estacion_km"
            ]
        ]
        .drop_duplicates()
    )

    print(
        "\n--- DISTANCIA A ESTACIÓN DMC ---"
    )

    print(
        "Distancia promedio:",
        round(
            estaciones[
                "distancia_estacion_km"
            ].mean(),
            2
        ),
        "km"
    )

    print(
        "Distancia máxima:",
        round(
            estaciones[
                "distancia_estacion_km"
            ].max(),
            2
        ),
        "km"
    )

    print(
        "\nComunas a más de 50 km:"
    )

    lejanas = estaciones[
        estaciones[
            "distancia_estacion_km"
        ] > 50
    ]

    print(
        lejanas.to_string(
            index=False
        )
    )


def resumen_registros_completos(datos):

    columnas_modelo = [
        "temperatura",
        "humedad",
        "viento",
        "vegetacion_cobertura",
        "incendios_historicos",
        "ocurrencia_incendio"
    ]

    completos = datos.dropna(
        subset=columnas_modelo
    )

    print(
        "\n--- REGISTROS COMPLETOS ---"
    )

    print(
        "Total integrado:",
        len(datos)
    )

    print(
        "Registros completos:",
        len(completos)
    )

    porcentaje = (
        len(completos)
        / len(datos)
        * 100
    )

    print(
        "Porcentaje completo:",
        round(
            porcentaje,
            2
        ),
        "%"
    )

    print(
        "Comunas con registros completos:",
        completos[
            "comuna"
        ].nunique()
    )

    print(
        "Rango temporal:",
        completos["periodo"].min(),
        "a",
        completos["periodo"].max()
    )

    return completos


def validar_dataset(datos):

    print(
        "\n=============================="
    )
    print(
        "VALIDACIÓN DEL DATASET"
    )
    print(
        "=============================="
    )

    validar_duplicados(datos)

    validar_nulos(datos)

    validar_ocurrencia_incendio(datos)

    validar_incendios_historicos(datos)

    validar_variables_meteorologicas(
        datos
    )

    validar_cobertura(datos)

    validar_distancias_estaciones(
        datos
    )

    completos = (
        resumen_registros_completos(
            datos
        )
    )

    return completos


if __name__ == "__main__":

    datos = integrar_todas_las_fuentes()

    datos_completos = validar_dataset(
        datos
    )