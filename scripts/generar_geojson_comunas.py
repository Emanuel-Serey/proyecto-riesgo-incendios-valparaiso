from pathlib import Path
import unicodedata

import geopandas as gpd
from shapely.geometry import box


BASE_DIR = Path(__file__).resolve().parents[1]

DPA_DIR = (
    BASE_DIR
    / "data"
    / "raw"
    / "dpa"
)

SALIDA_COMUNAS = (
    BASE_DIR
    / "frontend"
    / "public"
    / "data"
    / "comunas_valparaiso.geojson"
)

SALIDA_REGION = (
    BASE_DIR
    / "frontend"
    / "public"
    / "data"
    / "region_valparaiso.geojson"
)

SALIDA_MASCARA = (
    BASE_DIR
    / "frontend"
    / "public"
    / "data"
    / "mascara_valparaiso.geojson"
)


COMUNAS = [
    "Algarrobo",
    "Cabildo",
    "Calle Larga",
    "Cartagena",
    "Casablanca",
    "Catemu",
    "Concón",
    "El Quisco",
    "El Tabo",
    "Hijuelas",
    "La Calera",
    "La Cruz",
    "La Ligua",
    "Limache",
    "Llaillay",
    "Los Andes",
    "Nogales",
    "Olmué",
    "Panquehue",
    "Papudo",
    "Petorca",
    "Puchuncaví",
    "Putaendo",
    "Quillota",
    "Quilpué",
    "Quintero",
    "Rinconada",
    "San Antonio",
    "San Esteban",
    "San Felipe",
    "Santa María",
    "Santo Domingo",
    "Valparaíso",
    "Villa Alemana",
    "Viña del Mar",
    "Zapallar",
]


ALIAS_COMUNAS = {
    "calera": "La Calera",
    "la calera": "La Calera",

    "llaillay": "Llaillay",
    "llay-llay": "Llaillay",
    "llay llay": "Llaillay",
}


def normalizar(texto):
    texto = str(texto).strip().lower()

    return "".join(
        caracter
        for caracter in unicodedata.normalize(
            "NFD",
            texto
        )
        if unicodedata.category(caracter)
        != "Mn"
    )


def buscar_columna_comuna(columnas):
    candidatos = [
        "nom_com",
        "comuna",
        "nom_comuna",
        "nombre_comuna",
        "comuna_mayu",
    ]

    mapa_columnas = {
        normalizar(columna): columna
        for columna in columnas
    }

    for candidato in candidatos:
        if candidato in mapa_columnas:
            return mapa_columnas[candidato]

    raise ValueError(
        "No se encontró una columna con "
        "el nombre de la comuna.\n"
        f"Columnas disponibles: {list(columnas)}"
    )


def buscar_shapefile_comunas():
    archivos = list(
        DPA_DIR.rglob("*.shp")
    )

    if not archivos:
        raise FileNotFoundError(
            f"No se encontró ningún .shp "
            f"dentro de {DPA_DIR}"
        )

    archivos_comunas = [
        archivo
        for archivo in archivos
        if "comuna" in normalizar(
            str(archivo)
        )
    ]

    if archivos_comunas:
        return archivos_comunas[0]

    return archivos[0]


def generar_mascara(geometria_region):
    minx, miny, maxx, maxy = (
        geometria_region.bounds
    )

    margen_longitud = 3.0
    margen_latitud = 3.0

    rectangulo_exterior = box(
        minx - margen_longitud,
        miny - margen_latitud,
        maxx + margen_longitud,
        maxy + margen_latitud,
    )

    return rectangulo_exterior.difference(
        geometria_region
    )


