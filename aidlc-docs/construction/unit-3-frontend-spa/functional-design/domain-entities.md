# Domain Entities — Unit 3: Frontend SPA

TypeScript types used throughout the SPA. Generated from `openapi.json` via `openapi-typescript` — these are the canonical shapes.

---

## Core Domain Types

```typescript
// auth/types.ts
export interface User {
  id: string;           // UUID
  email: string;
  display_name: string;
  avatar_url: string | null;
  created_at: string;   // ISO 8601
}

// groups/types.ts
export interface Group {
  id: string;
  name: string;
  description: string | null;
  owner_id: string;
  created_at: string;
  archived_at: string | null;
  members: Member[];
}

export interface Member {
  id: string;
  group_id: string;
  user_id: string | null;
  email: string;
  display_name: string;
  joined_at: string;
  removed_at: string | null;
  is_pending: boolean;
}

// expenses/types.ts
export type SplitType = "EQUAL" | "EXACT" | "PERCENTAGE" | "RATIO";

export interface SplitDetail {
  member_id: string;
  value?: string | null;  // Decimal as string
}

export interface ExpenseSplit {
  id: string;
  member_id: string;
  raw_value: string | null;
  computed_amount: string;
}

export interface Expense {
  id: string;
  group_id: string;
  payer_id: string;
  description: string;
  amount: string;         // Decimal as string
  currency: string;
  expense_date: string;   // YYYY-MM-DD
  split_type: SplitType;
  created_at: string;
  archived_at: string | null;
  splits: ExpenseSplit[];
}

export interface ExpensePage {
  items: Expense[];
  total: number;
  page: number;
  page_size: number;
}

// settlements/types.ts
export interface Settlement {
  id: string;
  group_id: string;
  payer_id: string;
  payee_id: string;
  amount: string;
  currency: string;
  recorded_at: string;
}

// balance/types.ts
export interface MemberBalance {
  member_id: string;
  display_name: string;
  net_amount: string;     // Decimal as string; positive = owed to; negative = owes
}

export interface SettlementSuggestion {
  payer_id: string;
  payer_name: string;
  payee_id: string;
  payee_name: string;
  amount: string;
  currency: string;
}

export interface CurrencyBalances {
  balances: Record<string, MemberBalance[]>;  // keyed by ISO currency
}

export interface CurrencySettlements {
  suggestions: Record<string, SettlementSuggestion[]>;
}
```

---

## API Client Request Types

```typescript
// api/types.ts
export interface CreateGroupRequest {
  name: string;
  description?: string;
}

export interface AddMemberRequest {
  email: string;
}

export interface CreateExpenseRequest {
  description: string;
  amount: string;         // Decimal as string
  currency: string;
  expense_date: string;
  payer_id: string;
  split_type: SplitType;
  split_details: SplitDetail[];
}

export interface CreateSettlementRequest {
  payer_id: string;
  payee_id: string;
  amount: string;
  currency: string;
}
```

---

## React Query Cache Keys

```typescript
export const queryKeys = {
  groups: (includeArchived?: boolean) => ["groups", { includeArchived }],
  group: (id: string) => ["groups", id],
  expenses: (groupId: string, filters?: object) => ["groups", groupId, "expenses", filters],
  balances: (groupId: string) => ["groups", groupId, "balances"],
  suggestions: (groupId: string) => ["groups", groupId, "suggestions"],
  settlements: (groupId: string) => ["groups", groupId, "settlements"],
} as const;
```
