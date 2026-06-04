# Unit Test Execution

## Overview

Unit tests cover two layers:
1. **Example-based integration tests** (Unit 1): FastAPI TestClient against in-memory SQLite
2. **Property-based + example-based unit tests** (Unit 2): Pure engine logic via Hypothesis

All tests run with `pytest` from the `backend/` directory.

---

## Prerequisites

```bash
cd backend
uv sync --frozen
```

No running database or external services required — tests use in-memory SQLite via `conftest.py`.

---

## Run All Tests

```bash
cd backend
uv run pytest tests/ --cov=. --cov-report=term-missing --cov-fail-under=80
```

**Expected output**:
- All tests pass (0 failures, 0 errors)
- Coverage ≥ 80% (enforced by `--cov-fail-under=80`)
- Hypothesis PBT tests log the number of examples drawn (default 200–300 per property)

---

## Run by Category

### Integration Tests Only (Unit 1)

```bash
cd backend
uv run pytest tests/integration/ -v
```

Test files:
- `tests/integration/test_groups.py` — group CRUD, member management, archive, IDOR prevention
- `tests/integration/test_expenses.py` — expense creation, split validation, immutability (405), pagination
- `tests/integration/test_settlements.py` — settlement create, zero-amount guard, self-settlement guard, list

### Unit Tests Only (Unit 2 — Balance Engine)

```bash
cd backend
uv run pytest tests/unit/ -v
```

Test file:
- `tests/unit/test_engine.py` — 6 property-based tests + example-based tests:

| Test | Rule | Description |
|---|---|---|
| `test_equal_split_sum_invariant` | PBT-03 | Σ shares = total for any member count |
| `test_exact_split_sum_invariant` | PBT-03 | Σ exact amounts = total |
| `test_percentage_split_sum_invariant` | PBT-03 | Σ percentages = 100% |
| `test_ratio_split_sum_invariant` | PBT-03 | Shares proportional to ratios |
| `test_balance_conservation` | PBT-03 | Σ all balances = 0 (per currency) |
| `test_simplify_debts_oracle` | PBT-05 | Applying suggestions → zero balances |
| `test_simplify_debts_size_bound` | PBT-03 | Suggestions ≤ n-1 for n members |
| `test_engine_isolation` | — | `engine.py` imports no app modules |

---

## Run Specific Test File

```bash
cd backend
uv run pytest tests/integration/test_expenses.py -v
uv run pytest tests/unit/test_engine.py -v --hypothesis-show-statistics
```

---

## Static Analysis (Required Before PR)

### Linting (ruff)

```bash
cd backend
uv run ruff check .
```

**Expected output**: No violations. Selected rules: E, F, I (isort), UP, S (security), B (bugbear).

### Type Checking (mypy)

```bash
cd backend
uv run mypy . --strict
```

**Expected output**: `Success: no issues found in N source files`

### Dependency Vulnerability Scan (pip-audit)

```bash
cd backend
uv run pip-audit
```

**Expected output**: No known vulnerabilities found.

---

## Frontend Static Analysis

The frontend has no test suite yet (no testing library configured in `package.json`), but must pass:

```bash
cd frontend
pnpm run lint        # ESLint with TypeScript rules
pnpm run type-check  # tsc --noEmit
```

**Expected output**: 0 warnings, 0 errors for both commands.

---

## Fix Failing Tests

1. Run `uv run pytest tests/ -v` to see full test names and failure details
2. For PBT failures, Hypothesis prints a minimal counterexample — fix the engine logic to satisfy the property
3. For integration failures, check the TestClient response body for error details
4. After fixing, rerun the specific failing file first, then the full suite

---

## Test Coverage Report

```bash
cd backend
uv run pytest tests/ --cov=. --cov-report=html
open htmlcov/index.html
```

The HTML report shows per-file and per-line coverage. Target: ≥80% across all modules.
