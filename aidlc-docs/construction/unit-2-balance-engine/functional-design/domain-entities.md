# Domain Entities — Unit 2: Balance Engine

The balance engine uses pure Python dataclasses and enums. No ORM, no I/O, no FastAPI imports.
All values are `Decimal` for exact arithmetic — no float.

---

## Enum: SplitType

```python
from enum import Enum

class SplitType(str, Enum):
    EQUAL      = "EQUAL"
    EXACT      = "EXACT"
    PERCENTAGE = "PERCENTAGE"
    RATIO      = "RATIO"
```

---

## Dataclass: SplitDetail

Input value for a single member's share specification.

```python
@dataclass
class SplitDetail:
    member_id: UUID
    value: Decimal | None   # None for EQUAL; amount/pct/ratio for others
```

---

## Dataclass: MemberShare

Output of `compute_shares()` — the resolved monetary share for one member.

```python
@dataclass
class MemberShare:
    member_id: UUID
    raw_value: Decimal | None    # the original input value (None for EQUAL)
    computed_amount: Decimal     # always a positive monetary amount
```

**Invariant**: `sum(share.computed_amount for share in result) == total_amount`

---

## Dataclass: ValidationResult

```python
@dataclass
class ValidationResult:
    valid: bool
    errors: list[str]
```

---

## Dataclass: ExpenseRecord

Lightweight projection of an expense used by the balance aggregator. Does not import ORM models.

```python
@dataclass
class ExpenseRecord:
    expense_id: UUID
    payer_member_id: UUID
    currency: str                           # ISO 4217
    splits: list[tuple[UUID, Decimal]]      # (member_id, computed_amount)
```

---

## Dataclass: SettlementRecord

```python
@dataclass
class SettlementRecord:
    settlement_id: UUID
    payer_member_id: UUID
    payee_member_id: UUID
    currency: str
    amount: Decimal
```

---

## Dataclass: MemberBalance

Net balance for a single member in a single currency. Positive = owed money. Negative = owes money.

```python
@dataclass
class MemberBalance:
    member_id: UUID
    net_amount: Decimal    # positive: owed to this member; negative: this member owes
```

---

## Dataclass: SettlementSuggestion

One suggested payment to settle debts.

```python
@dataclass
class SettlementSuggestion:
    payer_id: UUID     # who should pay
    payee_id: UUID     # who should receive
    amount: Decimal    # always positive
    currency: str
```

---

## Type Aliases

```python
# Balances keyed by currency then member_id
BalanceMap = dict[str, list[MemberBalance]]

# Suggestions keyed by currency
SuggestionMap = dict[str, list[SettlementSuggestion]]
```
