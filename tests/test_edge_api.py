from pathlib import Path
import sys

from fastapi import HTTPException
from fastapi.testclient import TestClient

SERVICE_ROOT = Path(__file__).resolve().parents[1] / "apps" / "edge-api"
sys.path.insert(0, str(SERVICE_ROOT))

from edge_api.main import (
    InventoryItem,
    OrderPreview,
    app,
    get_order_preview_fetcher,
)

client = TestClient(app)


def test_health_returns_service_status() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "edge-api",
    }


def test_checkout_for_available_item() -> None:
    async def fake_order_preview_fetcher(sku: str) -> OrderPreview:
        return OrderPreview(
            sku=sku,
            can_place_order=True,
            inventory=InventoryItem(
                sku=sku,
                available=True,
                quantity=12,
            ),
        )

    app.dependency_overrides[get_order_preview_fetcher] = (
        lambda: fake_order_preview_fetcher
    )

    try:
        response = client.get("/api/v1/checkout/sku-001")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["checkout_available"] is True
    assert response.json()["order_preview"]["inventory"]["quantity"] == 12


def test_checkout_returns_orders_service_failure() -> None:
    async def unavailable_order_preview_fetcher(
        sku: str,
    ) -> OrderPreview:
        raise HTTPException(
            status_code=503,
            detail={
                "message": "Orders service is unavailable",
                "service": "orders-api",
            },
        )

    app.dependency_overrides[get_order_preview_fetcher] = (
        lambda: unavailable_order_preview_fetcher
    )

    try:
        response = client.get("/api/v1/checkout/sku-001")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json()["detail"]["service"] == "orders-api"
