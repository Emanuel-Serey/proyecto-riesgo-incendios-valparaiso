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

from logger_config import obtener_logger


logger = obtener_logger("integracion", "integracion.log")


# CONAF + IDE

def integrar_conaf_ide():
    logger.info("Inicio de integración CONAF + IDE.")

    eventos_conaf = procesar_eventos_conaf()
    conaf = construir_panel_conaf(eventos_conaf)
    conaf["anio"] = conaf["periodo"].str[:4].astype(int)

    ide = procesar_ide()
    cobertura = obtener_cobertura_dominante(ide)
    cobertura["anio_cobertura"] = cobertura["anio_cobertura"].astype(int)

    integrado = conaf.merge(cobertura, on="comuna", how="inner")

    # Se utiliza la cobertura más reciente conocida hasta el año del registro
    integrado = integrado[integrado["anio_cobertura"] <= integrado["anio"]].copy()

    integrado = integrado.sort_values(
        ["comuna", "periodo", "anio_cobertura"],
        ascending=[True, True, False]
    )

    integrado = integrado.drop_duplicates(
        subset=["comuna", "periodo"],
        keep="first"
    ).reset_index(drop=True)

    logger.info(
        "Integración CONAF + IDE finalizada: %s registros | Comunas: %s.",
        len(integrado),
        integrado["comuna"].nunique()
    )

    return integrado


# Estaciones DMC

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

    return gpd.GeoDataFrame(
        estaciones,
        geometry=gpd.points_from_xy(
            estaciones["longitud_estacion"],
            estaciones["latitud_estacion"]
        ),
        crs="EPSG:4326"
    )


# Geometrías comunales

def obtener_geometrias_comunas():
    ide = gpd.read_file(RUTA_IDE)

    comunas = ide[["NOM_COM", "geometry"]].copy()
    comunas = comunas.rename(columns={"NOM_COM": "comuna"})
    comunas["comuna"] = comunas["comuna"].astype(str).str.strip()

    # Une los polígonos pertenecientes a una misma comuna
    comunas = comunas.dissolve(by="comuna", as_index=False)

    logger.info("Geometrías comunales generadas: %s comunas.", len(comunas))
    return comunas


# Asignación comuna -> estación DMC

def asignar_estacion_mas_cercana():
    logger.info("Inicio de asignación de estaciones DMC.")

    comunas = obtener_geometrias_comunas()
    estaciones = obtener_estaciones_dmc()

    crs_proyectado = comunas.estimate_utm_crs()
    comunas = comunas.to_crs(crs_proyectado)
    estaciones = estaciones.to_crs(crs_proyectado)

    comunas["centroide"] = comunas.geometry.centroid
    resultados = []

    for _, comuna in comunas.iterrows():
        distancias = estaciones.geometry.distance(comuna["centroide"])
        indice_cercana = distancias.idxmin()
        estacion = estaciones.loc[indice_cercana]
        distancia_km = distancias.loc[indice_cercana] / 1000

        resultados.append({
            "comuna": comuna["comuna"],
            "codigo_estacion": estacion["codigo_estacion"],
            "nombre_estacion": estacion["nombre_estacion"],
            "distancia_estacion_km": round(distancia_km, 2)
        })

    asignacion = pd.DataFrame(resultados)

    logger.info(
        "Asignación DMC finalizada: %s comunas | Distancia promedio: %.2f km | Distancia máxima: %.2f km.",
        len(asignacion),
        asignacion["distancia_estacion_km"].mean(),
        asignacion["distancia_estacion_km"].max()
    )

    return asignacion


# Integración completa

