# Component Dependencies — Expense Splitter

---

## Dependency Matrix

| Consumer → | CoreInfra | BalanceEngine | GroupRepo | ExpenseRepo | SettlementRepo | UserRepo | AuthMiddleware |
|---|---|---|---|---|---|---|---|
| GroupService | config, db, log | BalanceService | read/write | — | — | read | via router |
| ExpenseService | db, log | validate_split, compute_shares | is_member, is_owner | read/write | — | — | via router |
| SettlementService | db, log | — | is_member | — | read/write | — | via router |
| BalanceService | db, log | aggregate_balances, simplify_debts | — | get_all_for_balance | get_all_for_balance | — | via router |
| AuthService | config, log | — | — | — | — | upsert/read | self |
| All routers | error handler | — | — | — | — | — | get_current_user |

**Key**: BalanceEngine has **no dependencies** — it is a pure computation module with zero imports from other app components (no DB, no config, no HTTP).

---

## Data Flow Diagrams

### Flow 1: Log an Expense

```
HTTP POST /groups/{id}/expenses
    |
    v
[ExpenseRouter]
    | Depends(get_current_user) → [AuthMiddleware] → [UserRepository]
    |
    v
[ExpenseService.create_expense()]
    |-- [GroupRepository.is_member()]     verify authorization
    |-- [BalanceEngine.validate_split()]  pure validation (no I/O)
    |-- [BalanceEngine.compute_shares()]  pure computation (no I/O)
    |-- [ExpenseRepository.create()]      atomic DB write
    |
    v
201 Created → Expense JSON
```

### Flow 2: Get Balance & Settlement Suggestions

```
HTTP GET /groups/{id}/balances
    |
    v
[GroupRouter / BalanceRouter]
    | Depends(get_current_user)
    |
    v
[BalanceService.get_balances()]
    |-- [GroupRepository.is_member()]           authorization
    |-- [ExpenseRepository.get_all_for_balance()] load data
    |-- [SettlementRepository.get_all_for_balance()] load data
    |-- [BalanceEngine.aggregate_balances()]     pure computation
    |
    v
200 OK → {GBP: [MemberBalance...], JPY: [...]}

HTTP GET /groups/{id}/settlements/suggestions
    |
    v
[BalanceService.get_settlement_suggestions()]
    | (same data loading as above)
    |-- [BalanceEngine.aggregate_balances()]
    |-- [BalanceEngine.simplify_debts()]         pure computation
    |
    v
200 OK → {GBP: [SettlementSuggestion...]}
```

### Flow 3: OAuth2 Sign-In

```
GET /auth/google/login
    |
    v
[AuthRouter] → [AuthService.get_authorization_url()]
    |
    v
302 Redirect → Google OAuth2

GET /auth/google/callback?code=...&state=...
    |
    v
[AuthRouter] → [AuthService.handle_callback()]
    |-- validate state (SECURITY-08)
    |-- httpx → Google token endpoint (exchange code)
    |-- httpx → Google userinfo endpoint
    |-- [UserRepository.upsert_oauth_user()]
    |-- sign JWT (SECURITY-12)
    |
    v
302 Redirect → /dashboard  (JWT in HttpOnly cookie)
```

### Flow 4: Frontend Data Fetch (React Query)

```
DashboardPage renders
    |
    v
useGroups() → React Query cache miss
    |-- ApiClient.get("/groups")
    |-- Attach Bearer JWT (AuthContext)
    |-- HTTP GET /groups
    |
    v
[GroupRouter] → [GroupService.list_groups()]
    |-- [GroupRepository.list_for_user()]
    |
    v
JSON response → React Query cache updated → DashboardPage re-renders
```

---

## Dependency Rules

1. **BalanceEngine has no upward dependencies** — it must never import from routers, services, or repositories. This keeps it purely testable.
2. **Repositories have no service dependencies** — they only import from `core/db.py` and SQLAlchemy.
3. **Services do not import other services directly** — cross-service calls go through the repository layer (e.g., BalanceService loads data via repositories, not by calling ExpenseService).
4. **Routers only import their own service** — no cross-domain router imports.
5. **Frontend ApiClient is the sole HTTP boundary** — no page/component makes `fetch()` calls directly.

---

## Monorepo Directory Structure

```
expense-splitter/                   # repo root
├── backend/
│   ├── auth/
│   │   ├── router.py
│   │   ├── service.py
│   │   ├── repository.py
│   │   ├── models.py               # SQLAlchemy ORM models
│   │   ├── schemas.py              # Pydantic request/response schemas
│   │   └── middleware.py           # get_current_user dependency
│   ├── groups/
│   │   ├── router.py
│   │   ├── service.py
│   │   ├── repository.py
│   │   ├── models.py
│   │   └── schemas.py
│   ├── expenses/
│   │   ├── router.py
│   │   ├── service.py
│   │   ├── repository.py
│   │   ├── models.py
│   │   └── schemas.py
│   ├── settlements/
│   │   ├── router.py
│   │   ├── service.py
│   │   ├── repository.py
│   │   ├── models.py
│   │   └── schemas.py
│   ├── balance/
│   │   ├── engine.py               # pure computation — no FastAPI deps
│   │   ├── service.py              # data loading + engine orchestration
│   │   ├── router.py
│   │   └── schemas.py
│   ├── core/
│   │   ├── config.py               # Pydantic Settings
│   │   ├── db.py                   # async SQLAlchemy session factory
│   │   ├── logging.py              # structured JSON logging
│   │   ├── middleware.py           # security headers, rate limiting, CORS
│   │   └── errors.py              # global exception handler
│   ├── migrations/                 # Alembic migration scripts
│   ├── tests/
│   │   ├── unit/                   # BalanceEngine pure function tests + PBT
│   │   └── integration/            # API endpoint tests against real test DB
│   ├── main.py                     # FastAPI app factory
│   ├── pyproject.toml
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── auth/
│   │   │   └── AuthContext.tsx
│   │   ├── api/
│   │   │   ├── client.ts           # axios/fetch base client
│   │   │   └── hooks/              # React Query hooks per resource
│   │   ├── pages/
│   │   │   ├── SignInPage.tsx
│   │   │   ├── DashboardPage.tsx
│   │   │   ├── GroupDetailPage.tsx
│   │   │   ├── ExpenseFormPage.tsx
│   │   │   └── ExpenseListPage.tsx
│   │   ├── components/
│   │   │   ├── GroupCard.tsx
│   │   │   ├── BalanceTable.tsx
│   │   │   ├── SettlementCard.tsx
│   │   │   ├── ExpenseRow.tsx
│   │   │   ├── SplitTypeSelector.tsx
│   │   │   ├── ConfirmationModal.tsx
│   │   │   └── ErrorBoundary.tsx
│   │   ├── router.tsx              # React Router routes
│   │   └── main.tsx                # app entry point
│   ├── package.json
│   └── vite.config.ts
├── docker-compose.yml              # local dev (backend + postgres + frontend)
└── .github/
    └── workflows/
        └── ci.yml
```
