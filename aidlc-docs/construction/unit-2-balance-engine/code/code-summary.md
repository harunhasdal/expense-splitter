# Code Summary — Unit 2: Balance Engine

## Modified Files
- `backend/balance/service.py` — replaced stub; now calls engine.aggregate_balances() and simplify_debts()
- `backend/balance/router.py` — replaced 501 stubs; returns real CurrencyBalances and CurrencySettlements
- `backend/pyproject.toml` — added `hypothesis==6.103.0`

## Created Files
- `backend/balance/engine.py` — pure computation module (zero app imports):
  - `validate_split()` — validates all 4 split types
  - `compute_shares()` — computes per-member amounts with stable sort + last-member adjustment
  - `aggregate_balances()` — per-currency net balance aggregation (conservation invariant)
  - `simplify_debts()` — greedy creditor-debtor matching, O(n log n), ≤ n-1 transfers
- `backend/tests/unit/strategies.py` — Hypothesis domain generators (PBT-07):
  - `monetary_amounts`, `member_id_list`, `equal_split_input`, `exact_split_input`
  - `percentage_split_input`, `ratio_split_input`, `expense_input`, `balance_map_input`
- `backend/tests/unit/test_engine.py` — example-based + 6 PBT tests:
  - EQUAL/EXACT/PERCENTAGE/RATIO sum invariants (@given, 200-300 examples)
  - Conservation law for aggregate_balances
  - Oracle test for simplify_debts (applying suggestions → zero balances) (PBT-05)
  - Size bound test (≤ n-1 suggestions) (PBT-03)
  - Isolation test (verifies engine.py imports no app modules)

## Stories Implemented
- US-2-1 Equal Split Calculation
- US-2-2 Exact Amount Split
- US-2-3 Percentage Split Calculation
- US-2-4 Custom Ratio Split
- US-2-5 Balance Aggregation
- US-2-6 Debt Simplification (minimum transfers)
- US-2-7 Expense Immutability (validate_split — pure validation, no mutations)

## PBT Compliance
- PBT-02: SplitDetail ↔ engine tested via round-trip in exact_split_input strategy
- PBT-03: sum invariants for all 4 split types; conservation law; size bound — all @given
- PBT-05: oracle test proving suggestions clear all debts
- PBT-07: domain generators with monetary constraints, UUID generation, valid percentages
- PBT-08: @settings(max_examples=200-300); Hypothesis shrinking always enabled
- PBT-09: hypothesis==6.103.0 in pyproject.toml
