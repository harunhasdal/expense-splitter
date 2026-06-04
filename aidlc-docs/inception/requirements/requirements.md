# Requirements — Expense Splitter

## Intent Analysis

| Attribute | Value |
|---|---|
| User Request | Design and build the app described in prd.md |
| Request Type | New Project (Greenfield) |
| Scope Estimate | System-wide — three distinct layers (REST API, balance engine, SPA frontend) |
| Complexity Estimate | Complex — non-trivial balance/debt-simplification algorithm, OAuth2 integration, cloud deployment |

---

## Functional Requirements

### FR-01: Group Management
- Users can create expense groups (e.g., "Thailand Trip 2026", "Flat Share")
- A group has a name, optional description, and a list of members
- Users can add and remove members from a group
- A group owner can archive/soft-delete a group (audit trail preserved)

### FR-02: Member Management
- Members are named participants within a group
- Members are linked to authenticated user accounts (OAuth2 identity)
- A user may be a member of multiple groups simultaneously
- Invited members who have not yet signed up are represented by email placeholders

### FR-03: Expense Recording
- Any group member can log an expense for the group
- Each expense records: description, amount, currency, date, payer (who paid), and split details
- Once recorded, an expense is **immutable** — soft-delete only (full audit trail, FR-09)

### FR-04: Split Types
The following split types MUST be supported at launch:
- **Equal split**: Amount divided equally among selected members
- **Exact amounts**: Each member's share is specified as an absolute amount (must sum to total)
- **Percentage split**: Each member's share is a percentage (must sum to 100%)
- **Custom ratio/share**: Each member is assigned a unitless ratio (e.g., 1:2:3); app computes proportional amounts

### FR-05: Balance Calculation Engine
- The engine computes real-time net balances for each member across all expenses in a group
- Balances update immediately when a new expense is recorded or a settlement is logged
- The engine produces **simplified settlement suggestions** — the minimum number of transactions needed for everyone to reach a zero balance (debt simplification algorithm)

### FR-06: Settlement Flow
- Any member can mark a payment/settlement as complete (e.g., "Alice paid Bob £30")
- Settlements are recorded as immutable events (same audit trail as expenses)
- The dashboard reflects settled amounts and recalculates outstanding balances

### FR-07: Dashboard & UI
- A group dashboard shows: current balances per member, outstanding debts, and settlement suggestions
- An expense list view shows all expenses for a group with payer, split breakdown, and status
- Users can filter/search expenses by date, payer, or description
- One-click flow to mark a suggested settlement as complete

### FR-08: Multi-Currency Display
- Each expense stores its own currency (ISO 4217 code)
- Balances within a group are displayed per-currency — no automatic conversion
- The UI clearly distinguishes amounts in different currencies

### FR-09: Audit Trail & Data Integrity
- Expenses and settlements are immutable once created (no hard delete)
- Soft-delete (archived flag) is the only removal mechanism — archived records remain in the data store
- All state-changing operations are logged with actor identity and timestamp
- Critical data modifications record actor, timestamp, and the full before/after state

---

## Non-Functional Requirements

### NFR-01: Technology Stack
| Layer | Technology |
|---|---|
| Backend API | Python — FastAPI |
| Frontend SPA | React with TypeScript |
| Database (dev) | SQLite (file-based, zero-config local setup) |
| Database (cloud) | PostgreSQL |
| Auth Provider | OAuth2 — Google and GitHub (via OAuth2 provider library) |
| Deployment | AWS — containerized (Docker + ECS Fargate, or Lambda + API Gateway) |
| PBT Framework | Python — Hypothesis (Partial enforcement: PBT-02, PBT-03, PBT-07, PBT-08, PBT-09) |

### NFR-02: Authentication & Authorization
- OAuth2 social login (Google, GitHub) — no local password accounts
- JWT-based session tokens (signed, with expiry) issued after OAuth2 callback
- Every API endpoint requires authentication except public health-check and OAuth2 callback routes
- Object-level authorization: members can only read/write data in groups they belong to (IDOR prevention)
- Admin/privileged routes have explicit role checks server-side

### NFR-03: Performance
- API responses for balance calculations on groups up to 50 members: < 300 ms p95
- Debt simplification algorithm: O(n log n) target for n members
- Frontend initial load (SPA bundle): < 3 s on a 4 Mbps connection

### NFR-04: Scalability
- Stateless API tier — horizontally scalable behind a load balancer
- Database connection pooling configured for cloud deployment
- No server-side session state — all session state in JWT

