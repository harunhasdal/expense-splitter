import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from auth.middleware import get_current_user
from auth.models import User
from core.db import get_db
from expenses import service as expense_service
from expenses.schemas import ExpenseCreate, ExpensePage, ExpenseResponse

router = APIRouter()


@router.post("/{group_id}/expenses", response_model=ExpenseResponse, status_code=201)
async def create_expense(
    group_id: uuid.UUID,
    body: ExpenseCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ExpenseResponse:
    expense = await expense_service.create_expense(db, group_id, current_user, body)
    return ExpenseResponse.model_validate(expense)


@router.get("/{group_id}/expenses", response_model=ExpensePage)
async def list_expenses(
    group_id: uuid.UUID,
    payer_id: uuid.UUID | None = None,
    include_archived: bool = False,
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ExpensePage:
    page_size = min(page_size, 100)
    return await expense_service.list_expenses(
        db, group_id, current_user.id, payer_id, include_archived, page, page_size
    )


@router.get("/{group_id}/expenses/{expense_id}", response_model=ExpenseResponse)
async def get_expense(
    group_id: uuid.UUID,
    expense_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ExpenseResponse:
    from groups import repository as group_repo
    member = await group_repo.get_active_member(db, group_id, current_user.id)
    if not member:
        raise ValueError("Not a member")
    from expenses import repository as expense_repo
    expense = await expense_repo.get_by_id(db, expense_id)
    if not expense or expense.group_id != group_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Expense not found")
    return ExpenseResponse.model_validate(expense)


@router.patch("/{group_id}/expenses/{expense_id}", response_model=ExpenseResponse)
async def archive_expense(
    group_id: uuid.UUID,
    expense_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ExpenseResponse:
    expense = await expense_service.archive_expense(db, group_id, expense_id, current_user)
    return ExpenseResponse.model_validate(expense)


@router.put("/{group_id}/expenses/{expense_id}")
async def update_expense_blocked() -> JSONResponse:
    return JSONResponse({"error": "Expenses are immutable after creation"}, status_code=405)


@router.delete("/{group_id}/expenses/{expense_id}")
async def delete_expense_blocked() -> JSONResponse:
    return JSONResponse({"error": "Expenses are immutable after creation"}, status_code=405)
