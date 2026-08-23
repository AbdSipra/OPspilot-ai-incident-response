from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

SERVICE_NAME = "inventory-api"

INVENTORY = {
    "sku-001": 12,
    "sku-002": 0,
    "sku-003": 30,
}


class HealthResponse(BaseModel):
    status: str
    service: str


class InventoryResponse(BaseModel):
    sku: str
    available: bool
    quantity: int = Field(ge=0)


app = FastAPI(
    title="OpsPilot Inventory API",
    version="0.1.0",
    description="Simulated downstream inventory service for OpsPilot.",
)


@app.get("/health", response_model=HealthResponse, tags=["health"])
async def health() -> HealthResponse:
    return HealthResponse(status="ok", service=SERVICE_NAME)


@app.get(
    "/api/v1/inventory/{sku}",
    response_model=InventoryResponse,
    tags=["inventory"],
)
async def get_inventory(sku: str) -> InventoryResponse:
    normalized_sku = sku.strip().lower()
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
