from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from fastapi.testclient import TestClient


# =========================================================
# CARGA DEL API GATEWAY
# =========================================================

RUTA_GATEWAY = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "services"
    / "api-gateway"
    / "main.py"
)

spec = spec_from_file_location(
    "api_gateway_main",
    RUTA_GATEWAY
)

gateway = module_from_spec(spec)

spec.loader.exec_module(
    gateway
)

client = TestClient(
    gateway.app
)


# =========================================================
# RESPUESTA HTTP SIMULADA
# =========================================================

class FakeResponse:

    def __init__(
        self,
        status_code,
        data
    ):
        self.status_code = status_code
        self._data = data

    def json(self):
        return self._data


# =========================================================
# HEALTH
# =========================================================

def test_health_gateway():

    response = client.get(
        "/health"
    )

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok"
    }


# =========================================================
# HEALTH GENERAL
# =========================================================

def test_health_system_ok(
    monkeypatch
):

    def fake_get(
        url,
        timeout
    ):
        return FakeResponse(
            200,
            {
                "status": "ok"
            }
        )

    monkeypatch.setattr(
        gateway.requests,
        "get",
        fake_get
    )

    response = client.get(
        "/health/system"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "ok"

    assert (
        data["services"]["data_service"]
        == "ok"
    )

    assert (
        data["services"]["risk_service"]
        == "ok"
    )


# =========================================================
# SISTEMA DEGRADADO
# =========================================================

def test_health_system_degraded(
    monkeypatch
):

    contador = {
        "llamadas": 0
    }

    def fake_get(
        url,
        timeout
    ):

        contador["llamadas"] += 1

        if contador["llamadas"] == 1:
            return FakeResponse(
                200,
                {
                    "status": "ok"
                }
            )

        raise gateway.requests.RequestException(
            "Servicio no disponible"
        )

    monkeypatch.setattr(
        gateway.requests,
        "get",
        fake_get
    )

    response = client.get(
        "/health/system"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "degraded"

    assert (
        data["services"]["data_service"]
        == "ok"
    )

    assert (
        data["services"]["risk_service"]
        == "unavailable"
    )


# =========================================================
# CONSULTA DE RIESGO
# =========================================================

def test_consulta_riesgo_correcta(
    monkeypatch
):

    variables = {
        "id_variables": 1,
        "comuna": "Valparaíso",
        "fecha_prediccion":
            "2026-11-04",
        "fecha_meteorologia":
            "2026-11-03",
        "temperatura_media": 20.0,
        "humedad_media": 55.0,
        "viento_medio": 4.0,
        "vegetacion_cobertura":
            "Bosques",
        "incendios_historicos": 5.0
    }

    resultado_modelo = {
        "id_variables": 1,
        "comuna": "Valparaíso",
        "fecha_prediccion":
            "2026-11-04",
        "score_modelo": 0.72,
        "nivel_riesgo": "Alto",
        "modelo_version":
            "random_forest_v1",
        "factores_principales": [
            {
                "variable":
                    "temperatura_media",
                "nombre":
                    "Temperatura",
                "direccion":
                    "aumenta",
                "impacto":
                    0.15
            },
            {
                "variable":
                    "humedad_media",
                "nombre":
                    "Humedad",
                "direccion":
                    "reduce",
                "impacto":
                    -0.10
            },
            {
                "variable":
                    "incendios_historicos",
                "nombre":
                    "Historial de incendios",
                "direccion":
                    "aumenta",
                "impacto":
                    0.08
            }
        ]
    }

    def fake_get(
        url,
        timeout
    ):

        assert "/variables/" in url

        return FakeResponse(
            200,
            variables
        )

    def fake_post(
        url,
        json,
        timeout
    ):

        if url.endswith("/predecir"):

            assert json["comuna"] == "Valparaíso"

            return FakeResponse(
                200,
                resultado_modelo
            )

        if url.endswith("/consultas"):

            assert json["comuna"] == "Valparaíso"

            return FakeResponse(
                200,
                {"ok": True}
            )

        raise AssertionError(
            f"POST inesperado: {url}"
        )

    monkeypatch.setattr(
        gateway.requests,
        "get",
        fake_get
    )

    monkeypatch.setattr(
        gateway.requests,
        "post",
        fake_post
    )

    response = client.get(
        "/riesgo/Valparaíso"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["comuna"] == "Valparaíso"
    assert data["nivel_riesgo"] == "Alto"
    assert data["score_modelo"] == 0.72

    assert len(
        data["factores_principales"]
    ) == 3


# =========================================================
# COMUNA INEXISTENTE
# =========================================================

def test_comuna_no_encontrada(
    monkeypatch
):

    def fake_get(
        url,
        timeout
    ):
        return FakeResponse(
            404,
            {
                "detail":
                    "Comuna no encontrada"
            }
        )

    monkeypatch.setattr(
        gateway.requests,
        "get",
        fake_get
    )

    response = client.get(
        "/riesgo/ComunaInexistente"
    )

    assert response.status_code == 404

    assert response.json() == {
        "detail":
            "Comuna no encontrada"
    }