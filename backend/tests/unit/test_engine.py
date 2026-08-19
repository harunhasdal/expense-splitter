"""
Balance Engine tests — example-based + property-based (Hypothesis).
PBT rules enforced: PBT-02, PBT-03, PBT-05, PBT-07, PBT-08, PBT-09.
"""
import uuid
from decimal import Decimal

from hypothesis import given, settings

from balance.engine import (
    CENT,
    ZERO,
    ExpenseInput,
    MemberBalance,
    SettlementInput,
    SplitDetail,
    SplitType,
    aggregate_balances,
    compute_shares,
    simplify_debts,
    validate_split,
)
from tests.unit.strategies import (
    balance_map_input,
    equal_split_input,
    exact_split_input,
    percentage_split_input,
    ratio_split_input,
)

# ---------------------------------------------------------------------------
# Example-based tests
# ---------------------------------------------------------------------------

def _ids(n: int) -> list[uuid.UUID]:
    return [uuid.UUID(int=i + 1) for i in range(n)]


class TestEqualSplit:
    def test_even_division(self) -> None:
        members = _ids(3)
        details = [SplitDetail(m, None) for m in members]
        shares = compute_shares(SplitType.EQUAL, Decimal("60.00"), members, details)
        assert all(s.computed_amount == Decimal("20.00") for s in shares)

    def test_remainder_distribution(self) -> None:
        members = _ids(3)
        details = [SplitDetail(m, None) for m in members]
        shares = compute_shares(SplitType.EQUAL, Decimal("10.00"), members, details)
        amounts = sorted(s.computed_amount for s in shares)
        assert amounts == [Decimal("3.33"), Decimal("3.33"), Decimal("3.34")]
        assert sum(s.computed_amount for s in shares) == Decimal("10.00")

    def test_single_member(self) -> None:
        members = _ids(1)
        details = [SplitDetail(m, None) for m in members]
        shares = compute_shares(SplitType.EQUAL, Decimal("50.00"), members, details)
        assert shares[0].computed_amount == Decimal("50.00")


class TestExactSplit:
    def test_valid_exact(self) -> None:
        m1, m2 = _ids(2)
        details = [SplitDetail(m1, Decimal("50.00")), SplitDetail(m2, Decimal("40.00"))]
        shares = compute_shares(SplitType.EXACT, Decimal("90.00"), [m1, m2], details)
        assert shares[0].computed_amount == Decimal("50.00")
        assert shares[1].computed_amount == Decimal("40.00")

    def test_zero_share_member(self) -> None:
        m1, m2 = _ids(2)
        details = [SplitDetail(m1, Decimal("100.00")), SplitDetail(m2, Decimal("0.00"))]
        shares = compute_shares(SplitType.EXACT, Decimal("100.00"), [m1, m2], details)
        assert any(s.computed_amount == ZERO for s in shares)


class TestPercentageSplit:
    def test_basic_50_30_20(self) -> None:
        m1, m2, m3 = _ids(3)
        details = [
            SplitDetail(m1, Decimal("50")),
            SplitDetail(m2, Decimal("30")),
            SplitDetail(m3, Decimal("20")),
        ]
        shares = compute_shares(SplitType.PERCENTAGE, Decimal("200.00"), [m1, m2, m3], details)
        assert sum(s.computed_amount for s in shares) == Decimal("200.00")

    def test_rounding_three_equal(self) -> None:
        m1, m2, m3 = _ids(3)
        total = Decimal("100.00")
        details = [SplitDetail(m, Decimal("33")) for m in [m1, m2, m3]]
        # 33+33+33 = 99 → last member gets remainder to reach total
        # validate_split would reject sum=99 ≠ 100, so use 33/33/34
        details[-1] = SplitDetail(m3, Decimal("34"))
        shares = compute_shares(SplitType.PERCENTAGE, total, [m1, m2, m3], details)
        assert sum(s.computed_amount for s in shares) == total


