# End-to-End Test Instructions

## Purpose

Validate complete user workflows across the full stack (Frontend SPA → Backend API → Balance Engine → Database) from a user's perspective.

These are manual E2E tests using a browser. Automated E2E (Playwright/Cypress) is out of scope for this release but can be added in a follow-up unit.

---

## Prerequisites

Full stack running:

```bash
docker-compose up --build -d
```

Open browser: `http://localhost:5173`

---

## E2E Workflow 1: Sign In and Group Creation (US-3-1, US-3-2)

1. Navigate to `http://localhost:5173`
2. Verify Sign In page shows "Sign in with Google" and "Sign in with GitHub" buttons
3. Click one of the OAuth providers — complete the OAuth flow
4. Expect redirect to `/dashboard`
5. Verify dashboard shows empty group list with a "Create Group" button
6. Click "Create Group", enter name "Weekend Trip", submit
7. Verify new group card appears in the dashboard list

**Pass criteria**: No JavaScript errors in console; group card visible.

---

## E2E Workflow 2: Add Members and Log Expense (US-3-3, US-3-4)

1. From dashboard, click into "Weekend Trip" group
2. Verify Group Detail page shows Balances tab and Members section
3. Click "Add Member", enter an email address, submit
4. Verify member appears in the member list
5. Click "Add Expense"
6. Fill in:
   - Description: "Hotel"
   - Amount: 300.00
   - Currency: USD
   - Paid by: (yourself)
   - Split type: Equal
7. Submit expense
8. Verify expense appears in the Expenses tab
9. Navigate to Balances tab — verify the new member owes you USD 150.00

**Pass criteria**: Expense persisted; balance reflects correct equal split.

---

## E2E Workflow 3: Settlement Flow (US-3-5)

1. From Group Detail, Balances tab, locate the settlement suggestion card
2. Verify suggestion shows correct payer, payee, and amount
3. Click "Settle Up"
4. Confirm the amount in the modal (optionally edit to partial amount)
5. Confirm settlement
6. Verify settlement card disappears (or shows settled state)
7. Verify balances update to zero (or remaining amount)

**Pass criteria**: Settlement recorded; balance updates immediately (optimistic UI).

---

## E2E Workflow 4: Expense List, Search, and Archive (US-3-6)

1. From Group Detail, navigate to Expenses tab
2. Verify paginated expense list shows "Hotel" entry
3. Use the payer filter to filter by your user — expense remains visible
4. Click "Archive" on the "Hotel" expense
5. Verify expense row shows archived state (strikethrough)
6. Toggle "Show archived" — verify archived expense is visible/hidden correctly

**Pass criteria**: Archive, filter, and pagination work without page reload errors.

---

## E2E Workflow 5: Split Types (US-2-1 to US-2-4 via UI)

Repeat Workflow 2's expense creation for each split type:

| Split Type | Test Input | Expected Balance |
|---|---|---|
| Equal | 3 members, $90 | each -$30 |
| Exact | member A=$50, member B=$50 | A: -$50, B: -$50 |
| Percentage | A=60%, B=40%, $100 | A: -$60, B: -$40 |
| Ratio | A:2, B:1, $90 | A: -$60, B: -$30 |

Verify the SplitTypeSelector running-sum indicator shows correct subtotals before submission.

**Pass criteria**: All split types produce correct balances in the Balances tab.

---

## E2E Workflow 6: Archived Group

1. From dashboard, click into a group
2. Click "Archive Group"
3. Confirm archival in the modal
4. Return to dashboard
5. Toggle "Show archived groups"
6. Verify archived group appears with an "Archived" badge

**Pass criteria**: Group archived; visible only when archived toggle is enabled.

---

## Regression Checklist

After completing all workflows, verify these do not regress:

- [ ] No console errors on any page
- [ ] `http://localhost:8000/health` returns `{"status": "ok"}`
- [ ] TypeScript build still passes: `cd frontend && pnpm run type-check`
- [ ] Backend tests still pass: `cd backend && uv run pytest tests/`
- [ ] Sign-out clears JWT cookie and redirects to sign-in page
