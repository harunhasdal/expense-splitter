import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from auth.middleware import get_current_user
from auth.models import User
from balance import service as balance_service
from balance.schemas import CurrencyBalances, CurrencySettlements
from balance.schemas import MemberBalance as MemberBalanceSchema
from balance.schemas import SettlementSuggestion as SettlementSuggestionSchema
from core.db import get_db

router = APIRouter()


@router.get("/{group_id}/balances", response_model=CurrencyBalances)
async def get_balances(
    group_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CurrencyBalances:
    raw = await balance_service.get_balances(db, group_id, current_user.id)
    return CurrencyBalances(
        balances={
            currency: [
                MemberBalanceSchema(
                    member_id=b.member_id,
                    display_name="",
                    net_amount=b.net_amount,
                )
                for b in member_balances
            ]
            for currency, member_balances in raw.items()
        }
    )


@router.get("/{group_id}/settlements/suggestions", response_model=CurrencySettlements)
async def get_settlement_suggestions(
    group_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CurrencySettlements:
    raw = await balance_service.get_settlement_suggestions(db, group_id, current_user.id)
    return CurrencySettlements(
        suggestions={
            currency: [
                SettlementSuggestionSchema(
                    payer_id=s.payer_id,
                    payer_name="",
                    payee_id=s.payee_id,
                    payee_name="",
                    amount=s.amount,
                    currency=s.currency,
                )
                for s in suggestions
            ]
            for currency, suggestions in raw.items()
        }
    )