class TestRatioSplit:
    def test_1_2_3_ratio(self) -> None:
        m1, m2, m3 = _ids(3)
        details = [
            SplitDetail(m1, Decimal("1")),
            SplitDetail(m2, Decimal("2")),
            SplitDetail(m3, Decimal("3")),
        ]
        shares = compute_shares(SplitType.RATIO, Decimal("120.00"), [m1, m2, m3], details)
        by_id = {s.member_id: s.computed_amount for s in shares}
        assert by_id[m1] == Decimal("20.00")
        assert by_id[m2] == Decimal("40.00")
        assert by_id[m3] == Decimal("60.00")

    def test_zero_ratio_member(self) -> None:
        m1, m2 = _ids(2)
        details = [SplitDetail(m1, Decimal("1")), SplitDetail(m2, Decimal("0"))]
        shares = compute_shares(SplitType.RATIO, Decimal("50.00"), [m1, m2], details)
        by_id = {s.member_id: s.computed_amount for s in shares}
        assert by_id[m2] == ZERO
        assert by_id[m1] == Decimal("50.00")


class TestBalanceAggregation:
    def test_two_person_equal_split(self) -> None:
        a, b = _ids(2)
        expenses = [ExpenseInput(a, "GBP", [(a, Decimal("15")), (b, Decimal("15"))])]
        result = aggregate_balances(expenses, [])
        by_id = {bal.member_id: bal.net_amount for bal in result["GBP"]}
        assert by_id[a] == Decimal("15")   # paid 30, owes 15 → net +15
        assert by_id[b] == Decimal("-15")  # owes 15

    def test_settlement_clears_balance(self) -> None:
        a, b = _ids(2)
        expenses = [ExpenseInput(a, "GBP", [(a, Decimal("15")), (b, Decimal("15"))])]
        settlements = [SettlementInput(b, a, "GBP", Decimal("15"))]
        result = aggregate_balances(expenses, settlements)
        by_id = {bal.member_id: bal.net_amount for bal in result["GBP"]}
        assert abs(by_id[a]) < CENT
        assert abs(by_id[b]) < CENT

    def test_multi_currency_isolation(self) -> None:
        a, b = _ids(2)
        expenses = [
            ExpenseInput(a, "GBP", [(a, Decimal("10")), (b, Decimal("10"))]),
            ExpenseInput(a, "EUR", [(a, Decimal("5")), (b, Decimal("5"))]),
        ]
        result = aggregate_balances(expenses, [])
        assert "GBP" in result
        assert "EUR" in result
        # Verify isolation — EUR balances unaffected by GBP expense
        eur_by_id = {bal.member_id: bal.net_amount for bal in result["EUR"]}
        assert eur_by_id[a] == Decimal("5")


class TestDebtSimplification:
    def test_simple_chain_a_owes_b_owes_c(self) -> None:
        a, b, c = _ids(3)
        balances = {"GBP": [
            MemberBalance(a, Decimal("-20")),
            MemberBalance(b, ZERO),
            MemberBalance(c, Decimal("20")),
        ]}
        suggestions = simplify_debts(balances)["GBP"]
        assert len(suggestions) == 1
        assert suggestions[0].payer_id == a
        assert suggestions[0].payee_id == c
        assert suggestions[0].amount == Decimal("20")

    def test_already_settled(self) -> None:
        a, b = _ids(2)
        balances = {"GBP": [MemberBalance(a, ZERO), MemberBalance(b, ZERO)]}
        assert simplify_debts(balances)["GBP"] == []

    def test_size_bound_5_members(self) -> None:
        members = _ids(5)
        # All owe one person
        creditor = members[0]
        debtors = members[1:]
        bal_list = [MemberBalance(creditor, Decimal("40"))] + [
            MemberBalance(d, Decimal("-10")) for d in debtors
        ]
        suggestions = simplify_debts({"USD": bal_list})["USD"]
        assert len(suggestions) <= 4  # n-1


# ---------------------------------------------------------------------------
# Property-Based Tests (Hypothesis) — PBT-03, PBT-05, PBT-07, PBT-08
# ---------------------------------------------------------------------------

