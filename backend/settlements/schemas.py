import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator

from expenses.schemas import VALID_CURRENCIES


class SettlementCreate(BaseModel):
    payer_id: uuid.UUID
    payee_id: uuid.UUID
    amount: Decimal = Field(gt=0)
    currency: str = Field(min_length=3, max_length=3)

    @model_validator(mode="after")
    def validate_fields(self) -> "SettlementCreate":
        if self.payer_id == self.payee_id:
            raise ValueError("Payer and payee must be different members")
        if self.currency.upper() not in VALID_CURRENCIES:
            raise ValueError(f"Unsupported currency: {self.currency}")
        self.currency = self.currency.upper()
        return self


class SettlementResponse(BaseModel):
    id: uuid.UUID
    group_id: uuid.UUID
    payer_id: uuid.UUID
    payee_id: uuid.UUID
    amount: Decimal
    currency: str
    recorded_at: datetime

    model_config = {"from_attributes": True}
