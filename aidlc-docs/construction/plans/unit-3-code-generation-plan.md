# Code Generation Plan — Unit 3: Frontend SPA

## Unit Context
- **Code location**: `frontend/` (monorepo, Vite + React 18 + TypeScript)
- **Stories**: US-3-1 through US-3-6
- **Dependencies**: Unit 1 REST API (consumes openapi.json for types)
- **State**: React Query + React Context; no Redux

## Story Traceability
- [ ] US-3-1 Sign-In Screen
- [ ] US-3-2 Group Dashboard
- [ ] US-3-3 Group Detail / Balance View
- [ ] US-3-4 Expense Entry Form
- [ ] US-3-5 Settlement Completion Flow
- [ ] US-3-6 Expense List and Search

---

## Generation Steps

### Step 1: Project Setup
- [ ] Create `frontend/package.json` — React 18, TypeScript, Vite, TanStack Query, React Router v6, pnpm
- [ ] Create `frontend/tsconfig.json` — strict mode
- [ ] Create `frontend/vite.config.ts` — dev proxy to localhost:8000
- [ ] Create `frontend/index.html`

### Step 2: Core Infrastructure
- [ ] Create `frontend/src/main.tsx` — app entry: QueryClientProvider + AuthProvider + RouterProvider
- [ ] Create `frontend/src/router.tsx` — all routes with protected route wrapper
- [ ] Create `frontend/src/auth/AuthContext.tsx` — session state, useCurrentUser
- [ ] Create `frontend/src/api/client.ts` — fetch wrapper with CSRF header, 401 handler

### Step 3: API Types & Hooks
- [ ] Create `frontend/src/api/types.ts` — all TypeScript domain types
- [ ] Create `frontend/src/api/queryKeys.ts` — typed cache key constants
- [ ] Create `frontend/src/api/hooks/useGroups.ts` + `useGroup.ts`
- [ ] Create `frontend/src/api/hooks/useExpenses.ts`
- [ ] Create `frontend/src/api/hooks/useBalances.ts` + `useSettlements.ts`
- [ ] Create `frontend/src/api/hooks/useMutations.ts`

### Step 4: Shared Components
- [ ] Create `frontend/src/components/ErrorBoundary.tsx`
- [ ] Create `frontend/src/components/LoadingSkeleton.tsx`
- [ ] Create `frontend/src/components/ConfirmationModal.tsx` (with data-testid)
- [ ] Create `frontend/src/components/GroupCard.tsx` (with data-testid)
- [ ] Create `frontend/src/components/BalanceTable.tsx` (with data-testid)
- [ ] Create `frontend/src/components/SettlementCard.tsx` (with data-testid, optimistic UI)
- [ ] Create `frontend/src/components/ExpenseRow.tsx` (with data-testid)
- [ ] Create `frontend/src/components/SplitTypeSelector.tsx` (with data-testid, all 4 split modes)

### Step 5: Pages
- [ ] Create `frontend/src/pages/SignInPage.tsx` (US-3-1)
- [ ] Create `frontend/src/pages/DashboardPage.tsx` (US-3-2)
- [ ] Create `frontend/src/pages/GroupDetailPage.tsx` (US-3-3, US-3-5)
- [ ] Create `frontend/src/pages/ExpenseFormPage.tsx` (US-3-4)
- [ ] Create `frontend/src/pages/ExpenseListPage.tsx` (US-3-6)

### Step 6: Code Documentation Summary
- [ ] Create `aidlc-docs/construction/unit-3-frontend-spa/code/code-summary.md`
