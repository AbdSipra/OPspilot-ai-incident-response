import os
from collections.abc import Awaitable, Callable
from typing import Annotated

import httpx
from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel, Field

SERVICE_NAME = "edge-api"
ORDERS_BASE_URL = os.getenv("ORDERS_BASE_URL", "http://127.0.0.1:8001")
ORDERS_TIMEOUT_SECONDS = float(
    os.getenv("ORDERS_TIMEOUT_SECONDS", "3.0")
)


class HealthResponse(BaseModel):
    status: str
    service: str


class InventoryItem(BaseModel):
    sku: str
    available: bool
    quantity: int = Field(ge=0)


class OrderPreview(BaseModel):
    sku: str
    can_place_order: bool
    inventory: InventoryItem


class CheckoutResponse(BaseModel):
    sku: str
    checkout_available: bool
    order_preview: OrderPreview


OrderPreviewFetcher = Callable[[str], Awaitable[OrderPreview]]


app = FastAPI(
    title="OpsPilot Edge API",
    version="0.1.0",
    description="Simulated customer-facing entry point for OpsPilot.",
)


@app.get("/health", response_model=HealthResponse, tags=["health"])
async def health() -> HealthResponse:
    return HealthResponse(status="ok", service=SERVICE_NAME)


async def fetch_order_preview(sku: str) -> OrderPreview:
    orders_url = f"{ORDERS_BASE_URL.rstrip('/')}/api/v1/orders/preview/{sku}"

    try:
        async with httpx.AsyncClient(
            timeout=ORDERS_TIMEOUT_SECONDS
        ) as client:
            response = await client.get(orders_url)
            response.raise_for_status()
    except httpx.TimeoutException as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail={
                "message": "Orders service timed out",
                "service": "orders-api",
            },
        ) from exc
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == status.HTTP_404_NOT_FOUND:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "SKU not found while creating checkout preview",
                    "sku": sku,
                },
            ) from exc

        raise HTTPException(
            status_code=exc.response.status_code,
            detail={
                "message": "Orders service returned an error",
                "service": "orders-api",
                "upstream_status": exc.response.status_code,
            },
        ) from exc
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "message": "Orders service is unavailable",
                "service": "orders-api",
            },
        ) from exc

    return OrderPreview.model_validate(response.json())


async def get_order_preview_fetcher() -> OrderPreviewFetcher:
    return fetch_order_preview


@app.get(
    "/api/v1/checkout/{sku}",
    response_model=CheckoutResponse,
    tags=["checkout"],
)
async def checkout(
    sku: str,
    order_preview_fetcher: Annotated[
        OrderPreviewFetcher,
        Depends(get_order_preview_fetcher),
    ],
) -> CheckoutResponse:
    normalized_sku = sku.strip().lower()
    order_preview = await order_preview_fetcher(normalized_sku)

    return CheckoutResponse(
        sku=normalized_sku,
        checkout_available=order_preview.can_place_order,
        order_preview=order_preview,
    )
