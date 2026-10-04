import pandas as pd
import geopandas as gpd

from limpieza_transformacion import (
    procesar_eventos_conaf,
    construir_panel_conaf,
    procesar_ide,
    obtener_cobertura_dominante,
    procesar_dmc,
    RUTA_IDE
)


# ==========================================================
# INTEGRACIÓN CONAF + IDE
# ==========================================================

def integrar_conaf_ide():

    # -------------------------
    # CONAF
    # -------------------------

    eventos_conaf = procesar_eventos_conaf()

    conaf = construir_panel_conaf(
        eventos_conaf
    )

    # Obtenemos el año desde el periodo YYYY-MM
    conaf["anio"] = (
        conaf["periodo"]
        .str[:4]
        .astype(int)
    )

    # -------------------------
    # IDE
    # -------------------------

    ide = procesar_ide()

    cobertura = obtener_cobertura_dominante(
        ide
    )

    cobertura["anio_cobertura"] = (
        cobertura["anio_cobertura"]
        .astype(int)
    )

    # -------------------------
    # CONAF + IDE
    # -------------------------

    integrado = conaf.merge(
        cobertura,
        on="comuna",
        how="inner"
    )

    # Solo utilizar coberturas conocidas
    # hasta el año del registro.
    #
    # Ejemplo:
    # 2018 -> puede usar 2017
    # 2020 -> puede usar 2019
    # 2022 -> puede usar 2021
    integrado = integrado[
        integrado["anio_cobertura"]
        <= integrado["anio"]
    ].copy()

    # Ordenamos para elegir la cobertura
    # más reciente disponible
    integrado = integrado.sort_values(
        [
            "comuna",
            "periodo",
            "anio_cobertura"
        ],
        ascending=[
            True,
            True,
            False
        ]
    )

    # Una sola cobertura por comuna + periodo
    integrado = integrado.drop_duplicates(
        subset=[
            "comuna",
            "periodo"
        ],
        keep="first"
    )

    integrado = integrado.reset_index(
        drop=True
    )

    return integrado


# ==========================================================
# ESTACIONES DMC
# ==========================================================

def obtener_estaciones_dmc():

    estaciones = pd.DataFrame([
        {
            "codigo_estacion": "320019",
            "nombre_estacion": "San Felipe Escuela Agrícola",
            "latitud_estacion": -32.755277,
            "longitud_estacion": -70.706944
        },
        {
            "codigo_estacion": "320041",
            "nombre_estacion": "Viña del Mar Ad. (Torquemada)",
            "latitud_estacion": -32.949444,
            "longitud_estacion": -71.476110
        },
        {
            "codigo_estacion": "330007",
            "nombre_estacion": "Rodelillo, Ad.",
            "latitud_estacion": -33.065277,
            "longitud_estacion": -71.556388
        },
        {
            "codigo_estacion": "330030",
            "nombre_estacion": "Santo Domingo, Ad.",
            "latitud_estacion": -33.656111,
            "longitud_estacion": -71.613333
        }
    ])

    estaciones = gpd.GeoDataFrame(
        estaciones,
        geometry=gpd.points_from_xy(
            estaciones["longitud_estacion"],
            estaciones["latitud_estacion"]
        ),
        crs="EPSG:4326"
    )

    return estaciones


# ==========================================================
# GEOMETRÍA DE LAS COMUNAS
# ==========================================================

def obtener_geometrias_comunas():

    ide = gpd.read_file(
        RUTA_IDE
    )

    comunas = ide[
        [
            "NOM_COM",
            "geometry"
        ]
    ].copy()

    comunas = comunas.rename(
        columns={
            "NOM_COM": "comuna"
        }
    )

    comunas["comuna"] = (
        comunas["comuna"]
        .astype(str)
        .str.strip()
    )

    # Une todos los polígonos de una misma comuna
    comunas = comunas.dissolve(
        by="comuna",
        as_index=False
    )

    return comunas


# ==========================================================
# ASIGNACIÓN DE ESTACIÓN DMC MÁS CERCANA
# ==========================================================

def asignar_estacion_mas_cercana():

    comunas = obtener_geometrias_comunas()

    estaciones = obtener_estaciones_dmc()

    # Sistema proyectado para calcular
    # distancias en metros
    crs_proyectado = (
        comunas.estimate_utm_crs()
    )

    comunas = comunas.to_crs(
        crs_proyectado
    )

    estaciones = estaciones.to_crs(
        crs_proyectado
    )

    # Centroide aproximado de cada comuna
    comunas["centroide"] = (
        comunas.geometry.centroid
    )

    resultados = []

    for _, comuna in comunas.iterrows():

        distancias = (
            estaciones.geometry.distance(
                comuna["centroide"]
            )
        )

        indice_cercana = (
            distancias.idxmin()
        )

        estacion = estaciones.loc[
            indice_cercana
        ]

        distancia_km = (
            distancias.loc[
                indice_cercana
            ]
            / 1000
        )

        resultados.append({
            "comuna":
                comuna["comuna"],

            "codigo_estacion":
                estacion["codigo_estacion"],

            "nombre_estacion":
                estacion["nombre_estacion"],

            "distancia_estacion_km":
                round(
                    distancia_km,
                    2
                )
        })

    return pd.DataFrame(
        resultados
    )


