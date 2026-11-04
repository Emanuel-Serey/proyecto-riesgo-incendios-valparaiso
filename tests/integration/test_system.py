import os

import pytest
import requests


BASE_URL = os.getenv(
    "INTEGRATION_BASE_URL",
    "http://localhost:8000/api"
)


# =========================================================
# HEALTH DEL SISTEMA REAL
# =========================================================

@pytest.mark.integration
def test_sistema_operativo():

    response = requests.get(
        f"{BASE_URL}/health/system",
        timeout=10
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
# INTEGRACION COMPLETA
# =========================================================

@pytest.mark.integration
def test_consulta_real_valparaiso():

    response = requests.get(
        f"{BASE_URL}/riesgo/Valpara%C3%ADso",
        timeout=30
    )

    assert response.status_code == 200

    data = response.json()

    assert data["comuna"] == "Valparaíso"

    assert data["nivel_riesgo"] in {
        "Bajo",
        "Medio",
        "Alto"
    }

    assert 0 <= data["score_modelo"] <= 1

    assert isinstance(
        data["temperatura_media"],
        (int, float)
    )

    assert isinstance(
        data["humedad_media"],
        (int, float)
    )

    assert isinstance(
        data["viento_medio"],
        (int, float)
    )

    assert isinstance(
        data["incendios_historicos"],
        (int, float)
    )

    assert len(
        data["factores_principales"]
    ) == 3