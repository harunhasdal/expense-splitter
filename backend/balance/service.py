"""Balance service — loads data from repositories and delegates to the pure engine."""
import uuid
from decimal import Decimal

import structlog
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from balance.engine import (
    ExpenseInput,
    MemberBalance,
    SettlementInput,
    SuggestionMap,
    aggregate_balances,
    simplify_debts,
)
from expenses import repository as expense_repo
from groups import repository as group_repo
from settlements import repository as settlement_repo

logger = structlog.get_logger()


async def _check_membership(db: AsyncSession, group_id: uuid.UUID, user_id: uuid.UUID) -> None:
    if not await group_repo.get_active_member(db, group_id, user_id):
        raise HTTPException(status_code=404, detail="Group not found")


async def get_balances(
    db: AsyncSession, group_id: uuid.UUID, user_id: uuid.UUID
) -> dict[str, list[MemberBalance]]:
    await _check_membership(db, group_id, user_id)

    expense_records = await expense_repo.get_all_for_balance(db, group_id)
    settlement_records = await settlement_repo.get_all_for_balance(db, group_id)

    expenses = [
        ExpenseInput(
            payer_member_id=er.payer_member_id,
            currency=er.currency,
            splits=er.splits,
        )
        for er in expense_records
    ]
    settlements = [
        SettlementInput(
            payer_member_id=sr.payer_member_id,
            payee_member_id=sr.payee_member_id,
            currency=sr.currency,
            amount=sr.amount,
        )
        for sr in settlement_records
    ]

    return aggregate_balances(expenses, settlements)


async def get_settlement_suggestions(
    db: AsyncSession, group_id: uuid.UUID, user_id: uuid.UUID
) -> SuggestionMap:
    balances = await get_balances(db, group_id, user_id)
    return simplify_debts(balances)


async def get_raw_balances(
    db: AsyncSession, group_id: uuid.UUID
) -> dict[str, dict[uuid.UUID, Decimal]]:
    """Raw balance map keyed by currency then member_id. Used by group/member guards."""
    expense_records = await expense_repo.get_all_for_balance(db, group_id)
    settlement_records = await settlement_repo.get_all_for_balance(db, group_id)

    expenses = [
        ExpenseInput(er.payer_member_id, er.currency, er.splits) for er in expense_records
    ]
    settlements = [
        SettlementInput(sr.payer_member_id, sr.payee_member_id, sr.currency, sr.amount)
        for sr in settlement_records
    ]

    balance_map = aggregate_balances(expenses, settlements)
    return {
        currency: {b.member_id: b.net_amount for b in member_balances}
        for currency, member_balances in balance_map.items()
    }
