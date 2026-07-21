from datetime import datetime

from pydantic import BaseModel, Field


class BookingCreate(BaseModel):
    seat_ids: list[int] = Field(min_length=1)


class EventCreate(BaseModel):
    location_id: int
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    category: str = Field(min_length=1, max_length=100)
    starts_at: datetime
    base_price: int = Field(gt=0)


class PaymentCreate(BaseModel):
    payment_method: str
    with_protection: bool = False
