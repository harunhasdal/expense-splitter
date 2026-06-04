# Code Summary — Unit 3: Frontend SPA

All files created in `frontend/` (workspace root).

## Project Config
- `package.json` — React 18, TanStack Query 5, React Router v6, TypeScript strict, Vite, pnpm
- `tsconfig.json` / `tsconfig.node.json` — strict mode, @/ alias
- `vite.config.ts` — proxy /auth + /groups to localhost:8000
- `index.html`

## Core Infrastructure
- `src/main.tsx` — QueryClient + BrowserRouter + AuthProvider + AppRouter + ErrorBoundary
- `src/router.tsx` — ProtectedRoute wrapper; all 5 route definitions
- `src/auth/AuthContext.tsx` — CSRF cookie detection; sign-out flow; useCurrentUser hook
- `src/api/client.ts` — fetch wrapper; CSRF header; 401 → signout redirect; ApiError class
- `src/api/types.ts` — all domain TypeScript types (Group, Member, Expense, Settlement, Balance, etc.)
- `src/api/queryKeys.ts` — typed cache key constants

## React Query Hooks
- `src/api/hooks/useGroups.ts` — useGroups, useGroup
- `src/api/hooks/useExpenses.ts` — useExpenses (with filters/pagination)
- `src/api/hooks/useBalances.ts` — useBalances, useSettlementSuggestions, useSettlements
- `src/api/hooks/useMutations.ts` — useCreateGroup, useArchiveGroup, useAddMember, useCreateExpense, useArchiveExpense, useCreateSettlement (all with cache invalidation)

## Shared Components (8)
- `ErrorBoundary.tsx` — class component; no PII in logs; generic fallback UI
- `LoadingSkeleton.tsx` — card/row/table variants; data-testid
- `ConfirmationModal.tsx` — controlled; data-testid on confirm/cancel buttons
- `GroupCard.tsx` — group summary; archived badge; data-testid
- `BalanceTable.tsx` — per-currency sections; +/- colour coding; data-testid per row
- `SettlementCard.tsx` — optimistic UI; ConfirmationModal with editable amount; data-testid
- `ExpenseRow.tsx` — archived strikethrough; split-type chip; data-testid
- `SplitTypeSelector.tsx` — all 4 split modes with sub-forms; running sum indicator; data-testid per input

## Pages (5)
- `SignInPage.tsx` — Google + GitHub OAuth2 buttons (US-3-1)
- `DashboardPage.tsx` — group list, new-group modal, archived toggle (US-3-2)
- `GroupDetailPage.tsx` — BalanceTable + SettlementCards + tab nav (US-3-3, US-3-5)
- `ExpenseFormPage.tsx` — full expense form with SplitTypeSelector (US-3-4)
- `ExpenseListPage.tsx` — paginated list, payer filter, archived toggle, read-only detail drawer (US-3-6)

## Stories Implemented
- US-3-1 Sign-In Screen
- US-3-2 Group Dashboard
- US-3-3 Group Detail / Balance View
- US-3-4 Expense Entry Form
- US-3-5 Settlement Completion Flow (in GroupDetailPage via SettlementCard)
- US-3-6 Expense List and Search