def integrar_todas_las_fuentes():
    logger.info("Inicio de integración completa de fuentes.")

    datos = integrar_conaf_ide()

    asignacion = asignar_estacion_mas_cercana()
    datos = datos.merge(asignacion, on="comuna", how="left")

    dmc = procesar_dmc()

    dmc["codigo_estacion"] = dmc["codigo_estacion"].astype(str)
    dmc["periodo"] = dmc["periodo"].astype(str)

    datos["codigo_estacion"] = datos["codigo_estacion"].astype(str)
    datos["periodo"] = datos["periodo"].astype(str)

    datos = datos.merge(
        dmc[["codigo_estacion", "periodo", "temperatura", "humedad", "viento"]],
        on=["codigo_estacion", "periodo"],
        how="left"
    )

    completos = datos.dropna(
        subset=[
            "temperatura",
            "humedad",
            "viento",
            "vegetacion_cobertura",
            "incendios_historicos"
        ]
    )

    logger.info(
        "Integración completa finalizada: %s registros | %s comunas | Registros completos: %s.",
        len(datos),
        datos["comuna"].nunique(),
        len(completos)
    )

    logger.info(
        "Nulos meteorológicos: temperatura=%s | humedad=%s | viento=%s.",
        datos["temperatura"].isna().sum(),
        datos["humedad"].isna().sum(),
        datos["viento"].isna().sum()
    )

    return datos


# Ejecución directa

if __name__ == "__main__":
    try:
        logger.info("Inicio de ejecución directa de integración.")

        datos = integrar_todas_las_fuentes()

        print("\n--- INTEGRACIÓN COMPLETA ---")

        print("\nPrimeros registros:")
        columnas = [
            "comuna", "periodo", "codigo_estacion", "nombre_estacion",
            "temperatura", "humedad", "viento", "vegetacion_cobertura",
            "incendios_historicos", "ocurrencia_incendio"
        ]
        print(datos[columnas].head(30))

        print("\nCantidad total de registros:")
        print(len(datos))

        print("\nCantidad de comunas:")
        print(datos["comuna"].nunique())

        print("\nComunas asignadas a cada estación:")
        asignaciones = (
            datos[
                ["comuna", "codigo_estacion", "nombre_estacion", "distancia_estacion_km"]
            ]
            .drop_duplicates()
            .sort_values(["codigo_estacion", "distancia_estacion_km"])
        )
        print(asignaciones.to_string(index=False))

        print("\nRegistros sin datos meteorológicos:")
        print(datos[["temperatura", "humedad", "viento"]].isna().sum())

        completos = datos.dropna(
            subset=[
                "temperatura",
                "humedad",
                "viento",
                "vegetacion_cobertura",
                "incendios_historicos"
            ]
        )

        print("\nRegistros completos de las 5 variables:")
        print(len(completos))

        print("\nRango temporal de registros completos:")
        print(completos["periodo"].min(), "a", completos["periodo"].max())

        print("\n--- DISPONIBILIDAD POR ESTACIÓN ---")

        resumen_estaciones = (
            datos.groupby(["codigo_estacion", "nombre_estacion"])
            .agg(
                registros=("periodo", "count"),
                temperatura_disponible=("temperatura", "count"),
                humedad_disponible=("humedad", "count"),
                viento_disponible=("viento", "count"),
                periodo_inicio=("periodo", "min"),
                periodo_fin=("periodo", "max")
            )
            .reset_index()
        )

        print(resumen_estaciones.to_string(index=False))

        print("\n--- REGISTROS COMPLETOS POR COMUNA ---")

        resumen_comunas = (
            datos.assign(
                completo=datos[
                    [
                        "temperatura",
                        "humedad",
                        "viento",
                        "vegetacion_cobertura",
                        "incendios_historicos"
                    ]
                ].notna().all(axis=1)
            )
            .groupby("comuna")
            .agg(
                total_registros=("periodo", "count"),
                registros_completos=("completo", "sum")
            )
            .reset_index()
        )

        print(
            resumen_comunas
            .sort_values("registros_completos")
            .to_string(index=False)
        )

        logger.info("Ejecución directa de integración finalizada correctamente.")

    except Exception:
        logger.exception("Error durante la integración de fuentes.")
        raise