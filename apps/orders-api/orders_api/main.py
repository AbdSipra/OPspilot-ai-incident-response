import os
from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Annotated

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field

from orders_api.faults import (
    FaultSnapshot,
    OrdersFaultController,
    OrdersFaultMode,
)

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


class FaultUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: OrdersFaultMode


class FaultStatusResponse(BaseModel):
    service: str
    mode: OrdersFaultMode
    changed_at: datetime


InventoryFetcher = Callable[[str], Awaitable[InventoryItem]]


def get_fault_controller(request: Request) -> OrdersFaultController:
    return request.app.state.fault_controller


def to_fault_status(snapshot: FaultSnapshot) -> FaultStatusResponse:
    return FaultStatusResponse(
        service=SERVICE_NAME,
        mode=snapshot.mode,
        changed_at=snapshot.changed_at,
    )


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


def create_app() -> FastAPI:
    app = FastAPI(
        title="OpsPilot Orders API",
        version="0.2.0",
        description="Simulated order service for OpsPilot.",
    )

    app.state.fault_controller = OrdersFaultController()

    @app.get("/health", response_model=HealthResponse, tags=["health"])
    async def health() -> HealthResponse:
        return HealthResponse(status="ok", service=SERVICE_NAME)

    @app.get(
        "/internal/simulation/fault",
        response_model=FaultStatusResponse,
        tags=["simulation-control"],
    )
    async def get_fault_status(
        controller: Annotated[
            OrdersFaultController,
            Depends(get_fault_controller),
        ],
    ) -> FaultStatusResponse:
        return to_fault_status(controller.snapshot())

    @app.put(
        "/internal/simulation/fault",
        response_model=FaultStatusResponse,
        tags=["simulation-control"],
    )
    async def set_fault_status(
        body: FaultUpdateRequest,
        controller: Annotated[
            OrdersFaultController,
            Depends(get_fault_controller),
        ],
    ) -> FaultStatusResponse:
        return to_fault_status(controller.set_mode(body.mode))

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
        controller: Annotated[
            OrdersFaultController,
            Depends(get_fault_controller),
        ],
    ) -> OrderPreviewResponse:
        normalized_sku = sku.strip().lower()
        snapshot = controller.snapshot()

        if snapshot.mode is OrdersFaultMode.BAD_CONFIGURATION:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "message": "Inventory service configuration is invalid",
                    "service": SERVICE_NAME,
                },
            )

        inventory = await inventory_fetcher(normalized_sku)

        return OrderPreviewResponse(
            sku=normalized_sku,
            can_place_order=inventory.available,
            inventory=inventory,
        )

    return app


app = create_app()
