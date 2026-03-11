from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Currency(str, Enum):
    USD = "USD"
    BRL = "BRL"


class ProductCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    price_cents: int = Field(..., gt=0, description="Price in smallest currency unit")
    caffeine_mg: int = Field(..., ge=0, description="Caffeine content in milligrams")
    currency: Currency


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    price_cents: Optional[int] = Field(None, gt=0)
    caffeine_mg: Optional[int] = Field(None, ge=0)
    currency: Optional[Currency] = None


class ProductResponse(BaseModel):
    id: str
    name: str
    price_cents: int
    caffeine_mg: int
    caffeine_currency_ratio: float
    currency: Currency

    model_config = {"from_attributes": True}


class CaffeineLookupResult(BaseModel):
    name: str
    caffeine_mg: Optional[int] = None
    source: str


class ErrorResponse(BaseModel):
    detail: str
    status_code: int
    request_id: Optional[str] = None
