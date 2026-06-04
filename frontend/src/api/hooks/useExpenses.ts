import { useQuery } from '@tanstack/react-query';
import { apiFetch } from '@/api/client';
import { queryKeys } from '@/api/queryKeys';
import type { ExpensePage } from '@/api/types';

export interface ExpenseFilters {
  payer_id?: string;
  include_archived?: boolean;
  page?: number;
  page_size?: number;
}

export function useExpenses(groupId: string, filters: ExpenseFilters = {}) {
  const params = new URLSearchParams();
  if (filters.payer_id) params.set('payer_id', filters.payer_id);
  if (filters.include_archived) params.set('include_archived', 'true');
  params.set('page', String(filters.page ?? 1));
  params.set('page_size', String(filters.page_size ?? 20));

  return useQuery({
    queryKey: queryKeys.expenses(groupId, filters),
    queryFn: () => apiFetch<ExpensePage>(`/groups/${groupId}/expenses?${params}`),
    enabled: !!groupId,
  });
}
