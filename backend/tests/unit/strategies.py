"""Hypothesis domain generators for Balance Engine PBT tests."""
import uuid
from decimal import Decimal

from hypothesis import strategies as st
from hypothesis.strategies import SearchStrategy, composite

from balance.engine import (
    ExpenseInput,
    MemberBalance,
    SettlementInput,
    SplitDetail,
    SplitType,
)


@composite
def monetary_amounts(draw: st.DrawFn) -> Decimal:
    """Realistic expense amounts: 0.01 to 9999.99."""
    cents = draw(st.integers(min_value=1, max_value=999999))
    return Decimal(cents) / 100


@composite
def member_id_list(draw: st.DrawFn, min_size: int = 1, max_size: int = 8) -> list[uuid.UUID]:
    return draw(
        st.lists(
            st.uuids(),
            min_size=min_size,
            max_size=max_size,
            unique=True,
        )
    )


@composite
def equal_split_input(draw: st.DrawFn) -> tuple[Decimal, list[uuid.UUID], list[SplitDetail]]:
    total = draw(monetary_amounts())
    members = draw(member_id_list())
    details = [SplitDetail(m, None) for m in members]
    return total, members, details


@composite
def exact_split_input(draw: st.DrawFn) -> tuple[Decimal, list[uuid.UUID], list[SplitDetail]]:
    """Generate a valid exact split where shares sum to total."""
    members = draw(member_id_list(min_size=2, max_size=6))
    n = len(members)
    # Generate shares as cents that sum to a total
    total_cents = draw(st.integers(min_value=n, max_value=99999))
    # Split total_cents into n non-negative parts
    cuts = sorted(draw(st.lists(
        st.integers(min_value=0, max_value=total_cents),
        min_size=n - 1, max_size=n - 1,
    )))
    cuts = [0] + cuts + [total_cents]
    shares_cents = [cuts[i + 1] - cuts[i] for i in range(n)]
    total = Decimal(total_cents) / 100
    details = [SplitDetail(m, Decimal(c) / 100) for m, c in zip(members, shares_cents)]
    return total, members, details


@composite
def percentage_split_input(draw: st.DrawFn) -> tuple[Decimal, list[uuid.UUID], list[SplitDetail]]:
    """Generate a valid percentage split that sums to exactly 100."""
    total = draw(monetary_amounts())
    members = draw(member_id_list(min_size=1, max_size=6))
    n = len(members)
    # Generate percentage points (integers) summing to 100
    cuts = sorted(draw(st.lists(
        st.integers(min_value=0, max_value=100),
        min_size=n - 1, max_size=n - 1,
    )))
    cuts = [0] + cuts + [100]
    pcts = [cuts[i + 1] - cuts[i] for i in range(n)]
    details = [SplitDetail(m, Decimal(p)) for m, p in zip(members, pcts)]
    return total, members, details


@composite
def ratio_split_input(draw: st.DrawFn) -> tuple[Decimal, list[uuid.UUID], list[SplitDetail]]:
    """Generate a valid ratio split with at least one non-zero ratio."""
    total = draw(monetary_amounts())
    members = draw(member_id_list(min_size=1, max_size=6))
    ratios = draw(st.lists(
        st.integers(min_value=0, max_value=10),
        min_size=len(members),
        max_size=len(members),
    ))
    # Ensure at least one non-zero
    if all(r == 0 for r in ratios):
        ratios[0] = 1
    details = [SplitDetail(m, Decimal(r)) for m, r in zip(members, ratios)]
    return total, members, details


@composite
def expense_input(draw: st.DrawFn) -> ExpenseInput:
    """Generate a realistic expense with an equal split."""
    currency = draw(st.sampled_from(["GBP", "USD", "EUR", "JPY"]))
    total, members, details = draw(equal_split_input())
    from balance.engine import SplitType, compute_shares
    shares_list = compute_shares(SplitType.EQUAL, total, members, details)
    payer = draw(st.sampled_from(members))
    return ExpenseInput(
        payer_member_id=payer,
        currency=currency,
        splits=[(s.member_id, s.computed_amount) for s in shares_list],
    )


@composite
def settlement_input(draw: st.DrawFn, members: list[uuid.UUID], currency: str) -> SettlementInput:
    """Generate a settlement between two distinct members."""
    if len(members) < 2:
        payer = members[0]
        payee = members[0]  # degenerate — filtered in tests
    else:
        payer, payee = draw(st.sampled_from(
            [(a, b) for i, a in enumerate(members) for j, b in enumerate(members) if i != j]
        ))
    amount = draw(monetary_amounts())
    return SettlementInput(payer, payee, currency, amount)


@composite
def balance_map_input(draw: st.DrawFn) -> dict[str, list[MemberBalance]]:
    """Generate a balance map where each currency sums to zero."""
    currencies = draw(st.lists(
        st.sampled_from(["GBP", "USD", "EUR"]),
        min_size=1, max_size=2, unique=True,
    ))
    result = {}
    for currency in currencies:
        members = draw(member_id_list(min_size=2, max_size=6))
        # Generate n-1 random balances, last is negated sum
        n = len(members)
        amounts = [
            Decimal(draw(st.integers(min_value=-10000, max_value=10000))) / 100
            for _ in range(n - 1)
        ]
        last = -sum(amounts)
        all_amounts = amounts + [last]
        result[currency] = [MemberBalance(m, a) for m, a in zip(members, all_amounts)]
    return result
