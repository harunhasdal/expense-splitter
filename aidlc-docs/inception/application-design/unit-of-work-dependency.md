# Unit of Work Dependencies — Expense Splitter

## Dependency Matrix

| Unit | Depends On | Communication | Dependency Type |
|---|---|---|---|
| U1 — Backend API & Data Layer | External: PostgreSQL/SQLite, OAuth2 providers (Google, GitHub) | SQLAlchemy async driver; httpx OAuth2 calls | Runtime (external services) |
| U2 — Balance Engine | U1 (repositories for data loading; ORM models for type definitions) | Python import | Build-time + runtime (same process) |
| U3 — Frontend SPA | U1 REST API | HTTP/JSON over TLS | Runtime (network) |

**Key rule**: U2 (`engine.py`) has a **one-way dependency** — it provides pure functions that U1's `BalanceService` imports. U1 never imports from U2's router or service; U3 never directly invokes the balance engine.

---

## Dependency Diagram

```
+------------------+        Python import        +------------------+
|                  | <--------------------------- |                  |
|  U1              |   (balance/service.py        |  U2              |
|  Backend API     |    imports engine.py)        |  Balance Engine  |
|  & Data Layer    |                              |                  |
|                  |                              |                  |
|  - REST API      |                              |  - engine.py     |
|  - ORM/DB        |                              |    (pure fns)    |
|  - Auth          |                              |  - service.py    |
|  - Core Infra    |                              |  - router.py     |
+------------------+                              +------------------+
        ^
        | HTTP/JSON (REST API calls)
        |
+------------------+
|  U3              |
|  Frontend SPA    |
|  - React/TS      |
|  - React Query   |
|  - 5 Pages       |
+------------------+
```

---

## Build & Development Order

### Strict Sequential Order

```
U1 (Backend API & Data Layer)
  |
  | Provides: DB schema, ORM models, repository interfaces,
  |           REST API contract, auth middleware
  v
U2 (Balance Engine)
  |
  | Provides: validate_split, compute_shares,
  |           aggregate_balances, simplify_debts
  |           Integrated into U1's balance/service.py
  v
U3 (Frontend SPA)
      Consumes: REST API endpoints from U1+U2
```

**Why sequential:**
- U2 depends on U1's ORM models (`Expense`, `Settlement`, `Member`) for its data-loading service layer — U1 must be designed first
- U3 depends on the full REST API contract (all endpoints + response schemas) — both U1 and U2 must be complete

---

## Integration Points

| Integration | Between | Interface | Risk |
|---|---|---|---|
| Balance engine ↔ API | U1 ↔ U2 | Python function calls (no serialization) | Low — same process, typed |
| Frontend ↔ API | U3 ↔ U1 | REST/JSON over HTTP | Medium — schema changes break frontend |
| API ↔ Database | U1 ↔ PostgreSQL/SQLite | SQLAlchemy async | Low — migrations managed by Alembic |
| API ↔ OAuth2 | U1 ↔ Google/GitHub | HTTPS / OAuth2 code flow | Low — well-defined external protocol |

---

## Shared Artifacts (produced in U1, consumed by U2 and U3)

| Artifact | Produced By | Consumed By |
|---|---|---|
| SQLAlchemy ORM models (`Expense`, `Settlement`, `Member`, `Group`) | U1 Functional Design | U2 (data loading in balance/service.py) |
| REST API OpenAPI schema | U1 Code Generation | U3 (typed API client generation) |
| Pydantic response schemas | U1 (schemas.py) | U3 (TypeScript types via openapi-typescript) |
| Alembic migrations | U1 Code Generation | U2 integration tests (same test DB) |
| Docker image | U1 Dockerfile | U2 (same image — co-deployed) |
