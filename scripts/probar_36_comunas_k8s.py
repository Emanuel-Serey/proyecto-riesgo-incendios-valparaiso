import sys
import time
from urllib.parse import quote

import requests


BASE_URL = "http://localhost:30080/api"


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


NIVELES_VALIDOS = {
    "Bajo",
    "Medio",
    "Alto",
}


CAMPOS_OBLIGATORIOS = [
    "comuna",
    "fecha_prediccion",
    "fecha_meteorologia",
    "nivel_riesgo",
    "score_modelo",
    "temperatura_media",
    "humedad_media",
    "viento_medio",
    "vegetacion_cobertura",
    "incendios_historicos",
    "factores_principales",
]


def verificar_sistema():
    print("=" * 70)
    print("VERIFICANDO ESTADO DE KUBERNETES")
    print("=" * 70)

    try:
        respuesta = requests.get(
            f"{BASE_URL}/health/system",
            timeout=10,
        )

        respuesta.raise_for_status()

        datos = respuesta.json()

    except Exception as error:
        print(
            f"ERROR: no se pudo consultar "
            f"el sistema: {error}"
        )

        return False


    if datos.get("status") != "ok":
        print(
            "ERROR: el sistema no está "
            "completamente operativo."
        )

        print(datos)

        return False


    print("Sistema: OK")
    print(
        "Data Service:",
        datos.get(
            "services",
            {}
        ).get(
            "data_service"
        )
    )

    print(
        "Risk Service:",
        datos.get(
            "services",
            {}
        ).get(
            "risk_service"
        )
    )

    print()

    return True


def validar_respuesta(
    comuna_consultada,
    datos,
):
    errores = []


    for campo in CAMPOS_OBLIGATORIOS:

        if campo not in datos:
            errores.append(
                f"Falta campo: {campo}"
            )


    nivel = datos.get(
        "nivel_riesgo"
    )

    if (
        nivel is not None
        and nivel not in NIVELES_VALIDOS
    ):
        errores.append(
            f"Nivel inválido: {nivel}"
        )


    score = datos.get(
        "score_modelo"
    )

    if score is not None:

        try:
            score = float(score)

            if not 0 <= score <= 1:
                errores.append(
                    f"Score fuera de rango: {score}"
                )

        except (TypeError, ValueError):
            errores.append(
                f"Score inválido: {score}"
            )


    comuna_respuesta = datos.get(
        "comuna"
    )

    if (
        comuna_respuesta
        and comuna_respuesta.lower()
        != comuna_consultada.lower()
    ):
        errores.append(
            "La comuna retornada no coincide: "
            f"{comuna_respuesta}"
        )


    factores = datos.get(
        "factores_principales"
    )

    if fatores_invalidos(factores):
        errores.append(
            "No se recibieron factores "
            "explicativos SHAP."
        )


    return errores


def fatores_invalidos(factores):
    return (
        not isinstance(
            factores,
            list
        )
        or len(factores) == 0
    )


def probar_comuna(
    numero,
    comuna,
):
    url = (
        f"{BASE_URL}/riesgo/"
        f"{quote(comuna, safe='')}"
    )


    inicio = time.perf_counter()


    try:
        respuesta = requests.get(
            url,
            timeout=30,
        )

        duracion = (
            time.perf_counter()
            - inicio
        )


        if respuesta.status_code != 200:

            return {
                "ok": False,
                "comuna": comuna,
                "status": respuesta.status_code,
                "tiempo": duracion,
                "error": respuesta.text,
            }


        datos = respuesta.json()


        errores = validar_respuesta(
            comuna,
            datos,
        )


        if errores:

            return {
                "ok": False,
                "comuna": comuna,
                "status": respuesta.status_code,
                "tiempo": duracion,
                "error": " | ".join(
                    errores
                ),
            }


        return {
            "ok": True,
            "comuna": comuna,
            "status": respuesta.status_code,
            "tiempo": duracion,
            "nivel": datos[
                "nivel_riesgo"
            ],
            "score": float(
                datos[
                    "score_modelo"
                ]
            ),
            "factores": len(
                datos[
                    "factores_principales"
                ]
            ),
        }


    except Exception as error:

        duracion = (
            time.perf_counter()
            - inicio
        )

        return {
            "ok": False,
            "comuna": comuna,
            "status": "-",
            "tiempo": duracion,
            "error": str(error),
        }


def main():

    if not verificar_sistema():
        sys.exit(1)


    print("=" * 70)
    print("PRUEBA END-TO-END DE LAS 36 COMUNAS")
    print("=" * 70)
    print()


    resultados = []


    for numero, comuna in enumerate(
        COMUNAS,
        start=1,
    ):

        resultado = probar_comuna(
            numero,
            comuna,
        )

        resultados.append(
            resultado
        )


        if resultado["ok"]:

            print(
                f"[{numero:02d}/36] "
                f"OK  "
                f"{comuna:<16} "
                f"{resultado['nivel']:<5} "
                f"score={resultado['score']:.3f} "
                f"SHAP={resultado['factores']} "
                f"{resultado['tiempo']:.2f}s"
            )

        else:

            print(
                f"[{numero:02d}/36] "
                f"ERROR "
                f"{comuna:<16} "
                f"HTTP={resultado['status']} "
                f"{resultado['error']}"
            )


    exitosos = [
        r
        for r in resultados
        if r["ok"]
    ]

    fallidos = [
        r
        for r in resultados
        if not r["ok"]
    ]


    print()
    print("=" * 70)
    print("RESUMEN")
    print("=" * 70)

    print(
        f"Comunas probadas: "
        f"{len(resultados)}"
    )

    print(
        f"Correctas: "
        f"{len(exitosos)}"
    )

    print(
        f"Con error: "
        f"{len(fallidos)}"
    )


    if exitosos:

        promedio = sum(
            r["tiempo"]
            for r in exitosos
        ) / len(exitosos)

        print(
            f"Tiempo promedio: "
            f"{promedio:.2f}s"
        )


        niveles = {
            "Bajo": 0,
            "Medio": 0,
            "Alto": 0,
        }


        for resultado in exitosos:

            niveles[
                resultado["nivel"]
            ] += 1


        print()
        print("Distribución de riesgo:")

        print(
            f"  Bajo:  "
            f"{niveles['Bajo']}"
        )

        print(
            f"  Medio: "
            f"{niveles['Medio']}"
        )

        print(
            f"  Alto:  "
            f"{niveles['Alto']}"
        )


    if fallidos:

        print()
        print("COMUNAS CON ERROR:")

        for resultado in fallidos:

            print(
                f" - {resultado['comuna']}: "
                f"{resultado['error']}"
            )


        print()
        print(
            "RESULTADO FINAL: "
            "PRUEBA FALLIDA"
        )

        sys.exit(1)


    print()
    print(
        "RESULTADO FINAL: "
        "36/36 COMUNAS CORRECTAS"
    )

    sys.exit(0)


if __name__ == "__main__":
    main()