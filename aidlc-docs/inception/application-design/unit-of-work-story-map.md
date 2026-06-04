# Unit of Work Story Map — Expense Splitter

## Story-to-Unit Assignment

| Story ID | Title | Unit | Rationale |
|---|---|---|---|
| US-1-1 | OAuth2 Sign-In via Google or GitHub | U1 | Auth flow, JWT, callback endpoint |
| US-1-2 | Create a Group | U1 | REST endpoint + DB persistence |
| US-1-3 | Add Members to a Group | U1 | REST endpoint + DB persistence |
| US-1-4 | Remove a Member from a Group | U1 | REST endpoint + authorization guard |
| US-1-5 | Archive a Group | U1 | REST endpoint + soft-archive logic |
| US-1-6 | Log an Expense | U1 | REST endpoint + split validation delegation to U2 |
| US-1-7 | Record a Settlement | U1 | REST endpoint + DB persistence |
| US-1-8 | View Group Expenses | U1 | REST endpoint + paginated query |
| US-2-1 | Equal Split Calculation | U2 | Pure computation — `compute_shares(EQUAL)` |
| US-2-2 | Exact Amount Split | U2 | Pure computation — `compute_shares(EXACT)` |
| US-2-3 | Percentage Split Calculation | U2 | Pure computation — `compute_shares(PERCENTAGE)` |
| US-2-4 | Custom Ratio Split | U2 | Pure computation — `compute_shares(RATIO)` |
| US-2-5 | Balance Aggregation | U2 | Pure computation — `aggregate_balances()` |
| US-2-6 | Debt Simplification | U2 | Pure computation — `simplify_debts()` |
| US-2-7 | Expense Immutability Enforcement | U1+U2 | HTTP enforcement in U1 (405); audit log in U1 core; U2 stateless so N/A for engine |
| US-3-1 | Sign-In Screen | U3 | SPA page — OAuth2 redirect UI |
| US-3-2 | Group Dashboard | U3 | SPA page — group list + balance summary cards |
| US-3-3 | Group Detail / Balance View | U3 | SPA page — balance table + settlement suggestions |
| US-3-4 | Expense Entry Form | U3 | SPA page — split type selector + inline validation |
| US-3-5 | Settlement Completion Flow | U3 | SPA overlay — one-click settle + confirmation modal |
| US-3-6 | Expense List and Search | U3 | SPA page — paginated list + search/filter |

---

## Unit Coverage Summary

| Unit | Stories | Count |
|---|---|---|
| U1 — Backend API & Data Layer | US-1-1, 1-2, 1-3, 1-4, 1-5, 1-6, 1-7, 1-8, 2-7 (partial) | 9 |
| U2 — Balance Engine | US-2-1, 2-2, 2-3, 2-4, 2-5, 2-6, 2-7 (partial) | 7 |
| U3 — Frontend SPA | US-3-1, 3-2, 3-3, 3-4, 3-5, 3-6 | 6 |

All 22 story assignments accounted for (US-2-7 spans U1 + U2 for different aspects).

---

## Requirement-to-Unit Traceability

| Requirement | Unit(s) |
|---|---|
| FR-01 Group Management | U1 |
| FR-02 Member Management | U1 |
| FR-03 Expense Recording | U1 (endpoint/persistence), U2 (split validation/computation) |
| FR-04 Split Types (4) | U2 |
| FR-05 Balance Calculation Engine | U2 |
| FR-06 Settlement Flow | U1 (endpoint/persistence), U3 (UI) |
| FR-07 Dashboard & UI | U3 |
| FR-08 Multi-Currency Display | U2 (per-currency computation), U3 (per-currency rendering) |
| FR-09 Audit Trail | U1 (immutability enforcement, structured logging) |
| NFR-01 Tech Stack | U1 (FastAPI, SQLAlchemy, Alembic), U2 (Hypothesis), U3 (React/TS, Vite) |
| NFR-02 Auth | U1 |
| NFR-05 Security Baseline | U1 (all 15 rules), U3 (SECURITY-04, 13) |
| NFR-07 PBT (Partial) | U2 (PBT-02, 03, 07, 08, 09) |
| NFR-09 Deployment | U1 (Docker, Alembic, IaC), U3 (S3/CloudFront via U1 infra design) |
