from asyncio import sleep
from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field

from inventory_api.faults import (
    FaultController,
    FaultSnapshot,
    InventoryFaultMode,
    SimulatedDatastoreFailure,
)

SERVICE_NAME = "inventory-api"

INVENTORY = {
    "sku-001": 12,
    "sku-002": 0,
    "sku-003": 30,
}

AsyncSleeper = Callable[[float], Awaitable[None]]


class HealthResponse(BaseModel):
    status: str
    service: str


class InventoryResponse(BaseModel):
    sku: str
    available: bool
    quantity: int = Field(ge=0)


class FaultUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: InventoryFaultMode


class FaultStatusResponse(BaseModel):
    service: str
    mode: InventoryFaultMode
    injected_delay_ms: int = Field(ge=0)
    changed_at: datetime


def get_fault_controller(request: Request) -> FaultController:
    return request.app.state.fault_controller


def get_sleeper(request: Request) -> AsyncSleeper:
    return request.app.state.sleeper


def to_fault_status(snapshot: FaultSnapshot) -> FaultStatusResponse:
    return FaultStatusResponse(
        service=SERVICE_NAME,
        mode=snapshot.mode,
        injected_delay_ms=int(snapshot.delay_seconds * 1_000),
        changed_at=snapshot.changed_at,
    )


def create_app(*, sleeper: AsyncSleeper = sleep) -> FastAPI:
    app = FastAPI(
        title="OpsPilot Inventory API",
        version="0.2.0",
        description="Simulated downstream inventory service for OpsPilot.",
    )

    app.state.fault_controller = FaultController()
    app.state.sleeper = sleeper

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
            FaultController,
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
            FaultController,
            Depends(get_fault_controller),
        ],
    ) -> FaultStatusResponse:
        return to_fault_status(controller.set_mode(body.mode))

    @app.get(
        "/api/v1/inventory/{sku}",
        response_model=InventoryResponse,
        tags=["inventory"],
    )
    async def get_inventory(
        sku: str,
        controller: Annotated[
            FaultController,
            Depends(get_fault_controller),
        ],
        request_sleeper: Annotated[
            AsyncSleeper,
            Depends(get_sleeper),
        ],
    ) -> InventoryResponse:
        normalized_sku = sku.strip().lower()
        snapshot = controller.snapshot()

        if snapshot.delay_seconds > 0:
            await request_sleeper(snapshot.delay_seconds)

        if snapshot.mode is InventoryFaultMode.DATABASE_FAILURE:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "message": "Inventory data store is unavailable",
                    "service": SERVICE_NAME,
                },
            ) from SimulatedDatastoreFailure()

        quantity = INVENTORY.get(normalized_sku)

        if quantity is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "SKU not found",
                    "sku": normalized_sku,
                },
            )

        return InventoryResponse(
            sku=normalized_sku,
            available=quantity > 0,
            quantity=quantity,
        )

    return app


app = create_app()
