# Logical Components — Unit 2: Balance Engine

---

## Component Map

```
backend/balance/
  engine.py          Pure computation module — ZERO external deps
    validate_split()
    compute_shares()
    aggregate_balances()
    simplify_debts()
  
  service.py         Data-loading orchestration
    get_raw_balances()         loads ExpenseRecords + SettlementRecords
    get_balances()             calls engine.aggregate_balances()
    get_settlement_suggestions() calls engine.aggregate_balances() + engine.simplify_debts()
  
  router.py          HTTP endpoints (wired to service)
    GET /groups/{id}/balances
    GET /groups/{id}/settlements/suggestions
  
  schemas.py         Pydantic response schemas (unchanged from Unit 1 stub)

backend/tests/unit/
  strategies.py      Hypothesis composite strategies (domain generators — PBT-07)
  test_engine.py     PBT + example-based tests for engine.py
```

---

## Dependency Flow

```
HTTP Request
  |
  v
balance/router.py
  | Depends(get_current_user)    [auth — Unit 1]
  | Depends(get_db)              [DB — Unit 1 core]
  |
  v
balance/service.py
  |-- expense_repo.get_all_for_balance()    [Unit 1 repository]
  |-- settlement_repo.get_all_for_balance() [Unit 1 repository]
  |-- balance/engine.aggregate_balances()   [pure — no deps]
  |-- balance/engine.simplify_debts()       [pure — no deps]
  |
  v
JSON response (CurrencyBalances / CurrencySettlements)
```

**Critical constraint**: `balance/engine.py` has NO imports from `fastapi`, `sqlalchemy`, `httpx`, or any other `backend/` module. This is verified by a test:

```python
def test_engine_has_no_app_imports():
    import balance.engine as eng
    import inspect, ast
    source = inspect.getsource(eng)
    tree = ast.parse(source)
    forbidden = {"fastapi", "sqlalchemy", "httpx", "auth", "groups", "expenses", "settlements", "core"}
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            name = getattr(node, "module", "") or ""
            assert not any(f in name for f in forbidden), f"Forbidden import: {name}"
```

---

## Test Architecture

```
backend/tests/unit/test_engine.py

Example-based tests (pinning known behavior):
  test_equal_split_even_division()
  test_equal_split_remainder_distribution()
  test_percentage_split_exact_sum()
  test_ratio_split_1_2_3()
  test_aggregate_balances_conservation()
  test_simplify_debts_3_person_chain()
  test_simplify_debts_already_settled()

PBT tests (Hypothesis):
  @given(equal_split_inputs())
  test_equal_split_sum_invariant(total, members, details)
    assert sum(s.computed_amount for s in compute_shares(...)) == total

  @given(percentage_split_inputs())
  test_percentage_split_sum_invariant(total, members, details)
    assert sum(s.computed_amount for s in compute_shares(...)) == total

  @given(st.lists(expense_records(), min_size=0, max_size=20), ...)
  test_balance_conservation(expenses, settlements)
    balances = aggregate_balances(expenses, settlements)
    for currency, member_balances in balances.items():
        assert sum(b.net_amount for b in member_balances) == ZERO

  @given(balance_maps())
  test_simplify_debts_oracle(balances)
    suggestions = simplify_debts(balances)
    # Apply suggestions back to balances
    applied = apply_suggestions(balances, suggestions)
    for currency, member_balances in applied.items():
        assert all(abs(b.net_amount) < CENT for b in member_balances)

  @given(balance_maps())
  test_simplify_debts_size_bound(balances)
    for currency, suggestions in simplify_debts(balances).items():
        n = len(balances.get(currency, []))
        assert len(suggestions) <= max(0, n - 1)
```
