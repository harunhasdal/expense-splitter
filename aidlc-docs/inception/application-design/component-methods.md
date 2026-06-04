# Component Methods — Expense Splitter

Method signatures for all backend components. Input/output types use Python type hint notation. Detailed business rules and validation logic are defined in Functional Design (Construction phase).

---

## BalanceEngine (`backend/balance/engine.py`)

Pure functions — no I/O, no DB, fully testable in isolation.

```python
def validate_split(
    split_type: SplitType,          # Enum: EQUAL | EXACT | PERCENTAGE | RATIO
    total_amount: Decimal,
    member_ids: list[UUID],
    split_details: list[SplitDetail],  # [{member_id, value}]
) -> ValidationResult:              # {valid: bool, errors: list[str]}

def compute_shares(
    split_type: SplitType,
    total_amount: Decimal,
    member_ids: list[UUID],
    split_details: list[SplitDetail],
) -> list[MemberShare]:             # [{member_id, amount: Decimal}]
# Invariant: sum(share.amount) == total_amount (PBT-03)

def aggregate_balances(
    expenses: list[ExpenseRecord],      # [{payer_id, shares: list[MemberShare], currency}]
    settlements: list[SettlementRecord],  # [{payer_id, payee_id, amount, currency}]
) -> dict[str, list[MemberBalance]]:  # keyed by ISO currency code
# Invariant: sum(balance.net) == 0 per currency (PBT-03)

def simplify_debts(
    balances: dict[str, list[MemberBalance]],
) -> dict[str, list[SettlementSuggestion]]:  # minimum transfers per currency
# Oracle: result clears all debts when applied (PBT-05)
```

---

## GroupRepository (`backend/groups/repository.py`)

```python
async def create(db: AsyncSession, owner_id: UUID, data: GroupCreate) -> Group
async def get_by_id(db: AsyncSession, group_id: UUID) -> Group | None
async def list_for_user(db: AsyncSession, user_id: UUID, include_archived: bool) -> list[Group]
async def update(db: AsyncSession, group_id: UUID, patch: GroupUpdate) -> Group
async def get_members(db: AsyncSession, group_id: UUID) -> list[Member]
async def add_member(db: AsyncSession, group_id: UUID, user_id: UUID) -> Member
async def add_pending_member(db: AsyncSession, group_id: UUID, email: str) -> Member
async def remove_member(db: AsyncSession, group_id: UUID, member_id: UUID) -> None
async def is_member(db: AsyncSession, group_id: UUID, user_id: UUID) -> bool
async def is_owner(db: AsyncSession, group_id: UUID, user_id: UUID) -> bool
```

---

## ExpenseRepository (`backend/expenses/repository.py`)

```python
async def create(
    db: AsyncSession,
    group_id: UUID,
    data: ExpenseCreate,
    shares: list[MemberShare],
) -> Expense  # atomic: expense + split rows together

async def get_by_id(db: AsyncSession, expense_id: UUID) -> Expense | None
async def list_for_group(
    db: AsyncSession,
    group_id: UUID,
    filters: ExpenseFilters,
    pagination: Pagination,
) -> Page[Expense]

async def archive(db: AsyncSession, expense_id: UUID) -> Expense
async def get_all_for_balance(
    db: AsyncSession, group_id: UUID
) -> list[ExpenseRecord]  # lightweight projection for balance engine
```

---

## SettlementRepository (`backend/settlements/repository.py`)

```python
async def create(db: AsyncSession, group_id: UUID, data: SettlementCreate) -> Settlement
async def list_for_group(db: AsyncSession, group_id: UUID) -> list[Settlement]
async def get_all_for_balance(
    db: AsyncSession, group_id: UUID
) -> list[SettlementRecord]  # lightweight projection for balance engine
```

---

## UserRepository (`backend/auth/repository.py`)

```python
async def get_by_id(db: AsyncSession, user_id: UUID) -> User | None
async def get_by_email(db: AsyncSession, email: str) -> User | None
async def upsert_oauth_user(db: AsyncSession, profile: OAuthProfile) -> User
```

---

## AuthMiddleware (`backend/auth/middleware.py`)

```python
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
# Raises HTTP 401 if token is missing, expired, or invalid (SECURITY-08, SECURITY-12)
```

---

## CoreInfrastructure (`backend/core/`)

```python
# config.py
class Settings(BaseSettings):
    database_url: str
    jwt_secret: SecretStr
    jwt_expiry_seconds: int
    allowed_origins: list[str]
    google_client_id: str
    google_client_secret: SecretStr
    github_client_id: str
    github_client_secret: SecretStr
    log_level: str = "INFO"

# db.py
def get_db() -> AsyncGenerator[AsyncSession, None]  # FastAPI dependency

# logging.py
def setup_logging(settings: Settings) -> None  # JSON structured, correlation ID

# middleware.py
def add_security_headers(app: FastAPI) -> None  # SECURITY-04
def add_rate_limiting(app: FastAPI) -> None      # SECURITY-11

# errors.py
async def global_exception_handler(request, exc) -> JSONResponse  # SECURITY-15
```

---

## Frontend: ApiClient hooks (signatures)

```typescript
// Groups
useGroups(options?: { includeArchived?: boolean }): UseQueryResult<Group[]>
useGroup(groupId: string): UseQueryResult<GroupDetail>
useCreateGroup(): UseMutationResult<Group, Error, CreateGroupInput>
useArchiveGroup(): UseMutationResult<void, Error, string>

// Members
useAddMember(groupId: string): UseMutationResult<Member, Error, AddMemberInput>
useRemoveMember(groupId: string): UseMutationResult<void, Error, string>

// Expenses
useExpenses(groupId: string, filters?: ExpenseFilters): UseQueryResult<Page<Expense>>
useCreateExpense(groupId: string): UseMutationResult<Expense, Error, CreateExpenseInput>
useArchiveExpense(groupId: string): UseMutationResult<void, Error, string>

// Balances & Settlements
useBalances(groupId: string): UseQueryResult<CurrencyBalances>
useSettlementSuggestions(groupId: string): UseQueryResult<CurrencySettlements>
useCreateSettlement(groupId: string): UseMutationResult<Settlement, Error, CreateSettlementInput>

// Auth
useCurrentUser(): User | null  // reads AuthContext
useSignOut(): () => void
```
