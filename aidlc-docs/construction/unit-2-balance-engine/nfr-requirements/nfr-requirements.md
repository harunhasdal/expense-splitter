# NFR Requirements — Unit 2: Balance Engine

---

## Performance

| Requirement | Target | Notes |
|---|---|---|
| Debt simplification algorithm | O(n log n) — greedy with sorted lists | For n members; n ≤ 50 is the practical maximum per group |
| Balance aggregation | O(e + s) — linear in expenses + settlements | Single pass over both lists |
| Split computation | O(m) — linear in member count | All 4 types are single-pass |
| Latency contribution | < 5 ms for groups up to 50 members | Engine is in-process; no I/O |

## Reliability

| Requirement | Approach |
|---|---|
| Exact arithmetic | All monetary values use `Decimal` throughout — no `float` |
| Rounding determinism | `ROUND_HALF_UP` for percentage/ratio; stable UUID sort for EQUAL remainder distribution |
| Ghost-debt prevention | Members with `abs(net) < Decimal("0.01")` treated as balanced |

## Testability (NFR-07 — PBT Partial Enforcement)

PBT rules enforced: **PBT-02, PBT-03, PBT-07, PBT-08, PBT-09**

| PBT Rule | Applies To | Description |
|---|---|---|
| PBT-02 | Split schema ↔ engine dataclass serialisation | Round-trip: schema → engine input → output → schema |
| PBT-03 | All 4 `compute_shares` variants | Invariant: `sum(computed_amount) == total_amount` for all valid inputs |
| PBT-03 | `aggregate_balances` | Invariant: `sum(net_amount) == 0` per currency |
| PBT-03 | `simplify_debts` | Invariant: result length ≤ n-1 |
| PBT-05 | `simplify_debts` | Oracle: applying suggestions to balances → all zeros |
| PBT-07 | All PBT tests | Domain generators: `ExpenseRecord`, `SettlementRecord`, `SplitDetail` respect business constraints |
| PBT-08 | All PBT tests | Hypothesis `@settings(deriving=True)` shrinking enabled; seed logged on failure |
| PBT-09 | Framework | Hypothesis selected, documented, added as dependency |

**Not enforced under Partial mode**: PBT-01 (property identification in design — covered in functional-design/business-logic-model.md instead), PBT-04 (idempotency — advisory), PBT-06 (stateful — N/A, engine is stateless), PBT-10 (complementary strategy — advisory).

## Maintainability

| Requirement | Approach |
|---|---|
| Zero external dependencies | `engine.py` imports only stdlib + `Decimal` — no FastAPI, SQLAlchemy, or app modules |
| Type safety | All public functions fully annotated; `mypy --strict` passes |
| Isolation | Engine importable standalone: `from balance.engine import compute_shares` works without a running app |
