import uuid
from decimal import Decimal

from pydantic import BaseModel


class MemberBalance(BaseModel):
    member_id: uuid.UUID
    display_name: str
    net_amount: Decimal


class SettlementSuggestion(BaseModel):
    payer_id: uuid.UUID
    payer_name: str
    payee_id: uuid.UUID
    payee_name: str
    amount: Decimal
    currency: str


class CurrencyBalances(BaseModel):
    balances: dict[str, list[MemberBalance]]  # keyed by ISO currency


class CurrencySettlements(BaseModel):
    suggestions: dict[str, list[SettlementSuggestion]]  # keyed by ISO currency
