import { useQuery } from '@tanstack/react-query';
import { apiFetch } from '@/api/client';
import { queryKeys } from '@/api/queryKeys';
import type { CurrencyBalances, CurrencySettlements, Settlement } from '@/api/types';

export function useBalances(groupId: string) {
  return useQuery({
    queryKey: queryKeys.balances(groupId),
    queryFn: () => apiFetch<CurrencyBalances>(`/groups/${groupId}/balances`),
    enabled: !!groupId,
    staleTime: 30_000,
  });
}

export function useSettlementSuggestions(groupId: string) {
  return useQuery({
    queryKey: queryKeys.suggestions(groupId),
    queryFn: () => apiFetch<CurrencySettlements>(`/groups/${groupId}/settlements/suggestions`),
    enabled: !!groupId,
    staleTime: 30_000,
  });
}

export function useSettlements(groupId: string) {
  return useQuery({
    queryKey: queryKeys.settlements(groupId),
    queryFn: () => apiFetch<Settlement[]>(`/groups/${groupId}/settlements`),
    enabled: !!groupId,
  });
}
