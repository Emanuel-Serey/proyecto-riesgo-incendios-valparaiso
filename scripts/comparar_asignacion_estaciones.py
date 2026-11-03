from pathlib import Path
import os

import geopandas as gpd
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text


# ============================================================
# CONFIGURACIÓN
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[1]

load_dotenv(BASE_DIR / ".env")

GEOJSON_PATH = (
    BASE_DIR
    / "frontend"
    / "public"
    / "data"
    / "comunas_valparaiso.geojson"
)

OUTPUT_DIR = BASE_DIR / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

OUTPUT_CSV = (
    OUTPUT_DIR
    / "comparacion_geopandas_postgis_estaciones.csv"
)

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "incendios_valparaiso")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD")

# UTM 19 Sur:
# apropiado para la Región de Valparaíso y permite
# calcular distancias métricas con GeoPandas.
CRS_METRICO = "EPSG:32719"


# ============================================================
# CONEXIÓN
# ============================================================

def crear_engine():

    if not DB_PASSWORD:
        raise ValueError(
            "No se encontró DB_PASSWORD en el archivo .env."
        )

    url = (
        f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}"
        f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )

    return create_engine(url)


# ============================================================
# DETECTAR COLUMNA COMUNA
# ============================================================

def obtener_columna_comuna(gdf):

    candidatos = [
        "comuna",
        "COMUNA",
        "Comuna",
        "NOM_COM",
        "NOM_COMUNA",
        "nombre",
        "NOMBRE",
    ]

    for columna in candidatos:
        if columna in gdf.columns:
            return columna

    raise ValueError(
        "No se encontró una columna de comuna. "
        f"Columnas disponibles: {list(gdf.columns)}"
    )


# ============================================================
# GEOPANDAS
# ============================================================

def calcular_asignacion_geopandas(engine):

    print("\n----------------------------------------------")
    print("1. Calculando asignación con GeoPandas")
    print("----------------------------------------------")

    # --------------------------------------------------------
    # CARGAR COMUNAS
    # --------------------------------------------------------

    comunas = gpd.read_file(GEOJSON_PATH)

    columna_comuna = obtener_columna_comuna(comunas)

    comunas = comunas[
        [
            columna_comuna,
            "geometry",
        ]
    ].copy()

    comunas = comunas.rename(
        columns={
            columna_comuna: "comuna"
        }
    )

    if comunas.crs is None:
        raise ValueError(
            "Las comunas no tienen CRS definido."
        )

    if comunas.crs.to_epsg() != 4326:
        comunas = comunas.to_crs(epsg=4326)

    print(f"Comunas cargadas: {len(comunas)}")

    # --------------------------------------------------------
    # GENERAR PUNTO REPRESENTATIVO
    # --------------------------------------------------------

    # representative_point() es el equivalente conceptual
    # de ST_PointOnSurface utilizado en PostGIS.
    puntos = comunas[
        ["comuna"]
    ].copy()

    puntos["geometry"] = (
        comunas.geometry.representative_point()
    )

    puntos = gpd.GeoDataFrame(
        puntos,
        geometry="geometry",
        crs="EPSG:4326",
    )

    # --------------------------------------------------------
    # CARGAR ESTACIONES DESDE POSTGIS
    # --------------------------------------------------------

    estaciones = gpd.read_postgis(
        """
        SELECT
            codigo_estacion,
            nombre,
            geom
        FROM estaciones_meteorologicas
        ORDER BY codigo_estacion;
        """,
        con=engine,
        geom_col="geom",
    )

    if estaciones.crs is None:
        estaciones = estaciones.set_crs(
            epsg=4326
        )

    print(
        f"Estaciones disponibles: {len(estaciones)}"
    )

    if len(estaciones) != 5:
        raise ValueError(
            "Se esperaban 5 estaciones meteorológicas."
        )

    # --------------------------------------------------------
    # REPROYECTAR A CRS MÉTRICO
    # --------------------------------------------------------

    puntos_metricos = puntos.to_crs(
        CRS_METRICO
    )

    estaciones_metricas = estaciones.to_crs(
        CRS_METRICO
    )

    # --------------------------------------------------------
    # BUSCAR ESTACIÓN MÁS CERCANA
    # --------------------------------------------------------

    resultados = []

    for _, comuna in puntos_metricos.iterrows():

        distancias = (
            estaciones_metricas.geometry
            .distance(comuna.geometry)
        )

        indice_menor = distancias.idxmin()

        estacion = estaciones_metricas.loc[
            indice_menor
        ]

        distancia_m = distancias.loc[
            indice_menor
        ]

        resultados.append(
            {
                "comuna": comuna["comuna"],
                "codigo_estacion_geopandas":
                    estacion["codigo_estacion"],
                "estacion_geopandas":
                    estacion["nombre"],
                "distancia_geopandas_km":
                    round(
                        float(distancia_m) / 1000,
                        2,
                    ),
            }
        )

    resultado = pd.DataFrame(resultados)

    print(
        f"Asignaciones GeoPandas calculadas: "
        f"{len(resultado)}"
    )

    return resultado


# ============================================================
# POSTGIS
# ============================================================

