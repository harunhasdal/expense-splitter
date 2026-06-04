export interface User {
  id: string;
  email: string;
  display_name: string;
  avatar_url: string | null;
  created_at: string;
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

export interface Group {
  id: string;
  name: string;
  description: string | null;
  owner_id: string;
  created_at: string;
  archived_at: string | null;
  members: Member[];
}

export type SplitType = 'EQUAL' | 'EXACT' | 'PERCENTAGE' | 'RATIO';

export interface SplitDetail {
  member_id: string;
  value?: string | null;
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
  amount: string;
  currency: string;
  expense_date: string;
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

export interface Settlement {
  id: string;
  group_id: string;
  payer_id: string;
  payee_id: string;
  amount: string;
  currency: string;
  recorded_at: string;
}

export interface MemberBalance {
  member_id: string;
  display_name: string;
  net_amount: string;
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
  balances: Record<string, MemberBalance[]>;
}

export interface CurrencySettlements {
  suggestions: Record<string, SettlementSuggestion[]>;
}

// Request types
export interface CreateGroupRequest {
  name: string;
  description?: string;
}

export interface AddMemberRequest {
  email: string;
}

export interface CreateExpenseRequest {
  description: string;
  amount: string;
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

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = 'ApiError';
  }
}
