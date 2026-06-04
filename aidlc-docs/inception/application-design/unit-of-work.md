# Units of Work — Expense Splitter

## Overview

The system decomposes into 3 units built sequentially. Units 1 and 2 live inside `backend/`; Unit 3 is `frontend/`. All three share the monorepo root.

| Unit | Name | Layer | Build Order | Design Stages |
|---|---|---|---|---|
| U1 | Backend API & Data Layer | API + Persistence | 1st | Functional Design, NFR Requirements, NFR Design, Infrastructure Design, Code Generation |
| U2 | Balance Engine | Computation | 2nd | Functional Design, NFR Requirements, NFR Design, Code Generation |
| U3 | Frontend SPA | Presentation | 3rd | Functional Design, Code Generation |

---

## Unit 1 — Backend API & Data Layer

**Description**: The FastAPI application shell and all domain modules that handle HTTP routing, business orchestration, persistence, and cross-cutting concerns. This is the deployable backend service.

**Scope**:
- `backend/auth/` — OAuth2 flow (Google, GitHub), JWT issue/validate, AuthMiddleware dependency
- `backend/groups/` — group CRUD, membership management (add/remove member)
- `backend/expenses/` — expense recording, soft-archive, paginated listing
- `backend/settlements/` — settlement recording and listing
- `backend/core/` — DB session factory, Pydantic Settings, structured logging, security headers middleware, rate limiting, CORS, global error handler
- `backend/migrations/` — Alembic migration scripts
- `backend/main.py` — FastAPI app factory, router registration, middleware registration
- `backend/Dockerfile` — multi-stage production build
- `backend/pyproject.toml` — dependencies (pinned via uv lock file)

**Responsibilities**:
- Expose all REST API endpoints (US-1-1 through US-1-8)
- Enforce authentication (AuthMiddleware) on every protected route
- Enforce object-level authorization in every service method
- Validate all input at the Pydantic schema boundary
- Persist all domain data to SQLite (dev) / PostgreSQL (cloud)
- Return generic error messages; log details server-side
- Apply all HTTP security headers, CORS policy, rate limiting

**Key NFRs**: SECURITY-01 through SECURITY-15 (full enforcement), Alembic schema migration, connection pooling, httpOnly JWT cookie

**Entry point for tests**: `backend/tests/integration/` — all API endpoint tests run against a real SQLite test database

**Code organization strategy** (Greenfield):
```
backend/
  {domain}/
    router.py      # FastAPI APIRouter — thin, no business logic
    service.py     # orchestration — calls repository + engine
    repository.py  # async SQLAlchemy queries only
    models.py      # SQLAlchemy ORM table definitions
    schemas.py     # Pydantic v2 request/response models
```

---

## Unit 2 — Balance Engine

**Description**: A pure Python computation module embedded within the backend package. Receives dedicated design treatment because of its algorithmic complexity, non-trivial rounding rules, multi-currency isolation, and PBT requirements.

**Scope**:
- `backend/balance/engine.py` — pure functions: `validate_split`, `compute_shares`, `aggregate_balances`, `simplify_debts`
- `backend/balance/service.py` — data-loading orchestration (loads from repositories, calls engine)
- `backend/balance/router.py` — balance and settlement-suggestion endpoints
- `backend/balance/schemas.py` — Pydantic schemas for balance/suggestion responses
- `backend/tests/unit/` — all BalanceEngine unit tests and PBT (Hypothesis)

**Responsibilities**:
- Implement and validate all 4 split types (equal, exact, percentage, ratio)
- Apply rounding rules so computed shares always sum exactly to the expense total
- Aggregate per-member net balances per currency across all expenses and settlements
- Implement the debt-simplification algorithm producing the minimum transfer graph
- Isolate all computation per currency (no cross-currency netting)
- Expose zero-dependency pure functions testable without a running app or database

**Key NFRs**: PBT-01, PBT-02, PBT-03, PBT-05, PBT-07, PBT-08, PBT-09 (Hypothesis, Partial enforcement), O(n log n) debt simplification

**Dependency constraint**: `engine.py` MUST NOT import from any other `backend/` module — enforced by tests

---

## Unit 3 — Frontend SPA

**Description**: The React/TypeScript single-page application that consumes the backend REST API. Served as a static build from S3/CloudFront in production.

**Scope**:
- `frontend/src/auth/AuthContext.tsx` — JWT session state, sign-in redirect
- `frontend/src/api/client.ts` — base HTTP client (fetch/axios, attaches bearer token)
- `frontend/src/api/hooks/` — 9 React Query hooks (one per resource operation)
- `frontend/src/pages/` — 5 screen components (SignInPage, DashboardPage, GroupDetailPage, ExpenseFormPage, ExpenseListPage)
- `frontend/src/components/` — 7 shared UI components
- `frontend/src/router.tsx` — React Router v6 route definitions
- `frontend/src/main.tsx` — app entry point, QueryClientProvider, AuthContext provider
- `frontend/package.json` — pinned dependencies
- `frontend/vite.config.ts` — build config, proxy for local dev

**Responsibilities**:
- Render all 6 screens covering US-3-1 through US-3-6
- Manage OAuth2 redirect flow and JWT storage in the browser
- Provide inline split validation before API submission (percentages must sum to 100%, etc.)
- Display multi-currency balances and settlement suggestions
- Handle optimistic UI updates for settlement marking
- Load CSP-compliant assets; use SRI hashes for any CDN-loaded scripts

**Key NFRs**: CSP headers (served by backend), SRI for CDN assets (SECURITY-13), bundle size target < 3 s load on 4 Mbps

**No independent infrastructure** — static assets served via S3/CloudFront defined in Unit 1's Infrastructure Design
