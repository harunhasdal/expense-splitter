# Tech Stack Decisions — Unit 2: Balance Engine

| Decision | Choice | Version | Rationale |
|---|---|---|---|
| Arithmetic | Python `decimal.Decimal` | stdlib | Exact base-10 arithmetic; no floating-point rounding errors on monetary values |
| Rounding mode | `ROUND_HALF_UP` | — | Standard financial rounding; deterministic |
| PBT Framework | Hypothesis | ≥6.103 | Mature Python PBT; excellent shrinking; Django/pytest integration; supports composite strategies (PBT-09) |
| Test runner integration | `pytest-hypothesis` (bundled with Hypothesis) | — | Native pytest integration; `@given` decorator |
| Hypothesis settings | `@settings(max_examples=200, deriving=True)` | — | 200 examples balances coverage vs CI speed; shrinking always enabled (PBT-08) |
| Type checking | mypy strict | ≥1.10 | Already in pyproject.toml; engine must pass independently |

## Added to `backend/pyproject.toml`

```toml
dependencies = [
    ...
    "hypothesis==6.103.0",   # PBT-09
]
```

## No Infrastructure

Unit 2 has no infrastructure of its own — it is an in-process Python module co-deployed in the Unit 1 Docker image. Infrastructure Design stage is skipped for this unit (as decided in execution-plan.md).
