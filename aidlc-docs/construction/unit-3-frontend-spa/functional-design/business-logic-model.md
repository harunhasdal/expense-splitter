# Business Logic Model — Unit 3: Frontend SPA

---

## Application Structure

```
frontend/src/
  main.tsx                  App entry: QueryClientProvider, AuthProvider, RouterProvider
  router.tsx                React Router v6 routes
  auth/
    AuthContext.tsx          Session state; useCurrentUser() hook
    useAuth.ts               sign-out helper
  api/
    client.ts               Base fetch wrapper; attaches X-CSRF-Token; handles 401
    hooks/
      useGroups.ts
      useGroup.ts
      useExpenses.ts
      useBalances.ts
      useSettlements.ts
      useMutations.ts         (createGroup, addMember, createExpense, createSettlement, archiveExpense)
  pages/
    SignInPage.tsx
    DashboardPage.tsx
    GroupDetailPage.tsx
    ExpenseFormPage.tsx
    ExpenseListPage.tsx
  components/
    GroupCard.tsx
    BalanceTable.tsx
    SettlementCard.tsx
    ExpenseRow.tsx
    SplitTypeSelector.tsx
    ConfirmationModal.tsx
    ErrorBoundary.tsx
    LoadingSkeleton.tsx
```

---

## Screen Flow: Sign-In (US-3-1)

```
/signin renders SignInPage
  |
  Show: app logo, "Continue with Google" button, "Continue with GitHub" button
  |
  User clicks provider button
    → window.location.href = /auth/{provider}/login
    → (server handles OAuth2 redirect)
  |
  After callback: server sets session cookie + csrf_token cookie
  → redirect to /dashboard (or saved URL)
  |
  AuthContext detects csrf_token cookie → sets authenticated = true
  → protected routes now accessible
```

---

## Screen Flow: Dashboard (US-3-2)

```
/dashboard renders DashboardPage
  |
  useGroups() → GET /groups
    Loading: skeleton grid
    Error: error toast
    Success: render GroupCard[] for each group
  |
  GroupCard shows:
    - group.name
    - net balance for current user across all currencies
      (derived from balances query — loaded lazily per card)
    - member count
    - "Archived" badge if archived_at set
  |
  Actions:
    "New Group" button (FAB) → opens NewGroupModal
      form: name (required), description (optional)
      submit → POST /groups → invalidate ["groups"] → close modal
    GroupCard click → navigate to /groups/:id
    "Show archived" toggle → refetch with include_archived=true
```

---

## Screen Flow: Group Detail / Balance View (US-3-3)

```
/groups/:id renders GroupDetailPage
  |
  Parallel queries:
    useGroup(id) → GET /groups/:id          (members list)
    useBalances(id) → GET /groups/:id/balances
    useSettlementSuggestions(id) → GET /groups/:id/settlements/suggestions
  |
  Tab bar: "Balances" | "Expenses"
  |
  "Balances" tab:
    BalanceTable: per-currency sections, each showing MemberBalance rows
      - display_name, net_amount (formatted with + or -)
      - row color: green if net > 0, red if net < 0, grey if zero
    |
    SettlementCard[] for each suggestion:
      - "payer_name owes payee_name amount currency"
      - "Mark as settled" button (data-testid="settlement-card-settle-button")
        → opens ConfirmationModal with pre-filled amount
        → confirm → POST /groups/:id/settlements
                  → invalidate ["groups", id, "balances"] + ["groups", id, "suggestions"]
  |
  "Expenses" tab:
    Link/button → navigate to /groups/:id/expenses
  |
  Header actions (owner only):
    "Add member" → opens AddMemberModal
    "Settings" → group name edit + archive button
```

---

## Screen Flow: Expense Entry Form (US-3-4)

```
/groups/:id/expenses/new renders ExpenseFormPage
  |
  useGroup(id) → load member list for payer + split selectors
  |
  Form fields (controlled):
    description: TextInput
    amount: NumberInput (Decimal, > 0)
    currency: CurrencySelect (dropdown of ISO codes)
    expense_date: DateInput (max=today)
    payer_id: MemberSelect (dropdown)
    split_type: SplitTypeSelector (segmented control: EQUAL | EXACT | PERCENTAGE | RATIO)
    split sub-form: rendered by SplitTypeSelector based on selection
      EQUAL: member checkboxes only
      EXACT: member checkboxes + amount input per member; running sum
      PERCENTAGE: member checkboxes + percentage input per member; running total with "X% remaining"
      RATIO: member checkboxes + ratio input per member (no sum constraint)
  |
  Client-side validation (FE-VAL-02, FE-VAL-03):
    Submit button disabled until all valid
    Inline error messages on blur
  |
  Submit → POST /groups/:id/expenses
    → invalidate ["groups", id, "expenses"], ["groups", id, "balances"], ["groups", id, "suggestions"]
    → navigate back to /groups/:id
    → success toast "Expense recorded"
```

---

## Screen Flow: Settlement Completion (US-3-5)

```
Settlement card "Mark as settled" button clicked
  |
  ConfirmationModal opens:
    Pre-filled: payer_name, payee_name, amount (editable), currency
    "Cancel" button → close modal, no action
    "Confirm" button (data-testid="confirmation-modal-confirm-button")
  |
  On confirm:
    Optimistic: card enters "settling…" loading state (FE-UX-03)
    POST /groups/:id/settlements {payer_id, payee_id, amount, currency}
      Success: invalidate balances + suggestions → card removed from list
      Error: revert card to normal state → show error toast
```

---

## Screen Flow: Expense List (US-3-6)

```
/groups/:id/expenses renders ExpenseListPage
  |
  useExpenses(groupId, filters) → GET /groups/:id/expenses
  |
  Controls:
    Search input → filters by description (client-side on loaded page, or re-query)
    Payer filter dropdown → refetch with payer_id param
    "Show archived" toggle → refetch with include_archived=true
    Pagination: "Previous" / "Next" buttons
  |
  ExpenseRow[] for each expense:
    description (truncated), payer display_name, amount+currency, date, split_type chip
    Archived expenses: strikethrough style + "Archived" badge
  |
  ExpenseRow click → read-only expense detail drawer
    (no edit — immutability; shows full split breakdown)
  |
  "New Expense" button → navigate to /groups/:id/expenses/new
```

---

## State Management Architecture

```
Server State (React Query):
  All API data managed by React Query
  Cache keys: queryKeys.* constants
  Invalidation on every mutation (createExpense, createSettlement, addMember, archiveGroup)
  staleTime: 30s for balances/suggestions; 60s for group/expense lists

Local/UI State (React useState/useReducer):
  Form field values (controlled inputs)
  Modal open/close state
  Active tab (Balances | Expenses)
  Optimistic loading state for settlement confirmation

Auth State (React Context):
  AuthContext: { user: User | null, isAuthenticated: boolean }
  Populated from /auth/me endpoint on app load (or inferred from csrf_token cookie)
  Cleared on logout or 401
```
