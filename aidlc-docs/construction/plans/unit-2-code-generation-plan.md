# Code Generation Plan — Unit 2: Balance Engine

## Unit Context

- **Code location**: `backend/balance/` (replaces stubs from Unit 1)
- **Stories**: US-2-1 through US-2-7
- **Dependencies**: Unit 1 ORM models, repositories (for service.py data loading)
- **Key constraint**: `engine.py` must have zero imports from other backend modules

## Story Traceability

- [x] US-2-1 Equal Split Calculation
- [x] US-2-2 Exact Amount Split
- [x] US-2-3 Percentage Split Calculation
- [x] US-2-4 Custom Ratio Split
- [x] US-2-5 Balance Aggregation
- [x] US-2-6 Debt Simplification
- [x] US-2-7 Expense Immutability (engine validates splits — no mutation)

---

## Generation Steps

### Step 1: Balance Engine Core
- [x] Create `backend/balance/engine.py` — all 4 pure functions with Decimal arithmetic, stable sort, last-member adjustment, greedy debt simplification

### Step 2: Balance Service (wire engine to data)
- [x] Replace `backend/balance/service.py` stub — implement `get_raw_balances()`, `get_balances()`, `get_settlement_suggestions()` calling engine functions

### Step 3: Balance Router (replace 501 stubs)
- [x] Replace `backend/balance/router.py` stubs — return real balances and suggestions

### Step 4: Hypothesis Strategies
- [ ] Create `backend/tests/unit/strategies.py` — domain generators: `monetary_amounts`, `member_ids`, `equal_split_inputs`, `percentage_split_inputs`, `ratio_split_inputs`, `expense_records`, `settlement_records`, `balance_maps`

### Step 5: Unit Tests (example-based + PBT)
- [ ] Create `backend/tests/unit/test_engine.py` — example-based pinning tests + 5 Hypothesis PBT tests (sum invariants, conservation, oracle, size bound)

### Step 6: Update pyproject.toml
- [ ] Add `hypothesis==6.103.0` to `backend/pyproject.toml` dependencies

### Step 7: Code Documentation Summary
- [ ] Create `aidlc-docs/construction/unit-2-balance-engine/code/code-summary.md`

---

## PBT Compliance Checklist

- [ ] PBT-02: Round-trip test for SplitDetail serialisation
- [ ] PBT-03: sum(computed_amount) == total_amount for all 4 split types
- [ ] PBT-03: sum(net_amount) == 0 per currency for aggregate_balances
- [ ] PBT-05: Oracle — applying suggestions zeroes all balances
- [ ] PBT-07: Domain generators use monetary_amounts, constrained UUIDs, valid percentages
- [ ] PBT-08: @settings with shrinking enabled; seed documented in CI
- [ ] PBT-09: hypothesis in pyproject.toml
