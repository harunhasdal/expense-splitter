# Application Design Plan — Expense Splitter

Please answer each question by filling in the letter choice after the `[Answer]:` tag.

---

## Question 1
How should the backend be structured — what top-level code organization pattern?

A) Layered by technical concern: `routers/`, `services/`, `repositories/`, `models/`, `schemas/`
B) Layered by feature/domain: `groups/`, `expenses/`, `settlements/`, `auth/` — each containing its own router, service, and model
C) Hybrid: domain folders at the top level, each containing the technical layers (router, service, repository, schema) inside
X) Other (please describe after [Answer]: tag below)

[Answer]: B

---

## Question 2
Should the balance engine (split calculators + debt simplification) be a standalone Python module/package within the backend repo, or a fully separate service?

A) Standalone module inside the backend repo (imported directly by the API service layer)
B) Separate deployable service (the API calls it over HTTP/gRPC internally)
X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Question 3
What pattern should the data access layer use?

A) Repository pattern — each domain entity has a dedicated repository class abstracting all DB queries (clean boundary, easier to test)
B) Direct SQLAlchemy sessions in the service layer — simpler, less abstraction
C) SQLAlchemy with an Active Record-style approach using model methods for queries
X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Question 4
How should the frontend state be managed in the React SPA?

A) React Query (TanStack Query) for server state + React Context for local/UI state
B) Redux Toolkit for global state + RTK Query for API data fetching
C) Zustand for global state + React Query for server state
D) Built-in React hooks only (useState/useReducer/useContext) — no external state library
X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Question 5
Should the frontend and backend live in the same repository (monorepo) or separate repositories?

A) Monorepo — single repo with `backend/` and `frontend/` directories
B) Separate repos — one for the API, one for the SPA
X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Generation Checklist

Steps to execute after answers are received and this plan is approved.

- [x] Step 1 — Generate `components.md` — all components with responsibilities and interfaces
- [x] Step 2 — Generate `component-methods.md` — method signatures per component
- [x] Step 3 — Generate `services.md` — service layer definitions and orchestration
- [x] Step 4 — Generate `component-dependency.md` — dependency matrix and data-flow diagram
- [x] Step 5 — Generate `application-design.md` — consolidated design document
- [x] Step 6 — Validate completeness: all FR-01 to FR-09 addressed, Security Baseline components present
