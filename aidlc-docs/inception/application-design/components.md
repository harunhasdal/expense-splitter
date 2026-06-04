# Components — Expense Splitter

Architecture: Monorepo (`backend/` + `frontend/`). Backend is domain-organized FastAPI app with an embedded balance engine module. Frontend is a React/TypeScript SPA.

---

## Backend Components

### 1. AuthComponent (`backend/auth/`)

**Purpose**: Handles the full OAuth2 social login flow, JWT lifecycle, and user identity.

**Responsibilities**:
- Initiate OAuth2 authorization requests (Google, GitHub)
- Handle OAuth2 callback: validate state, exchange code for tokens, fetch user profile
- Create or match user records by email
- Issue signed JWT access tokens with expiry
- Validate JWT on every incoming authenticated request (middleware)
- Invalidate sessions on logout

**Interfaces**:
- `GET /auth/{provider}/login` — redirect to provider authorization URL
- `GET /auth/{provider}/callback` — OAuth2 callback handler
- `POST /auth/logout` — invalidate session
- `AuthMiddleware` — FastAPI dependency injected into all protected routes

**Security rules**: SECURITY-08, SECURITY-12

---

### 2. GroupComponent (`backend/groups/`)

**Purpose**: Manages group lifecycle and group membership.

**Responsibilities**:
- Create, read, update (rename/description), and archive groups
- Add members by email (create placeholder if user not yet registered)
- Remove members (enforcing balance-zero and sole-owner guards)
- Enforce ownership authorization for privileged operations

**Interfaces**:
- `POST /groups` — create group
- `GET /groups` — list authenticated user's groups (active + optionally archived)
- `GET /groups/{id}` — get single group with member list
- `PATCH /groups/{id}` — update name/description/archived flag
- `POST /groups/{id}/members` — add member
- `DELETE /groups/{id}/members/{memberId}` — remove member

**Security rules**: SECURITY-05, SECURITY-08

---

### 3. ExpenseComponent (`backend/expenses/`)

**Purpose**: Records immutable group expenses with validated split rules.

**Responsibilities**:
- Accept and validate expense payloads (amount, currency, payer, split type, split details)
- Delegate split arithmetic validation to BalanceEngine
- Persist expense and split records atomically
- Enforce immutability: no updates or hard deletes after creation
- Support soft-archive by group owner
- Return paginated, filterable expense lists

**Interfaces**:
- `POST /groups/{id}/expenses` — record expense
- `GET /groups/{id}/expenses` — list expenses (paginated, filterable)
- `GET /groups/{id}/expenses/{expenseId}` — get single expense with split detail
- `PATCH /groups/{id}/expenses/{expenseId}` — archive only (owner-only)

**Security rules**: SECURITY-05, SECURITY-08, SECURITY-13

---

### 4. SettlementComponent (`backend/settlements/`)

**Purpose**: Records immutable settlement payments between members.

**Responsibilities**:
- Accept and validate settlement payloads (payer, payee, amount, currency)
- Persist settlement as an immutable event
- Reject zero-amount settlements
- Return settlement history per group

**Interfaces**:
- `POST /groups/{id}/settlements` — record settlement
- `GET /groups/{id}/settlements` — list settlements

**Security rules**: SECURITY-05, SECURITY-08

---

### 5. BalanceEngine (`backend/balance/`)

**Purpose**: Pure-computation module for all financial arithmetic — no DB access.

**Responsibilities**:
- Validate split rules (sum checks for exact/percentage; non-zero check for ratio)
- Compute per-member share amounts for all 4 split types (equal, exact, percentage, ratio)
- Apply rounding rules ensuring shares always sum to the expense total
- Aggregate net balances per member per currency across all expenses and settlements
- Run debt-simplification algorithm to produce minimum-transfer settlement suggestions
- Expose all functions as pure Python (no FastAPI dependencies) for direct testing

**Interfaces**: Python module API (no HTTP routes — imported by service layer)

**PBT rules**: PBT-01, PBT-02, PBT-03, PBT-05, PBT-07, PBT-08, PBT-09

---

### 6. CoreInfrastructure (`backend/core/`)

**Purpose**: Shared infrastructure used by all domain components.

**Responsibilities**:
- Database session factory (SQLAlchemy async engine, connection pool)
- Application config loading from environment variables (Pydantic Settings)
- Structured logging setup (JSON output, request correlation ID, no PII)
- Global exception handler (returns generic error responses, logs details server-side)
- Security headers middleware (CSP, HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy)
- Rate limiting middleware for public-facing endpoints
- CORS configuration (explicit allowed origins only)

**Security rules**: SECURITY-01, SECURITY-03, SECURITY-04, SECURITY-07, SECURITY-09, SECURITY-11, SECURITY-15

---

## Frontend Components

### 7. AuthContext (`frontend/src/auth/`)

**Purpose**: Manages authenticated user session state across the SPA.

**Responsibilities**:
- Store and refresh JWT token (httpOnly cookie preferred; fallback: memory)
- Expose current user identity to all components via React Context
- Redirect unauthenticated users to sign-in page
- Handle logout (clear session, redirect)

---

### 8. ApiClient (`frontend/src/api/`)

**Purpose**: Typed HTTP client wrapping all backend REST calls.

**Responsibilities**:
- Define typed request/response interfaces for every API endpoint
- Attach JWT bearer token to all authenticated requests
- Handle 401 responses by redirecting to sign-in
- Expose React Query hooks for each resource (useGroups, useExpenses, useBalances, etc.)

---

### 9. Pages (`frontend/src/pages/`)

**Purpose**: Top-level route components — one per screen.

| Page | Route | Stories |
|---|---|---|
| SignInPage | `/signin` | US-3-1 |
| DashboardPage | `/dashboard` | US-3-2 |
| GroupDetailPage | `/groups/:id` | US-3-3 |
| ExpenseFormPage | `/groups/:id/expenses/new` | US-3-4 |
| ExpenseListPage | `/groups/:id/expenses` | US-3-6 |

Settlement flow is a modal/overlay triggered from GroupDetailPage (US-3-5).

---

### 10. SharedComponents (`frontend/src/components/`)

**Purpose**: Reusable UI components used across multiple pages.

| Component | Used By |
|---|---|
| GroupCard | DashboardPage |
| BalanceTable | GroupDetailPage |
| SettlementCard | GroupDetailPage |
| ExpenseRow | ExpenseListPage |
| SplitTypeSelector | ExpenseFormPage |
| ConfirmationModal | Settlement flow, archive actions |
| ErrorBoundary | All pages |
