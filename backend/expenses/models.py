import uuid
from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.db import Base


class Expense(Base):
    __tablename__ = "expenses"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    group_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("groups.id"), nullable=False)
    payer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("members.id"), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    expense_date: Mapped[date] = mapped_column(Date, nullable=False)
    split_type: Mapped[str] = mapped_column(
        Enum("EQUAL", "EXACT", "PERCENTAGE", "RATIO", name="split_type"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    archived_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    splits: Mapped[list["ExpenseSplit"]] = relationship("ExpenseSplit", back_populates="expense", lazy="selectin")


class ExpenseSplit(Base):
    __tablename__ = "expense_splits"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    expense_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("expenses.id"), nullable=False)
    member_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("members.id"), nullable=False)
    raw_value: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    computed_amount: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)

    expense: Mapped["Expense"] = relationship("Expense", back_populates="splits")