### NFR-05: Security (Security Baseline — Full Enforcement)
Security rules SECURITY-01 through SECURITY-15 are fully enforced. Key constraints:
- Encryption at rest and in transit for all data stores (SECURITY-01)
- Structured logging with centralized log service; no PII in logs (SECURITY-03)
- HTTP security headers on all HTML-serving endpoints (SECURITY-04)
- Input validation (type, length, format, injection prevention) on all API endpoints (SECURITY-05)
- Least-privilege IAM policies; no wildcard actions or resources (SECURITY-06)
- Deny-by-default network configuration; no 0.0.0.0/0 except public LB on 443 (SECURITY-07)
- Object-level + function-level authorization; CORS restricted to explicit origins (SECURITY-08)
- No default credentials; generic error messages in production (SECURITY-09)
- Pinned dependencies with lock file; vulnerability scanning in CI/CD (SECURITY-10)
- Security logic isolated in dedicated modules; rate limiting on public endpoints (SECURITY-11)
- OAuth2 only (no local passwords); session expiry and invalidation on logout (SECURITY-12)
- SRI hashes for any CDN-loaded scripts; CI/CD pipeline access-controlled (SECURITY-13)
- Alerting on auth failures and access-denied events; 90-day log retention (SECURITY-14)
- Global error handler; fail-closed on errors; no unhandled exceptions in production (SECURITY-15)

### NFR-06: Reliability & Availability
- Target: 99.5% uptime for cloud deployment
- Graceful degradation: if balance engine fails, API returns an error rather than stale/incorrect data
- Database connection errors result in 503 responses with retry-after headers

### NFR-07: Testability
- Unit tests for all business logic (balance engine, split calculators, debt simplification)
- Integration tests for all API endpoints against a real test database (no mocks for the DB layer)
- Property-based tests (Hypothesis) under Partial enforcement:
  - PBT-02: Round-trip tests for serialization/deserialization
  - PBT-03: Invariant tests for balance/debt calculations
  - PBT-07: Domain-specific generators (Expense, Group, Member, SplitRule)
  - PBT-08: Shrinking enabled; seed logged on failure; PBT in CI
  - PBT-09: Hypothesis selected and documented

### NFR-08: Maintainability
- Python code follows PEP 8; FastAPI models use Pydantic v2
- TypeScript strict mode enabled; ESLint + Prettier configured
- All environment-specific config via environment variables (no hardcoded values)
- README documents all required environment variables

### NFR-09: Deployment & Infrastructure
- Docker multi-stage build for the API container
- Environment parity: same container image used in dev, staging, and production
- Database migrations managed by Alembic (SQLAlchemy migration tool)
- SQLite used in local development; PostgreSQL connection string provided via env var in cloud
- Infrastructure-as-Code for cloud resources (CDK or Terraform — to be decided in Infrastructure Design stage)

---

## User Scenarios

### Scenario 1: Create a group and log an expense
1. Alice signs in via Google OAuth2
2. Alice creates a group "Greece Trip" and invites Bob and Carol by email
3. Alice logs an expense: "Airbnb deposit" £600, split equally among 3 members
4. Dashboard shows: Alice is owed £400, Bob owes £200, Carol owes £200

### Scenario 2: Mixed-currency trip
1. Group "Japan 2026" has expenses in JPY and EUR
2. Dashboard shows separate balance columns per currency — no conversion
3. Settlement suggestions are also per-currency

### Scenario 3: Custom ratio split
1. Dave pays £120 for a hotel room; Alice takes the single room (ratio 1), Dave and Eve share a double (ratio 2 each)
2. Expense recorded with ratio split 1:2:2 → Alice owes £24, Dave owes £48, Eve owes £48

### Scenario 4: Debt simplification
1. A 5-person group has 8 expenses creating a web of debts
2. Balance engine simplifies to the minimum payment graph (at most n-1 transfers for n people)
3. Dashboard shows 4 settlement suggestions instead of 8 separate debts

### Scenario 5: Attempted unauthorized access
1. Frank (not a member of "Greece Trip") attempts to GET /groups/123/expenses
2. API returns 403 Forbidden; no expense data is exposed (IDOR prevention)

---

## Out of Scope (for this release)
- Currency conversion / exchange rate integration
- Real-time push notifications or WebSocket updates
- Native mobile applications
- Email notification sending (invited members see a placeholder; email delivery deferred)
- Recurring expense templates
- Export to CSV/PDF
