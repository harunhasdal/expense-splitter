# NFR Design Patterns — Unit 2: Balance Engine

---

## Pattern 1: Decimal-Only Arithmetic

**Addresses**: Exact arithmetic NFR, BR-ENG-COMP rounding rules

All monetary inputs converted to `Decimal` at the module boundary. The engine never accepts or returns `float`.

```python
# Correct — engine boundary
def compute_shares(
    split_type: SplitType,
    total_amount: Decimal,       # caller converts float to Decimal before calling
    member_ids: list[UUID],
    split_details: list[SplitDetail],
) -> list[MemberShare]: ...

# Callers in service layer convert at the boundary:
total = Decimal(str(expense.amount))  # str conversion avoids float imprecision
```

Rounding constants defined once:
```python
CENT = Decimal("0.01")
ZERO = Decimal("0")
ROUNDING = ROUND_HALF_UP
```

---

## Pattern 2: Last-Member Adjustment for Exact Sums

**Addresses**: BR-ENG-COMP-03, BR-ENG-COMP-04, PBT-03 invariant

For PERCENTAGE and RATIO splits, rounding individual shares can produce sums that are off by 1 cent. The adjustment pattern guarantees exact totals:

```python
shares = []
running_total = ZERO
for i, detail in enumerate(non_zero_details):
    if i == len(non_zero_details) - 1:
        # Last member gets the remainder — exact
        amount = total_amount - running_total
    else:
        amount = (detail.value / total_ratio * total_amount).quantize(CENT, ROUNDING)
        running_total += amount
    shares.append(MemberShare(detail.member_id, detail.value, amount))
```

This pattern is tested by a PBT invariant that verifies `sum == total_amount` for 10,000+ generated inputs.

---

## Pattern 3: Stable Sort for EQUAL Remainder Distribution

**Addresses**: BR-ENG-COMP-01, PBT-03 determinism

Remainder cents must be distributed deterministically (same input → same output, regardless of call order):

```python
sorted_members = sorted(member_ids, key=lambda uid: str(uid))
cents_to_distribute = int((total_amount - base * len(sorted_members)) * 100)
for i, member_id in enumerate(sorted_members):
    extra = CENT if i < cents_to_distribute else ZERO
    yield MemberShare(member_id, None, base + extra)
```

UUID string sort is stable across Python versions and platforms.

---

## Pattern 4: Greedy Creditor-Debtor Matching

**Addresses**: BR-ENG-DEBT-01, PBT-05 oracle

The debt simplification uses a greedy sorted-list approach (equivalent to a max-heap for small n ≤ 50):

```python
def simplify_debts(balances: BalanceMap) -> SuggestionMap:
    result: SuggestionMap = {}
    for currency, member_balances in balances.items():
        # Filter ghost debts
        active = [b for b in member_balances if abs(b.net_amount) >= CENT]
        creditors = sorted([b for b in active if b.net_amount > 0],
                           key=lambda b: b.net_amount, reverse=True)
        debtors   = sorted([b for b in active if b.net_amount < 0],
                           key=lambda b: b.net_amount)  # most negative first
        suggestions = []
        while creditors and debtors:
            credit = creditors[0].net_amount
            debt   = abs(debtors[0].net_amount)
            payment = min(credit, debt)
            suggestions.append(SettlementSuggestion(
                payer_id=debtors[0].member_id,
                payee_id=creditors[0].member_id,
                amount=payment, currency=currency
            ))
            # Update amounts, remove if settled
            creditors[0] = MemberBalance(creditors[0].member_id, credit - payment)
            debtors[0]   = MemberBalance(debtors[0].member_id, -(debt - payment))
            if creditors[0].net_amount < CENT: creditors.pop(0)
            if abs(debtors[0].net_amount) < CENT: debtors.pop(0)
            # Re-sort after update (small n — acceptable)
            creditors.sort(key=lambda b: b.net_amount, reverse=True)
            debtors.sort(key=lambda b: b.net_amount)
        result[currency] = suggestions
    return result
```

---

## Pattern 5: Hypothesis PBT Strategy Definitions

**Addresses**: PBT-07, PBT-08, PBT-09

Domain-specific generators defined in `tests/unit/strategies.py` (reusable across all PBT tests):

```python
from hypothesis import strategies as st
from hypothesis.strategies import composite
from decimal import Decimal
import uuid

@composite
def monetary_amounts(draw) -> Decimal:
    """Realistic expense amounts: 0.01 to 9999.99"""
    cents = draw(st.integers(min_value=1, max_value=999999))
    return Decimal(cents) / 100

@composite
def member_ids(draw, min_size=1, max_size=8) -> list[uuid.UUID]:
    count = draw(st.integers(min_value=min_size, max_value=max_size))
    return [uuid.uuid4() for _ in range(count)]

@composite
def equal_split_inputs(draw):
    total = draw(monetary_amounts())
    members = draw(member_ids())
    details = [SplitDetail(m, None) for m in members]
    return total, members, details

@composite
def percentage_split_inputs(draw):
    total = draw(monetary_amounts())
    members = draw(member_ids(min_size=1, max_size=6))
    n = len(members)
    # Generate n-1 percentages, last gets remainder
    parts = draw(st.lists(
        st.integers(min_value=0, max_value=100),
        min_size=n-1, max_size=n-1
    ))
    used = sum(parts)
    if used > 100:
        parts = [p * 100 // used for p in parts]
        used = sum(parts)
    last = 100 - used
    pcts = [Decimal(p) for p in parts] + [Decimal(last)]
    details = [SplitDetail(m, p) for m, p in zip(members, pcts)]
    return total, members, details
```

**Shrinking**: Hypothesis shrinks automatically — never disabled. All `@given` tests use `@settings(max_examples=200)`.

**Seed logging**: CI configured with `HYPOTHESIS_SEED` env var; failures print seed in output.
