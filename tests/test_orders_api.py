from collections.abc import Generator
from pathlib import Path
import sys

import pytest
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


def test_fault_status_defaults_to_none() -> None:
    response = client.get(FAULT_PATH)

    assert response.status_code == 200
    assert response.json()["mode"] == "none"


def test_fault_control_rejects_invalid_requests() -> None:
    unknown_mode_response = client.put(
        FAULT_PATH,
        json={"mode": "arbitrary-command"},
    )
    extra_field_response = client.put(
        FAULT_PATH,
        json={
            "mode": "none",
            "inventory_url": "http://untrusted.example",
        },
    )

    assert unknown_mode_response.status_code == 422
    assert extra_field_response.status_code == 422


def test_bad_configuration_fails_before_inventory_request() -> None:
    async def unexpected_inventory_fetcher(sku: str) -> InventoryItem:
        raise AssertionError("The inventory fetcher should not be called")

    app.dependency_overrides[get_inventory_fetcher] = (
        lambda: unexpected_inventory_fetcher
    )

    try:
        response = client.put(
            FAULT_PATH,
            json={"mode": "bad_configuration"},
        )
        assert response.status_code == 200

        response = client.get("/api/v1/orders/preview/sku-001")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 500
    assert response.json()["detail"] == {
        "message": "Inventory service configuration is invalid",
        "service": "orders-api",
    }


def test_reset_to_none_restores_order_preview() -> None:
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
        client.put(FAULT_PATH, json={"mode": "bad_configuration"})

        failed_response = client.get("/api/v1/orders/preview/sku-001")
        assert failed_response.status_code == 500

        reset_response = client.put(FAULT_PATH, json={"mode": "none"})
        assert reset_response.status_code == 200

        recovered_response = client.get("/api/v1/orders/preview/sku-001")
    finally:
        app.dependency_overrides.clear()

    assert recovered_response.status_code == 200
