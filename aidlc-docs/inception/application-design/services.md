# Services — Expense Splitter

Each domain component contains a service class that orchestrates business operations. Services call repositories for persistence and the BalanceEngine for computation. Services do not contain direct SQL — that belongs in repositories.

---

## Backend Services

### GroupService (`backend/groups/service.py`)

**Purpose**: Orchestrates all group and membership operations.

**Operations**:
- `create_group(owner_id, name, description)` → `Group`
- `get_group(group_id, requesting_user_id)` → `Group` (enforces membership authorization)
- `list_groups(user_id, include_archived)` → `list[Group]`
- `update_group(group_id, requesting_user_id, patch)` → `Group` (owner-only)
- `archive_group(group_id, requesting_user_id)` → `Group` (checks zero balances first via BalanceService)
- `add_member(group_id, requesting_user_id, email)` → `Member`
- `remove_member(group_id, requesting_user_id, member_id)` → `None` (checks zero balance, not-sole-owner)

**Collaborators**: `GroupRepository`, `UserRepository`, `MemberRepository`, `BalanceService`

---

### ExpenseService (`backend/expenses/service.py`)

**Purpose**: Orchestrates expense recording with split validation.

**Operations**:
- `create_expense(group_id, requesting_user_id, payload)` → `Expense`
  - Delegates split validation to `BalanceEngine.validate_split()`
  - Persists expense + split records atomically
- `list_expenses(group_id, requesting_user_id, filters, pagination)` → `Page[Expense]`
- `get_expense(group_id, expense_id, requesting_user_id)` → `Expense`
- `archive_expense(group_id, expense_id, requesting_user_id)` → `Expense` (owner-only, soft-archive)

**Collaborators**: `ExpenseRepository`, `BalanceEngine`

---

### SettlementService (`backend/settlements/service.py`)

**Purpose**: Orchestrates settlement recording.

**Operations**:
- `create_settlement(group_id, requesting_user_id, payload)` → `Settlement`
- `list_settlements(group_id, requesting_user_id)` → `list[Settlement]`

**Collaborators**: `SettlementRepository`

---

### BalanceService (`backend/balance/service.py`)

**Purpose**: Orchestrates balance queries and settlement suggestions by loading data and delegating to the pure BalanceEngine module.

**Operations**:
- `get_balances(group_id, requesting_user_id)` → `dict[Currency, list[MemberBalance]]`
  - Loads all expenses and settlements for the group
  - Calls `BalanceEngine.aggregate_balances()`
- `get_settlement_suggestions(group_id, requesting_user_id)` → `dict[Currency, list[SettlementSuggestion]]`
  - Calls `BalanceEngine.aggregate_balances()` then `BalanceEngine.simplify_debts()`

**Collaborators**: `ExpenseRepository`, `SettlementRepository`, `BalanceEngine`

---

### AuthService (`backend/auth/service.py`)

**Purpose**: Orchestrates OAuth2 flow and JWT lifecycle.

**Operations**:
- `get_authorization_url(provider, state)` → `str` (redirect URL)
- `handle_callback(provider, code, state)` → `(User, jwt_token: str)`
  - Validates state, exchanges code, fetches profile, upserts user
- `validate_token(token)` → `User` (used by AuthMiddleware dependency)
- `logout(user_id)` → `None`

**Collaborators**: `UserRepository`, OAuth2 provider clients (httpx)

---

## Frontend Service Hooks (React Query)

These are the React Query hooks exposed by `ApiClient`. They act as the frontend's service layer — managing cache, loading states, and error handling.

| Hook | HTTP Call | Used By |
|---|---|---|
| `useGroups()` | `GET /groups` | DashboardPage |
| `useGroup(id)` | `GET /groups/:id` | GroupDetailPage |
| `useCreateGroup()` | `POST /groups` | DashboardPage |
| `useAddMember(groupId)` | `POST /groups/:id/members` | GroupDetailPage |
| `useExpenses(groupId, filters)` | `GET /groups/:id/expenses` | ExpenseListPage |
| `useCreateExpense(groupId)` | `POST /groups/:id/expenses` | ExpenseFormPage |
| `useBalances(groupId)` | `GET /groups/:id/balances` | GroupDetailPage |
| `useSettlementSuggestions(groupId)` | `GET /groups/:id/settlements/suggestions` | GroupDetailPage |
| `useCreateSettlement(groupId)` | `POST /groups/:id/settlements` | SettlementCard |
