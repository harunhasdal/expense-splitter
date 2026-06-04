# Functional Design Plan — Unit 2: Balance Engine

## Context

All decisions are pre-determined from Application Design, NFR Requirements, and User Stories.
No open questions — generating artifacts directly.

| Decision | Source |
|---|---|
| 4 split types (EQUAL, EXACT, PERCENTAGE, RATIO) | FR-04, US-2-1 to US-2-4 |
| Remainder distribution for equal split | US-2-1 Scenario 2 |
| Debt simplification: minimum transfer algorithm | US-2-6 |
| Per-currency isolation (no cross-currency netting) | FR-08, US-2-5/2-6 |
| Conservation invariant: sum(net balances) = 0 | US-2-5 Scenario 4 |
| PBT properties: invariant, oracle, round-trip | NFR-07, PBT-01 |
| BalanceEngine has zero external dependencies | component-dependency.md |

## Stories
- US-2-1 Equal Split Calculation
- US-2-2 Exact Amount Split
- US-2-3 Percentage Split Calculation
- US-2-4 Custom Ratio Split
- US-2-5 Balance Aggregation
- US-2-6 Debt Simplification
- US-2-7 Expense Immutability (engine-side: pure validation only)

## Generation Checklist

- [x] Step 1 — Generate `domain-entities.md` — engine data types and value objects
- [x] Step 2 — Generate `business-rules.md` — validation rules per split type + algorithm invariants
- [x] Step 3 — Generate `business-logic-model.md` — detailed algorithm designs with PBT properties
