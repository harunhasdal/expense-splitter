import { useQuery } from '@tanstack/react-query';
import { apiFetch } from '@/api/client';
import { queryKeys } from '@/api/queryKeys';
import type { Group } from '@/api/types';

export function useGroups(includeArchived = false) {
  return useQuery({
    queryKey: queryKeys.groups(includeArchived),
    queryFn: () =>
      apiFetch<Group[]>(`/groups?include_archived=${includeArchived}`),
  });
}

export function useGroup(id: string) {
  return useQuery({
    queryKey: queryKeys.group(id),
    queryFn: () => apiFetch<Group>(`/groups/${id}`),
    enabled: !!id,
  });
}
