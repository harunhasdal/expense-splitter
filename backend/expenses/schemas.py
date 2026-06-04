import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, model_validator

VALID_CURRENCIES = {
    "USD", "EUR", "GBP", "JPY", "AUD", "CAD", "CHF", "CNY", "SEK", "NZD",
    "MXN", "SGD", "HKD", "NOK", "KRW", "TRY", "INR", "RUB", "BRL", "ZAR",
}


class SplitDetail(BaseModel):
    member_id: uuid.UUID
    value: Decimal | None = None  # None for EQUAL split


class ExpenseCreate(BaseModel):
    description: str = Field(min_length=1, max_length=255)
    amount: Decimal = Field(gt=0)
    currency: str = Field(min_length=3, max_length=3)
    expense_date: date
    payer_id: uuid.UUID
    split_type: Literal["EQUAL", "EXACT", "PERCENTAGE", "RATIO"]
    split_details: list[SplitDetail] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_currency(self) -> "ExpenseCreate":
        if self.currency.upper() not in VALID_CURRENCIES:
            raise ValueError(f"Unsupported currency: {self.currency}")
        self.currency = self.currency.upper()
        return self


class SplitResponse(BaseModel):
    id: uuid.UUID
    member_id: uuid.UUID
    raw_value: Decimal | None
    computed_amount: Decimal

    model_config = {"from_attributes": True}


class ExpenseResponse(BaseModel):
    id: uuid.UUID
    group_id: uuid.UUID
    payer_id: uuid.UUID
    description: str
    amount: Decimal
    currency: str
    expense_date: date
    split_type: str
    created_at: datetime
    archived_at: datetime | None
    splits: list[SplitResponse] = []

    model_config = {"from_attributes": True}


class ExpensePage(BaseModel):
    items: list[ExpenseResponse]
    total: int
    page: int
    page_size: int
