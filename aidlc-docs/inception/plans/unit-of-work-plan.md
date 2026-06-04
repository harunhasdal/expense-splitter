# Unit of Work Plan — Expense Splitter

## Decomposition Assessment

All unit boundaries are **pre-determined** from the Application Design stage. No clarifying questions are needed — the decisions below are already locked in by prior artifacts.

| Category | Status | Decision Source |
|---|---|---|
| Story Grouping | Decided — stories organized by technical layer (US-1-*, US-2-*, US-3-*) | User Stories (Q3=C) |
| Dependencies | Decided — Unit 2 embedded in Unit 1; Unit 3 calls Unit 1 via REST | component-dependency.md |
| Team Alignment | N/A — single-team monorepo | application-design.md |
| Technical Considerations | Decided — Units 1+2 in same Docker image; Unit 3 is static SPA build | execution-plan.md |
| Business Domain | Decided — API/data layer, computation engine, presentation layer | requirements.md |
| Code Organization | Decided — full directory structure documented | component-dependency.md |

---

## Units of Work

### Unit 1 — Backend API & Data Layer
- **Scope**: FastAPI application, all domain routers/services/repositories, SQLAlchemy ORM models, Pydantic schemas, Alembic migrations, CoreInfrastructure (config, logging, middleware, error handler), OAuth2 auth flow
- **Key stories**: US-1-1 through US-1-8
- **Design stages**: Functional Design, NFR Requirements, NFR Design, Infrastructure Design, Code Generation
- **Construction order**: First — all other units depend on it

### Unit 2 — Balance Engine
- **Scope**: `backend/balance/engine.py` (pure Python module) — split calculators (4 types), balance aggregation, debt-simplification algorithm, rounding logic. Also `backend/balance/service.py` (data-loading orchestration) and `backend/balance/router.py` (balance/suggestions endpoints)
- **Key stories**: US-2-1 through US-2-7
- **Design stages**: Functional Design, NFR Requirements, NFR Design, Code Generation
- **Construction order**: Second — builds on Unit 1's DB models and repositories
- **Note**: Lives inside the `backend/` package but receives focused design treatment due to algorithmic complexity and PBT requirements (PBT-01, 02, 03, 05, 07, 08, 09)

### Unit 3 — Frontend SPA
- **Scope**: React/TypeScript Vite app — all 5 pages, 7 shared components, AuthContext, ApiClient with React Query hooks, React Router config
- **Key stories**: US-3-1 through US-3-6
- **Design stages**: Functional Design, Code Generation
- **Construction order**: Third — consumes Unit 1's REST API

---

## Generation Checklist

- [x] Step 1 — Generate `unit-of-work.md` — unit definitions, responsibilities, development order
- [x] Step 2 — Generate `unit-of-work-dependency.md` — dependency matrix between units
- [x] Step 3 — Generate `unit-of-work-story-map.md` — full story-to-unit mapping
