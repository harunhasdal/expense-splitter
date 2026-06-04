# Application Design — Expense Splitter

## Summary

| Decision | Choice |
|---|---|
| Repo structure | Monorepo (`backend/` + `frontend/`) |
| Backend organization | Domain-based folders (`groups/`, `expenses/`, `settlements/`, `balance/`, `auth/`, `core/`) |
| Balance engine placement | Embedded pure Python module (`backend/balance/engine.py`) — no HTTP |
| Data access pattern | Repository pattern (one repo class per domain entity) |
| Frontend state | React Query (TanStack) for server state + React Context for auth/UI state |
| Backend framework | FastAPI + SQLAlchemy (async) + Alembic + Pydantic v2 |
| Frontend framework | React 18 + TypeScript + Vite |

---

## Components (10 total)

### Backend (6)

| Component | Path | Purpose |
|---|---|---|
| AuthComponent | `backend/auth/` | OAuth2 flow (Google/GitHub), JWT issue/validate, user identity |
| GroupComponent | `backend/groups/` | Group lifecycle, membership management |
| ExpenseComponent | `backend/expenses/` | Immutable expense recording with split validation |
| SettlementComponent | `backend/settlements/` | Immutable settlement event recording |
| BalanceEngine | `backend/balance/engine.py` | Pure computation: split arithmetic, balance aggregation, debt simplification |
| CoreInfrastructure | `backend/core/` | DB sessions, config, logging, security headers, error handling, rate limiting |

### Frontend (4)

| Component | Path | Purpose |
|---|---|---|
| AuthContext | `frontend/src/auth/` | JWT session state, unauthenticated redirect |
| ApiClient | `frontend/src/api/` | Typed HTTP client + React Query hooks for all resources |
| Pages | `frontend/src/pages/` | 5 route-level screen components |
| SharedComponents | `frontend/src/components/` | 7 reusable UI components |

---

## Service Layer (5 backend services)

| Service | Orchestrates |
|---|---|
| GroupService | GroupRepository + MemberRepository + BalanceService (for archive guard) |
| ExpenseService | GroupRepository (auth) + BalanceEngine (validate/compute) + ExpenseRepository |
| SettlementService | GroupRepository (auth) + SettlementRepository |
| BalanceService | ExpenseRepository + SettlementRepository + BalanceEngine |
| AuthService | UserRepository + httpx (OAuth2 provider calls) |

---

## Key Architectural Decisions

### BalanceEngine Isolation
The engine is a dependency-free pure Python module. It has no imports from FastAPI, SQLAlchemy, or any other app component. This enables:
- Direct unit testing without a running app or database
- Property-based testing with Hypothesis (PBT-02, PBT-03, PBT-05)
- Future extraction to a separate service if needed with zero logic changes

### Repository Pattern
Each domain entity has a dedicated async repository class. Services never write raw SQL. This provides:
- A clean seam for integration tests (real DB, no mocks)
- Consistent query patterns across the codebase
- Easy swap between SQLite (dev) and PostgreSQL (cloud) via `DATABASE_URL`

### Security Architecture (SECURITY-11: Separation of Concerns)
Security-critical logic is isolated:
- **Authentication**: `AuthComponent` only — no auth logic in other domains
- **Authorization**: `AuthMiddleware` dependency injected at router level; service methods receive `requesting_user_id` and call repository guards
- **Input validation**: Pydantic v2 schemas at router boundary; `BalanceEngine.validate_split()` for financial rules
- **Error handling**: Single `global_exception_handler` in `core/errors.py` — no scattered try/catch in routers

### Frontend Data Strategy
React Query manages all server state (caching, invalidation, loading/error states). After any mutation (create expense, record settlement), the relevant query cache keys are invalidated, triggering automatic re-fetches. No manual state synchronization.

---

## Dependency Rules (Enforced)

1. `BalanceEngine` → no imports from any other app module
2. Repositories → only `core/db.py` and SQLAlchemy
3. Services → only their own repository + BalanceEngine (no cross-service imports)
4. Routers → only their own service + `auth/middleware.py`
5. Frontend pages/components → only via `api/hooks/` (no direct `fetch()` calls)

---

## Requirement Coverage

| Requirement | Components |
|---|---|
| FR-01 Group Management | GroupComponent, GroupService, GroupRepository |
| FR-02 Member Management | GroupComponent (members), GroupService, MemberRepository |
| FR-03 Expense Recording | ExpenseComponent, ExpenseService, ExpenseRepository |
| FR-04 Split Types (4) | BalanceEngine.validate_split, BalanceEngine.compute_shares |
| FR-05 Balance Calculation | BalanceEngine.aggregate_balances, BalanceEngine.simplify_debts, BalanceService |
| FR-06 Settlement Flow | SettlementComponent, SettlementService, SettlementRepository |
| FR-07 Dashboard & UI | Pages, SharedComponents, ApiClient hooks |
| FR-08 Multi-Currency | BalanceEngine (currency-keyed output), all schemas (currency field) |
| FR-09 Audit Trail | ExpenseComponent (immutability), SettlementComponent (immutable events), CoreInfrastructure (structured logging) |
| NFR-02 Auth | AuthComponent, AuthMiddleware, AuthService |
| NFR-05 Security | CoreInfrastructure (headers, rate limiting, CORS, error handling), all AuthMiddleware guards |
| NFR-07 PBT | BalanceEngine (PBT-01, 02, 03, 05, 07, 08, 09) |

---

*See individual files for full detail:*
- *`components.md` — component responsibilities and interfaces*
- *`component-methods.md` — method signatures*
- *`services.md` — service operations and collaborators*
- *`component-dependency.md` — dependency matrix, data flow diagrams, directory structure*
