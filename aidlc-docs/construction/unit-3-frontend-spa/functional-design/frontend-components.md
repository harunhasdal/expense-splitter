# Frontend Components — Unit 3: Frontend SPA

---

## AuthContext (`src/auth/AuthContext.tsx`)

**Props**: none (Provider wraps the app)

**State**:
```typescript
{
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}
```

**Behaviour**: On mount, checks for `csrf_token` cookie. If present, fetches `/auth/me` (or reads from JWT claims via a lightweight decode). Sets `isAuthenticated = true` on success. Exposes `useCurrentUser()` hook.

---

## API Client (`src/api/client.ts`)

No React state — pure fetch wrapper.

```typescript
function apiFetch(path: string, options?: RequestInit): Promise<Response>
// - Reads csrf_token cookie and attaches as X-CSRF-Token header
// - On 401: clears auth state, redirects to /signin
// - On non-ok: throws ApiError with status + message
```

---

## React Query Hooks (`src/api/hooks/`)

| Hook | Endpoint | Invalidated By |
|---|---|---|
| `useGroups(includeArchived?)` | GET /groups | `createGroup`, `archiveGroup` |
| `useGroup(id)` | GET /groups/:id | `addMember`, `removeMember`, `archiveGroup` |
| `useExpenses(groupId, filters?)` | GET /groups/:id/expenses | `createExpense`, `archiveExpense` |
| `useBalances(groupId)` | GET /groups/:id/balances | `createExpense`, `createSettlement`, `archiveExpense` |
| `useSettlementSuggestions(groupId)` | GET /groups/:id/settlements/suggestions | `createSettlement`, `createExpense` |
| `useSettlements(groupId)` | GET /groups/:id/settlements | `createSettlement` |

Mutations (from `useMutations.ts`):
- `useCreateGroup()` — POST /groups
- `useAddMember(groupId)` — POST /groups/:id/members
- `useArchiveGroup()` — PATCH /groups/:id `{archived: true}`
- `useCreateExpense(groupId)` — POST /groups/:id/expenses
- `useArchiveExpense(groupId)` — PATCH /groups/:id/expenses/:expId
- `useCreateSettlement(groupId)` — POST /groups/:id/settlements

---

## GroupCard (`src/components/GroupCard.tsx`)

**Props**:
```typescript
{
  group: Group;
  currentUserId: string;
  onSelect: (groupId: string) => void;
}
```

**State**: none (presentational)

**Renders**: name, member count, net balance badge (colour + +/- prefix), archived indicator

**data-testid**: `group-card-{group.id}`, `group-card-balance-badge`

---

## BalanceTable (`src/components/BalanceTable.tsx`)

**Props**:
```typescript
{
  balances: CurrencyBalances;
  members: Member[];  // for display_name lookup
}
```

**State**: none (presentational)

**Renders**: one section per currency; table rows with member name and net amount. Positive = green "+£X", negative = red "-£X".

**data-testid**: `balance-table`, `balance-row-{memberId}`

---

## SettlementCard (`src/components/SettlementCard.tsx`)

**Props**:
```typescript
{
  suggestion: SettlementSuggestion;
  groupId: string;
  onSettled: () => void;
}
```

**State**:
```typescript
{ isConfirmOpen: boolean; isSettling: boolean; }
```

**Interactions**:
- "Mark as settled" button → set `isConfirmOpen = true`
- ConfirmationModal confirm → call `useCreateSettlement`, optimistic `isSettling = true`
- On success: `onSettled()` (parent invalidates cache)
- On error: `isSettling = false`, show error toast

**data-testid**: `settlement-card-{suggestionId}`, `settlement-card-settle-button`

---

## ExpenseRow (`src/components/ExpenseRow.tsx`)

**Props**:
```typescript
{
  expense: Expense;
  members: Member[];
  onClick: (expense: Expense) => void;
}
```

**State**: none (presentational)

**Renders**: description (truncated 40 chars), payer name, amount+currency, date, split-type chip. Archived: strikethrough + badge.

**data-testid**: `expense-row-{expense.id}`

---

## SplitTypeSelector (`src/components/SplitTypeSelector.tsx`)

**Props**:
```typescript
{
  splitType: SplitType;
  members: Member[];
  selectedMemberIds: string[];
  splitDetails: SplitDetail[];
  totalAmount: string;
  onChange: (type: SplitType, details: SplitDetail[]) => void;
  onMemberToggle: (memberId: string) => void;
}
```

**State**: internal detail values per member (lifted to parent via `onChange`)

**Sub-forms**:
- EQUAL: checkboxes only; no per-member input
- EXACT: amount inputs; running sum shown; turns red if ≠ total
- PERCENTAGE: percentage inputs; running total "%X of 100%" indicator
- RATIO: ratio inputs; no sum indicator

**data-testid**: `split-type-selector`, `split-type-{type}-button`, `split-detail-{memberId}-input`

---

## ConfirmationModal (`src/components/ConfirmationModal.tsx`)

**Props**:
```typescript
{
  isOpen: boolean;
  title: string;
  description: string;
  confirmLabel?: string;
  onConfirm: () => void;
  onCancel: () => void;
  isLoading?: boolean;
  children?: React.ReactNode;  // for editable amount field in settlement flow
}
```

**State**: none (controlled by parent)

**data-testid**: `confirmation-modal`, `confirmation-modal-confirm-button`, `confirmation-modal-cancel-button`

---

## ErrorBoundary (`src/components/ErrorBoundary.tsx`)

**Props**: `{ children: React.ReactNode; fallback?: React.ReactNode }`

**Behaviour**: Catches React render errors; logs to console (no PII); shows fallback UI with "Something went wrong" message and a reload button. Never exposes error details to user (SECURITY-09).

---

## LoadingSkeleton (`src/components/LoadingSkeleton.tsx`)

**Props**: `{ variant: "card" | "row" | "table"; count?: number }`

Used during React Query `isLoading` states to prevent layout shift.