def main():
    print(
        "Generando cartografía "
        "de la Región de Valparaíso..."
    )

    ruta_shp = (
        buscar_shapefile_comunas()
    )

    print(
        f"Shapefile utilizado: {ruta_shp}"
    )

    gdf = gpd.read_file(
        ruta_shp
    )

    columna_comuna = (
        buscar_columna_comuna(
            gdf.columns
        )
    )

    print(
        "Columna de comuna detectada: "
        f"{columna_comuna}"
    )

    mapa_comunas = {
        normalizar(nombre): nombre
        for nombre in COMUNAS
    }

    for (
        nombre_shp,
        nombre_sistema,
    ) in ALIAS_COMUNAS.items():

        mapa_comunas[
            normalizar(nombre_shp)
        ] = nombre_sistema

    gdf["_nombre_normalizado"] = (
        gdf[columna_comuna]
        .astype(str)
        .map(normalizar)
    )

    gdf = gdf[
        gdf[
            "_nombre_normalizado"
        ].isin(
            mapa_comunas.keys()
        )
    ].copy()

    if gdf.empty:
        raise ValueError(
            "No se encontraron comunas "
            "de Valparaíso."
        )

    gdf["comuna"] = (
        gdf[
            "_nombre_normalizado"
        ].map(
            mapa_comunas
        )
    )

    # Leaflet utiliza WGS84
    gdf = gdf.to_crs(
        epsg=4326
    )

    gdf = gdf[
        [
            "comuna",
            "geometry",
        ]
    ]

    # Una geometría por comuna
    gdf = gdf.dissolve(
        by="comuna",
        as_index=False
    )

    gdf = gdf.sort_values(
        by="comuna"
    ).reset_index(
        drop=True
    )

    SALIDA_COMUNAS.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    # -------------------------
    # GEOJSON DE COMUNAS
    # -------------------------

    gdf.to_file(
        SALIDA_COMUNAS,
        driver="GeoJSON"
    )

    # -------------------------
    # POLÍGONO REGIONAL
    # -------------------------

    geometria_region = (
        gdf.geometry.union_all()
    )

    region = gpd.GeoDataFrame(
        {
            "nombre": [
                "Área continental "
                "Región de Valparaíso"
            ]
        },
        geometry=[
            geometria_region
        ],
        crs="EPSG:4326"
    )

    region.to_file(
        SALIDA_REGION,
        driver="GeoJSON"
    )

    # -------------------------
    # MÁSCARA EXTERIOR
    # -------------------------

    geometria_mascara = (
        generar_mascara(
            geometria_region
        )
    )

    mascara = gpd.GeoDataFrame(
        {
            "nombre": [
                "Exterior del área analizada"
            ]
        },
        geometry=[
            geometria_mascara
        ],
        crs="EPSG:4326"
    )

    mascara.to_file(
        SALIDA_MASCARA,
        driver="GeoJSON"
    )

    # -------------------------
    # VALIDACIÓN
    # -------------------------

    encontradas = set(
        gdf["comuna"]
    )

    esperadas = set(
        COMUNAS
    )

    faltantes = sorted(
        esperadas - encontradas
    )

    adicionales = sorted(
        encontradas - esperadas
    )

    print()
    print(
        "GeoJSON comunas creado:"
    )
    print(
        SALIDA_COMUNAS
    )

    print()
    print(
        "GeoJSON regional creado:"
    )
    print(
        SALIDA_REGION
    )

    print()
    print(
        "Máscara exterior creada:"
    )
    print(
        SALIDA_MASCARA
    )

    print()
    print(
        f"Comunas incluidas: "
        f"{len(gdf)}"
    )

    if faltantes:
        print(
            "ADVERTENCIA - "
            "comunas faltantes:"
        )

        for comuna in faltantes:
            print(
                f" - {comuna}"
            )

    if adicionales:
        print(
            "ADVERTENCIA - "
            "comunas adicionales:"
        )

        for comuna in adicionales:
            print(
                f" - {comuna}"
            )

    if (
        not faltantes
        and not adicionales
        and len(gdf) == 36
    ):
        print(
            "Las 36 comunas fueron "
            "encontradas correctamente."
        )


if __name__ == "__main__":
    main()