import os
from collections.abc import Awaitable, Callable
from typing import Annotated

import httpx
from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel, Field

SERVICE_NAME = "orders-api"
INVENTORY_BASE_URL = os.getenv("INVENTORY_BASE_URL", "http://127.0.0.1:8002")
INVENTORY_TIMEOUT_SECONDS = float(
    os.getenv("INVENTORY_TIMEOUT_SECONDS", "1.0")
)


class HealthResponse(BaseModel):
    status: str
    service: str


class InventoryItem(BaseModel):
    sku: str
    available: bool
    quantity: int = Field(ge=0)


class OrderPreviewResponse(BaseModel):
    sku: str
    can_place_order: bool
    inventory: InventoryItem


InventoryFetcher = Callable[[str], Awaitable[InventoryItem]]


app = FastAPI(
    title="OpsPilot Orders API",
    version="0.1.0",
    description="Simulated order service for OpsPilot.",
)


@app.get("/health", response_model=HealthResponse, tags=["health"])
async def health() -> HealthResponse:
    return HealthResponse(status="ok", service=SERVICE_NAME)


async def fetch_inventory(sku: str) -> InventoryItem:
    inventory_url = (
        f"{INVENTORY_BASE_URL.rstrip('/')}/api/v1/inventory/{sku}"
    )

    try:
        async with httpx.AsyncClient(
            timeout=INVENTORY_TIMEOUT_SECONDS
        ) as client:
            response = await client.get(inventory_url)
            response.raise_for_status()
    except httpx.TimeoutException as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail={
                "message": "Inventory service timed out",
                "service": "inventory-api",
            },
        ) from exc
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == status.HTTP_404_NOT_FOUND:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "SKU not found in inventory",
                    "sku": sku,
                },
            ) from exc

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "message": "Inventory service returned an error",
                "service": "inventory-api",
            },
        ) from exc
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "message": "Inventory service is unavailable",
                "service": "inventory-api",
            },
        ) from exc

    return InventoryItem.model_validate(response.json())


async def get_inventory_fetcher() -> InventoryFetcher:
    return fetch_inventory


@app.get(
    "/api/v1/orders/preview/{sku}",
    response_model=OrderPreviewResponse,
    tags=["orders"],
)
async def preview_order(
    sku: str,
    inventory_fetcher: Annotated[
        InventoryFetcher,
        Depends(get_inventory_fetcher),
    ],
) -> OrderPreviewResponse:
    normalized_sku = sku.strip().lower()
    inventory = await inventory_fetcher(normalized_sku)

    return OrderPreviewResponse(
        sku=normalized_sku,
        can_place_order=inventory.available,
        inventory=inventory,
    )
