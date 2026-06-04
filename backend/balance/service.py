"""Balance service — data loading orchestration. Engine wired in Unit 2."""
import uuid
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from expenses import repository as expense_repo
from settlements import repository as settlement_repo


async def get_raw_balances(
    db: AsyncSession, group_id: uuid.UUID
) -> dict[str, dict[uuid.UUID, Decimal]]:
    """Returns {currency: {member_id: net_amount}}. Stub until Unit 2 engine is wired."""
    expense_records = await expense_repo.get_all_for_balance(db, group_id)
    settlement_records = await settlement_repo.get_all_for_balance(db, group_id)

    # Will call BalanceEngine.aggregate_balances() once Unit 2 implements engine.py
    # Returning empty dict as placeholder stub
    _ = expense_records
    _ = settlement_records
    return {}
