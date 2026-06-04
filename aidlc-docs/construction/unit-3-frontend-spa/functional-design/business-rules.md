# Business Rules — Unit 3: Frontend SPA

Frontend rules govern client-side validation and UX constraints. Server-side rules remain authoritative; frontend rules are a UX layer to prevent unnecessary round-trips.

---

## Authentication Rules (FE-AUTH)

### FE-AUTH-01: Unauthenticated redirect
Any route other than `/signin` accessed without a valid session → redirect to `/signin` preserving the original URL in state for post-login redirect.

### FE-AUTH-02: Session detection
Session presence detected by checking for the `csrf_token` cookie (non-HttpOnly, readable by JS). If absent → treat as unauthenticated.

### FE-AUTH-03: 401 interception
Any API response with status 401 → clear session state → redirect to `/signin`.

---

## Form Validation Rules (FE-VAL)

### FE-VAL-01: Group name
- Required, 1–100 characters
- Submit button disabled until non-empty
- Inline error shown on blur

### FE-VAL-02: Expense form
- Description: required, 1–255 chars
- Amount: required, > 0, numeric
- Currency: required, 3-letter code from dropdown (not freetext)
- Date: required, must not be in the future (max = today)
- Payer: required, must select a member
- At least one split member selected

### FE-VAL-03: Split-type-specific validation (client-side — mirrors server)
- **EQUAL**: no per-member input; auto-distributes
- **EXACT**: each selected member shows amount input; running sum shown; submit disabled if sum ≠ total
- **PERCENTAGE**: each member shows percentage input; running sum indicator; submit disabled if sum ≠ 100%
- **RATIO**: each member shows ratio input; no sum constraint (server computes proportions)

### FE-VAL-04: Decimal display
- All amounts displayed with 2 decimal places
- JPY and other zero-minor-unit currencies displayed as integers (detect from currency code)

### FE-VAL-05: Settlement form
- Amount: required, > 0
- Payer and payee pre-filled from suggestion; editable
- Submit disabled if payer == payee

### FE-VAL-06: Email for add member
- RFC 5322 format validated client-side before submission
- Error shown inline; no API call until valid

---

## Navigation Rules (FE-NAV)

### FE-NAV-01: Route structure
```
/signin              → SignInPage (public)
/dashboard           → DashboardPage (protected)
/groups/:id          → GroupDetailPage (protected)
/groups/:id/expenses → ExpenseListPage (protected)
/groups/:id/expenses/new → ExpenseFormPage (protected)
```

### FE-NAV-02: Deep link preservation
Unauthenticated access to a protected route → redirect to signin; after login → redirect to original route.

### FE-NAV-03: Group not found
API returns 404 for group → redirect to /dashboard with toast "Group not found".

---

## UX Rules (FE-UX)

### FE-UX-01: Loading states
All async operations show a skeleton or spinner. No blank screens during data loading.

### FE-UX-02: Error states
API errors display a user-facing toast with a generic message. Error details never shown to user (SECURITY-09).

### FE-UX-03: Optimistic UI for settlement
Marking a settlement complete: the card immediately moves to a "settling…" state before the API confirms. On error, revert with error toast.

### FE-UX-04: Cache invalidation on mutation
After any create/patch mutation, invalidate the affected query cache keys so the UI reflects updated data without manual refresh.

### FE-UX-05: data-testid attributes
All interactive elements (buttons, inputs, forms, links) carry `data-testid` attributes following the pattern `{component}-{element-role}` (e.g., `expense-form-submit-button`, `group-card-archive-button`).

### FE-UX-06: Accessibility
- All form inputs have associated `<label>` elements
- Interactive elements have `aria-label` where visual label is absent
- Color is not the sole indicator of state (balance direction also shown with +/- prefix and text)
