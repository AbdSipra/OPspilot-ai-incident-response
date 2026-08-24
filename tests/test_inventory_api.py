from collections.abc import Generator
from pathlib import Path
import sys

import pytest
from fastapi.testclient import TestClient

SERVICE_ROOT = Path(__file__).resolve().parents[1] / "apps" / "inventory-api"
sys.path.insert(0, str(SERVICE_ROOT))

from inventory_api.faults import FAULT_PROFILES, InventoryFaultMode
from inventory_api.main import app, create_app

client = TestClient(app)
FAULT_PATH = "/internal/simulation/fault"


@pytest.fixture(autouse=True)
def reset_fault_state() -> Generator[None, None, None]:
    response = client.put(FAULT_PATH, json={"mode": "none"})
    assert response.status_code == 200

    yield

    response = client.put(FAULT_PATH, json={"mode": "none"})
    assert response.status_code == 200


def test_health_returns_service_status() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "inventory-api",
    }


def test_known_sku_returns_inventory() -> None:
    response = client.get("/api/v1/inventory/sku-001")

    assert response.status_code == 200
    assert response.json() == {
        "sku": "sku-001",
        "available": True,
        "quantity": 12,
    }


def test_unknown_sku_returns_not_found() -> None:
    response = client.get("/api/v1/inventory/unknown-sku")

    assert response.status_code == 404
    assert response.json()["detail"]["sku"] == "unknown-sku"


def test_fault_status_defaults_to_none() -> None:
    response = client.get(FAULT_PATH)

    assert response.status_code == 200
    assert response.json()["mode"] == "none"
    assert response.json()["injected_delay_ms"] == 0


def test_fault_control_rejects_unknown_mode() -> None:
    response = client.put(FAULT_PATH, json={"mode": "arbitrary-command"})

    assert response.status_code == 422


def test_fault_control_rejects_extra_fields() -> None:
    response = client.put(
        FAULT_PATH,
        json={
            "mode": "none",
            "delay_seconds": 999,
        },
    )

    assert response.status_code == 422


def test_database_failure_returns_service_unavailable() -> None:
    response = client.put(FAULT_PATH, json={"mode": "database_failure"})
    assert response.status_code == 200

    response = client.get("/api/v1/inventory/sku-001")

    assert response.status_code == 503
    assert response.json()["detail"] == {
        "message": "Inventory data store is unavailable",
        "service": "inventory-api",
    }


def test_reset_to_none_restores_inventory_response() -> None:
    client.put(FAULT_PATH, json={"mode": "database_failure"})

    failed_response = client.get("/api/v1/inventory/sku-001")
    assert failed_response.status_code == 503

    reset_response = client.put(FAULT_PATH, json={"mode": "none"})
    assert reset_response.status_code == 200

    recovered_response = client.get("/api/v1/inventory/sku-001")
    assert recovered_response.status_code == 200


@pytest.mark.parametrize(
    ("mode", "expected_delay"),
    [
        (
            InventoryFaultMode.HIGH_LATENCY,
            FAULT_PROFILES[
                InventoryFaultMode.HIGH_LATENCY
            ].delay_seconds,
        ),
        (
            InventoryFaultMode.API_TIMEOUT,
            FAULT_PROFILES[
                InventoryFaultMode.API_TIMEOUT
            ].delay_seconds,
        ),
    ],
)
def test_delay_faults_use_fixed_profiles(
    mode: InventoryFaultMode,
    expected_delay: float,
) -> None:
    recorded_delays: list[float] = []

    async def record_sleep(delay_seconds: float) -> None:
        recorded_delays.append(delay_seconds)

    with TestClient(create_app(sleeper=record_sleep)) as local_client:
        response = local_client.put(
            FAULT_PATH,
            json={"mode": mode.value},
        )
        assert response.status_code == 200

        response = local_client.get("/api/v1/inventory/sku-001")

    assert response.status_code == 200
    assert recorded_delays == [expected_delay]
