import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from auth.middleware import get_current_user
from auth.models import User
from balance.schemas import CurrencyBalances, CurrencySettlements
from core.db import get_db

router = APIRouter()


@router.get("/{group_id}/balances", response_model=CurrencyBalances)
async def get_balances(
    group_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    # Stub — balance engine implemented in Unit 2
    return JSONResponse({"balances": {}}, status_code=501)


@router.get("/{group_id}/settlements/suggestions", response_model=CurrencySettlements)
async def get_settlement_suggestions(
    group_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    # Stub — balance engine implemented in Unit 2
    return JSONResponse({"suggestions": {}}, status_code=501)