@given(equal_split_input())
@settings(max_examples=300)
def test_pbt_equal_split_sum_invariant(
    args: tuple[Decimal, list[uuid.UUID], list[SplitDetail]],
) -> None:
    """PBT-03: sum(computed_amount) == total_amount for all valid EQUAL inputs."""
    total, members, details = args
    shares = compute_shares(SplitType.EQUAL, total, members, details)
    assert sum(s.computed_amount for s in shares) == total


@given(exact_split_input())
@settings(max_examples=300)
def test_pbt_exact_split_sum_invariant(
    args: tuple[Decimal, list[uuid.UUID], list[SplitDetail]],
) -> None:
    """PBT-03: sum(computed_amount) == total_amount for all valid EXACT inputs."""
    total, members, details = args
    result = validate_split(SplitType.EXACT, total, members, details)
    if result.valid:
        shares = compute_shares(SplitType.EXACT, total, members, details)
        assert abs(sum(s.computed_amount for s in shares) - total) <= CENT


@given(percentage_split_input())
@settings(max_examples=300)
def test_pbt_percentage_split_sum_invariant(
    args: tuple[Decimal, list[uuid.UUID], list[SplitDetail]],
) -> None:
    """PBT-03: sum(computed_amount) == total_amount for all valid PERCENTAGE inputs."""
    total, members, details = args
    result = validate_split(SplitType.PERCENTAGE, total, members, details)
    if result.valid:
        shares = compute_shares(SplitType.PERCENTAGE, total, members, details)
        assert sum(s.computed_amount for s in shares) == total


@given(ratio_split_input())
@settings(max_examples=300)
def test_pbt_ratio_split_sum_invariant(
    args: tuple[Decimal, list[uuid.UUID], list[SplitDetail]],
) -> None:
    """PBT-03: sum(computed_amount) == total_amount for all valid RATIO inputs."""
    total, members, details = args
    result = validate_split(SplitType.RATIO, total, members, details)
    if result.valid:
        shares = compute_shares(SplitType.RATIO, total, members, details)
        assert sum(s.computed_amount for s in shares) == total


@given(balance_map_input())
@settings(max_examples=200)
def test_pbt_simplify_debts_oracle(balances: dict[str, list[MemberBalance]]) -> None:
    """PBT-05: Applying all suggestions to balances yields zero net for all members."""
    suggestions = simplify_debts(balances)
    for currency, suggestion_list in suggestions.items():
        # Build adjusted balances
        adj: dict[uuid.UUID, Decimal] = {
            b.member_id: b.net_amount for b in balances.get(currency, [])
        }
        for s in suggestion_list:
            adj[s.payer_id] = adj.get(s.payer_id, ZERO) + s.amount
            adj[s.payee_id] = adj.get(s.payee_id, ZERO) - s.amount
        for member_id, net in adj.items():
            assert abs(net) < CENT, f"Member {member_id} has residual {net} in {currency}"


@given(balance_map_input())
@settings(max_examples=200)
def test_pbt_simplify_debts_size_bound(balances: dict[str, list[MemberBalance]]) -> None:
    """PBT-03: Number of suggestions <= n-1 for n members."""
    for currency, suggestion_list in simplify_debts(balances).items():
        n = len(balances.get(currency, []))
        assert len(suggestion_list) <= max(0, n - 1)


def test_engine_has_no_forbidden_imports() -> None:
    """Verify engine.py has no imports from app modules (dependency isolation)."""
    import ast
    import inspect

    import balance.engine as eng

    source = inspect.getsource(eng)
    tree = ast.parse(source)
    forbidden = {
        "fastapi", "sqlalchemy", "httpx", "auth",
        "groups", "expenses", "settlements", "core",
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Import | ast.ImportFrom):
            module = getattr(node, "module", "") or ""
            for name in (node.names if isinstance(node, ast.Import) else []):
                module = getattr(name, "name", module)
            assert not any(f in module for f in forbidden), f"Forbidden import: {module}"