def calcular_asignacion_postgis(engine):

    print("\n----------------------------------------------")
    print("2. Calculando asignación con PostGIS")
    print("----------------------------------------------")

    consulta = text(
        """
        SELECT
            c.comuna,

            e.codigo_estacion
                AS codigo_estacion_postgis,

            e.nombre
                AS estacion_postgis,

            ROUND(
                (
                    ST_Distance(
                        ST_PointOnSurface(
                            c.geom
                        )::geography,
                        e.geom::geography
                    )
                    / 1000
                )::numeric,
                2
            )::double precision
                AS distancia_postgis_km

        FROM comunas_geometrias c

        CROSS JOIN LATERAL (

            SELECT
                codigo_estacion,
                nombre,
                geom

            FROM estaciones_meteorologicas e

            ORDER BY
                ST_Distance(
                    ST_PointOnSurface(
                        c.geom
                    )::geography,
                    e.geom::geography
                )

            LIMIT 1

        ) e

        ORDER BY c.comuna;
        """
    )

    resultado = pd.read_sql(
        consulta,
        engine,
    )

    print(
        f"Asignaciones PostGIS calculadas: "
        f"{len(resultado)}"
    )

    return resultado


# ============================================================
# COMPARACIÓN
# ============================================================

def comparar(
    geopandas_df,
    postgis_df,
):

    print("\n----------------------------------------------")
    print("3. Comparando resultados")
    print("----------------------------------------------")

    comparacion = geopandas_df.merge(
        postgis_df,
        on="comuna",
        how="outer",
        validate="one_to_one",
    )

    comparacion["coincide"] = (
        comparacion[
            "codigo_estacion_geopandas"
        ]
        ==
        comparacion[
            "codigo_estacion_postgis"
        ]
    )

    comparacion[
        "diferencia_distancia_km"
    ] = (
        comparacion[
            "distancia_geopandas_km"
        ]
        -
        comparacion[
            "distancia_postgis_km"
        ]
    ).abs().round(2)

    comparacion = comparacion.sort_values(
        "comuna"
    ).reset_index(drop=True)

    return comparacion


# ============================================================
# MAIN
# ============================================================

def main():

    print("==============================================")
    print("Comparación GeoPandas vs PostGIS")
    print("Asignación de estaciones meteorológicas")
    print("==============================================")

    if not GEOJSON_PATH.exists():
        raise FileNotFoundError(
            f"No existe: {GEOJSON_PATH}"
        )

    engine = crear_engine()

    # --------------------------------------------------------
    # COMPROBAR POSTGIS
    # --------------------------------------------------------

    with engine.connect() as connection:

        version = connection.execute(
            text(
                """
                SELECT PostGIS_Version();
                """
            )
        ).scalar()

    print(f"\nPostGIS activo: {version}")

    # --------------------------------------------------------
    # CALCULAR
    # --------------------------------------------------------

    geopandas_df = (
        calcular_asignacion_geopandas(
            engine
        )
    )

    postgis_df = (
        calcular_asignacion_postgis(
            engine
        )
    )

    comparacion = comparar(
        geopandas_df,
        postgis_df,
    )

    # --------------------------------------------------------
    # RESUMEN
    # --------------------------------------------------------

    total = len(comparacion)

    coinciden = int(
        comparacion["coincide"].sum()
    )

    diferentes = total - coinciden

    porcentaje = (
        coinciden / total * 100
        if total > 0
        else 0
    )

    print("\n==============================================")
    print("RESULTADO FINAL")
    print("==============================================")

    print(f"Comunas comparadas: {total}")
    print(f"Asignaciones iguales: {coinciden}")
    print(f"Asignaciones diferentes: {diferentes}")

    print(
        f"Coincidencia: {porcentaje:.2f}%"
    )

    # --------------------------------------------------------
    # DIFERENCIAS
    # --------------------------------------------------------

    diferencias = comparacion[
        ~comparacion["coincide"]
    ]

    if diferencias.empty:

        print(
            "\n✅ GeoPandas y PostGIS asignan "
            "la misma estación a las 36 comunas."
        )

    else:

        print(
            "\n⚠️ Comunas con asignación diferente:"
        )

        for _, fila in diferencias.iterrows():

            print(
                f"\n- {fila['comuna']}"
            )

            print(
                "  GeoPandas: "
                f"{fila['codigo_estacion_geopandas']} | "
                f"{fila['estacion_geopandas']} | "
                f"{fila['distancia_geopandas_km']} km"
            )

            print(
                "  PostGIS:   "
                f"{fila['codigo_estacion_postgis']} | "
                f"{fila['estacion_postgis']} | "
                f"{fila['distancia_postgis_km']} km"
            )

    # --------------------------------------------------------
    # GUARDAR CSV
    # --------------------------------------------------------

    comparacion.to_csv(
        OUTPUT_CSV,
        index=False,
        encoding="utf-8-sig",
    )

    print(
        f"\nArchivo generado:\n{OUTPUT_CSV}"
    )

    print("\n==============================================")

    engine.dispose()


# ============================================================
# EJECUCIÓN
# ============================================================

if __name__ == "__main__":
    main()