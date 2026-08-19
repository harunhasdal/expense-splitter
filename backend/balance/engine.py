"""
Balance Engine — pure computation module.
No imports from FastAPI, SQLAlchemy, or any other backend module.
All monetary values use Decimal for exact arithmetic.
"""
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from enum import Enum
from uuid import UUID

CENT = Decimal("0.01")
ZERO = Decimal("0")
HUNDRED = Decimal("100")


class SplitType(str, Enum):
    EQUAL = "EQUAL"
    EXACT = "EXACT"
    PERCENTAGE = "PERCENTAGE"
    RATIO = "RATIO"


@dataclass
class SplitDetail:
    member_id: UUID
    value: Decimal | None  # None for EQUAL; amount/pct/ratio for others


@dataclass
class MemberShare:
    member_id: UUID
    raw_value: Decimal | None
    computed_amount: Decimal


@dataclass
class ValidationResult:
    valid: bool
    errors: list[str]


@dataclass
class MemberBalance:
    member_id: UUID
    net_amount: Decimal  # positive = owed to; negative = owes


@dataclass
class SettlementSuggestion:
    payer_id: UUID
    payee_id: UUID
    amount: Decimal
    currency: str


BalanceMap = dict[str, list[MemberBalance]]
SuggestionMap = dict[str, list[SettlementSuggestion]]


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_split(
    split_type: SplitType,
    total_amount: Decimal,
    member_ids: list[UUID],
    split_details: list[SplitDetail],
) -> ValidationResult:
    errors: list[str] = []

    if not member_ids:
        errors.append("At least one member is required")
        return ValidationResult(False, errors)

    if total_amount <= ZERO:
        errors.append("Total amount must be greater than zero")

    if len(split_details) != len(member_ids):
        errors.append(
            f"Split details count ({len(split_details)}) must match "
            f"member count ({len(member_ids)})"
        )
        return ValidationResult(False, errors)

    if split_type == SplitType.EQUAL:
        pass  # no value constraints

    elif split_type == SplitType.EXACT:
        for sd in split_details:
            if sd.value is None or sd.value < ZERO:
                errors.append(f"Member {sd.member_id}: exact amount must be >= 0")
        if not errors:
            total_split = sum(sd.value for sd in split_details if sd.value is not None)
            if abs(total_split - total_amount) > CENT:
                errors.append(
                    f"Split amounts ({total_split}) must equal total amount ({total_amount})"
                )

    elif split_type == SplitType.PERCENTAGE:
        for sd in split_details:
            if sd.value is None or sd.value < ZERO or sd.value > HUNDRED:
                errors.append(f"Member {sd.member_id}: percentage must be in [0, 100]")
        if not errors:
            total_pct = sum(sd.value for sd in split_details if sd.value is not None)
            if abs(total_pct - HUNDRED) > CENT:
                errors.append(f"Percentages must sum to 100 (got {total_pct})")

    elif split_type == SplitType.RATIO:
        for sd in split_details:
            if sd.value is None or sd.value < ZERO:
                errors.append(f"Member {sd.member_id}: ratio must be >= 0")
        if not errors:
            total_ratio = sum(sd.value for sd in split_details if sd.value is not None)
            if total_ratio <= ZERO:
                errors.append("At least one member must have a non-zero ratio")

    return ValidationResult(len(errors) == 0, errors)


# ---------------------------------------------------------------------------
# Share computation
# ---------------------------------------------------------------------------

def compute_shares(
    split_type: SplitType,
    total_amount: Decimal,
    member_ids: list[UUID],
    split_details: list[SplitDetail],
) -> list[MemberShare]:
    """Compute per-member monetary shares. Caller must validate first."""
    if split_type == SplitType.EQUAL:
        return _compute_equal(total_amount, member_ids)
    elif split_type == SplitType.EXACT:
        return _compute_exact(split_details)
    elif split_type == SplitType.PERCENTAGE:
        return _compute_percentage(total_amount, split_details)
    elif split_type == SplitType.RATIO:
        return _compute_ratio(total_amount, split_details)
    raise ValueError(f"Unknown split type: {split_type}")


def _compute_equal(total_amount: Decimal, member_ids: list[UUID]) -> list[MemberShare]:
    n = len(member_ids)
    base = (total_amount / n).quantize(CENT, rounding=ROUND_HALF_UP)
    # Recalculate base with truncation to avoid over-distribution
    base = (total_amount / n).quantize(CENT, rounding="ROUND_DOWN")
    remainder_cents = int((total_amount - base * n) * 100)

    # Stable ordering: sort by UUID string for determinism
    sorted_ids = sorted(member_ids, key=lambda uid: str(uid))

    shares = []
    for i, member_id in enumerate(sorted_ids):
        extra = CENT if i < remainder_cents else ZERO
        shares.append(MemberShare(member_id, None, base + extra))
    return shares


def _compute_exact(split_details: list[SplitDetail]) -> list[MemberShare]:
    return [
        MemberShare(sd.member_id, sd.value, sd.value or ZERO)
        for sd in split_details
    ]


