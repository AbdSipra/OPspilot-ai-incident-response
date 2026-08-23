from pathlib import Path
import sys

from fastapi.testclient import TestClient

SERVICE_ROOT = Path(__file__).resolve().parents[1] / "apps" / "inventory-api"
sys.path.insert(0, str(SERVICE_ROOT))

from inventory_api.main import app

client = TestClient(app)


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