# ==========================================================
# INTEGRACIÓN COMPLETA
# ==========================================================

def integrar_todas_las_fuentes():

    # -------------------------
    # CONAF + IDE
    # -------------------------

    datos = integrar_conaf_ide()

    # -------------------------
    # COMUNA -> ESTACIÓN DMC
    # -------------------------

    asignacion = (
        asignar_estacion_mas_cercana()
    )

    datos = datos.merge(
        asignacion,
        on="comuna",
        how="left"
    )

    # -------------------------
    # DMC
    # -------------------------

    dmc = procesar_dmc()

    # Nos aseguramos de que los códigos
    # tengan el mismo tipo
    dmc["codigo_estacion"] = (
        dmc["codigo_estacion"]
        .astype(str)
    )

    dmc["periodo"] = (
        dmc["periodo"]
        .astype(str)
    )

    datos["codigo_estacion"] = (
        datos["codigo_estacion"]
        .astype(str)
    )

    datos["periodo"] = (
        datos["periodo"]
        .astype(str)
    )

    # -------------------------
    # INTEGRACIÓN DMC
    # -------------------------

    datos = datos.merge(
        dmc[
            [
                "codigo_estacion",
                "periodo",
                "temperatura",
                "humedad",
                "viento"
            ]
        ],
        on=[
            "codigo_estacion",
            "periodo"
        ],
        how="left"
    )

    return datos


# ==========================================================
# EJECUCIÓN DIRECTA
# ==========================================================

if __name__ == "__main__":

    datos = integrar_todas_las_fuentes()

    print(
        "\n--- INTEGRACIÓN COMPLETA ---"
    )

    # -------------------------
    # PRIMEROS REGISTROS
    # -------------------------

    print(
        "\nPrimeros registros:"
    )

    print(
        datos[
            [
                "comuna",
                "periodo",
                "codigo_estacion",
                "nombre_estacion",
                "temperatura",
                "humedad",
                "viento",
                "vegetacion_cobertura",
                "incendios_historicos",
                "ocurrencia_incendio"
            ]
        ].head(30)
    )

    # -------------------------
    # RESUMEN GENERAL
    # -------------------------

    print(
        "\nCantidad total de registros:"
    )

    print(
        len(datos)
    )

    print(
        "\nCantidad de comunas:"
    )

    print(
        datos["comuna"].nunique()
    )

    # -------------------------
    # ASIGNACIÓN DE ESTACIONES
    # -------------------------

    print(
        "\nComunas asignadas a cada estación:"
    )

    asignaciones = (
        datos[
            [
                "comuna",
                "codigo_estacion",
                "nombre_estacion",
                "distancia_estacion_km"
            ]
        ]
        .drop_duplicates()
        .sort_values(
            [
                "codigo_estacion",
                "distancia_estacion_km"
            ]
        )
    )

    print(
        asignaciones.to_string(
            index=False
        )
    )

    # -------------------------
    # NULOS METEOROLÓGICOS
    # -------------------------

    print(
        "\nRegistros sin datos meteorológicos:"
    )

    print(
        datos[
            [
                "temperatura",
                "humedad",
                "viento"
            ]
        ]
        .isna()
        .sum()
    )

    # -------------------------
    # REGISTROS COMPLETOS
    # -------------------------

    completos = datos.dropna(
        subset=[
            "temperatura",
            "humedad",
            "viento",
            "vegetacion_cobertura",
            "incendios_historicos"
        ]
    )

    print(
        "\nRegistros completos de las 5 variables:"
    )

    print(
        len(completos)
    )

    print(
        "\nRango temporal de registros completos:"
    )

    print(
        completos["periodo"].min(),
        "a",
        completos["periodo"].max()
    )

    # -------------------------
    # DISPONIBILIDAD POR ESTACIÓN
    # -------------------------

    print(
        "\n--- DISPONIBILIDAD POR ESTACIÓN ---"
    )

    resumen_estaciones = (
        datos
        .groupby(
            [
                "codigo_estacion",
                "nombre_estacion"
            ]
        )
        .agg(
            registros=(
                "periodo",
                "count"
            ),
            temperatura_disponible=(
                "temperatura",
                "count"
            ),
            humedad_disponible=(
                "humedad",
                "count"
            ),
            viento_disponible=(
                "viento",
                "count"
            ),
            periodo_inicio=(
                "periodo",
                "min"
            ),
            periodo_fin=(
                "periodo",
                "max"
            )
        )
        .reset_index()
    )

    print(
        resumen_estaciones.to_string(
            index=False
        )
    )

    # -------------------------
    # COMPLETOS POR COMUNA
    # -------------------------

    print(
        "\n--- REGISTROS COMPLETOS POR COMUNA ---"
    )

    resumen_comunas = (
        datos
        .assign(
            completo=datos[
                [
                    "temperatura",
                    "humedad",
                    "viento",
                    "vegetacion_cobertura",
                    "incendios_historicos"
                ]
            ]
            .notna()
            .all(axis=1)
        )
        .groupby(
            "comuna"
        )
        .agg(
            total_registros=(
                "periodo",
                "count"
            ),
            registros_completos=(
                "completo",
                "sum"
            )
        )
        .reset_index()
    )

    print(
        resumen_comunas
        .sort_values(
            "registros_completos"
        )
        .to_string(
            index=False
        )
    )