def _compute_percentage(
    total_amount: Decimal, split_details: list[SplitDetail]
) -> list[MemberShare]:
    shares: list[MemberShare] = []
    running = ZERO
    non_zero = [sd for sd in split_details if (sd.value or ZERO) > ZERO]
    zero_members = [sd for sd in split_details if (sd.value or ZERO) <= ZERO]

    for i, sd in enumerate(non_zero):
        pct = sd.value or ZERO
        if i == len(non_zero) - 1:
            amount = total_amount - running
        else:
            amount = (pct / HUNDRED * total_amount).quantize(CENT, rounding=ROUND_HALF_UP)
            running += amount
        shares.append(MemberShare(sd.member_id, sd.value, amount))

    for sd in zero_members:
        shares.append(MemberShare(sd.member_id, ZERO, ZERO))

    return shares


def _compute_ratio(
    total_amount: Decimal, split_details: list[SplitDetail]
) -> list[MemberShare]:
    total_ratio = sum(sd.value or ZERO for sd in split_details)
    shares: list[MemberShare] = []
    running = ZERO
    non_zero = [sd for sd in split_details if (sd.value or ZERO) > ZERO]
    zero_members = [sd for sd in split_details if (sd.value or ZERO) <= ZERO]

    for i, sd in enumerate(non_zero):
        ratio = sd.value or ZERO
        if i == len(non_zero) - 1:
            amount = total_amount - running
        else:
            amount = (ratio / total_ratio * total_amount).quantize(CENT, rounding=ROUND_HALF_UP)
            running += amount
        shares.append(MemberShare(sd.member_id, sd.value, amount))

    for sd in zero_members:
        shares.append(MemberShare(sd.member_id, ZERO, ZERO))

    return shares


# ---------------------------------------------------------------------------
# Balance aggregation
# ---------------------------------------------------------------------------

@dataclass
class _ExpenseInput:
    payer_member_id: UUID
    currency: str
    splits: list[tuple[UUID, Decimal]]


@dataclass
class _SettlementInput:
    payer_member_id: UUID
    payee_member_id: UUID
    currency: str
    amount: Decimal


def aggregate_balances(
    expenses: list[_ExpenseInput],
    settlements: list[_SettlementInput],
) -> BalanceMap:
    """
    Compute net balances per member per currency.
    Invariant: sum(net_amount) == 0 for each currency.
    """
    raw: dict[str, dict[UUID, Decimal]] = {}

    for exp in expenses:
        cur = exp.currency
        if cur not in raw:
            raw[cur] = {}
        total = sum(amount for _, amount in exp.splits)
        raw[cur][exp.payer_member_id] = raw[cur].get(exp.payer_member_id, ZERO) + total
        for member_id, amount in exp.splits:
            raw[cur][member_id] = raw[cur].get(member_id, ZERO) - amount

    for stl in settlements:
        cur = stl.currency
        if cur not in raw:
            raw[cur] = {}
        raw[cur][stl.payer_member_id] = raw[cur].get(stl.payer_member_id, ZERO) + stl.amount
        raw[cur][stl.payee_member_id] = raw[cur].get(stl.payee_member_id, ZERO) - stl.amount

    return {
        currency: [
            MemberBalance(member_id, net)
            for member_id, net in balances.items()
        ]
        for currency, balances in raw.items()
    }


# ---------------------------------------------------------------------------
# Debt simplification
# ---------------------------------------------------------------------------

def simplify_debts(balances: BalanceMap) -> SuggestionMap:
    """
    Produce the minimum set of transfers to settle all debts.
    Uses greedy creditor-debtor matching (O(n log n)).
    Invariant: applying all suggestions to balances yields zero net for all members.
    """
    result: SuggestionMap = {}

    for currency, member_balances in balances.items():
        active = [b for b in member_balances if abs(b.net_amount) >= CENT]
        creditors = sorted(
            [b for b in active if b.net_amount > ZERO],
            key=lambda b: b.net_amount, reverse=True,
        )
        debtors = sorted(
            [b for b in active if b.net_amount < ZERO],
            key=lambda b: b.net_amount,  # most negative first
        )

        suggestions: list[SettlementSuggestion] = []
        while creditors and debtors:
            credit = creditors[0].net_amount
            debt = abs(debtors[0].net_amount)
            payment = min(credit, debt)

            suggestions.append(SettlementSuggestion(
                payer_id=debtors[0].member_id,
                payee_id=creditors[0].member_id,
                amount=payment,
                currency=currency,
            ))

            new_credit = credit - payment
            new_debt = debt - payment

            if new_credit < CENT:
                creditors.pop(0)
            else:
                creditors[0] = MemberBalance(creditors[0].member_id, new_credit)
                creditors.sort(key=lambda b: b.net_amount, reverse=True)

            if new_debt < CENT:
                debtors.pop(0)
            else:
                debtors[0] = MemberBalance(debtors[0].member_id, -new_debt)
                debtors.sort(key=lambda b: b.net_amount)

        result[currency] = suggestions

    return result


# Export the input types needed by service.py
ExpenseInput = _ExpenseInput
SettlementInput = _SettlementInput
