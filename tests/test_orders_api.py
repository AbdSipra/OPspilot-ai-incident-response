from pathlib import Path
import sys

from fastapi import HTTPException
from fastapi.testclient import TestClient

SERVICE_ROOT = Path(__file__).resolve().parents[1] / "apps" / "orders-api"
sys.path.insert(0, str(SERVICE_ROOT))

from orders_api.main import (
    InventoryItem,
    app,
    get_inventory_fetcher,
)

client = TestClient(app)


def test_health_returns_service_status() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "orders-api",
    }


def test_order_preview_for_available_item() -> None:
    async def fake_inventory_fetcher(sku: str) -> InventoryItem:
        return InventoryItem(
            sku=sku,
            available=True,
            quantity=12,
        )

    app.dependency_overrides[get_inventory_fetcher] = (
        lambda: fake_inventory_fetcher
    )

    try:
        response = client.get("/api/v1/orders/preview/sku-001")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "sku": "sku-001",
        "can_place_order": True,
        "inventory": {
            "sku": "sku-001",
            "available": True,
            "quantity": 12,
        },
    }


def test_order_preview_returns_downstream_failure() -> None:
    async def unavailable_inventory_fetcher(
        sku: str,
    ) -> InventoryItem:
        raise HTTPException(
            status_code=503,
            detail={
                "message": "Inventory service is unavailable",
                "service": "inventory-api",
            },
        )

    app.dependency_overrides[get_inventory_fetcher] = (
        lambda: unavailable_inventory_fetcher
    )

    try:
        response = client.get("/api/v1/orders/preview/sku-001")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json()["detail"]["service"] == "inventory-api"
