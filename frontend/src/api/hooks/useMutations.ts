import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiFetch } from '@/api/client';
import { queryKeys } from '@/api/queryKeys';
import type {
  AddMemberRequest,
  CreateExpenseRequest,
  CreateGroupRequest,
  CreateSettlementRequest,
  Expense,
  Group,
  Member,
  Settlement,
} from '@/api/types';

export function useCreateGroup() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: CreateGroupRequest) =>
      apiFetch<Group>('/groups', { method: 'POST', body: JSON.stringify(data) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['groups'] }),
  });
}

export function useArchiveGroup() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ groupId, force = false }: { groupId: string; force?: boolean }) =>
      apiFetch<Group>(`/groups/${groupId}`, {
        method: 'PATCH',
        body: JSON.stringify({ archived: true, force }),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['groups'] }),
  });
}

export function useAddMember(groupId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: AddMemberRequest) =>
      apiFetch<Member>(`/groups/${groupId}/members`, {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.group(groupId) }),
  });
}

export function useCreateExpense(groupId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: CreateExpenseRequest) =>
      apiFetch<Expense>(`/groups/${groupId}/expenses`, {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.expenses(groupId) });
      qc.invalidateQueries({ queryKey: queryKeys.balances(groupId) });
      qc.invalidateQueries({ queryKey: queryKeys.suggestions(groupId) });
    },
  });
}

export function useArchiveExpense(groupId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (expenseId: string) =>
      apiFetch<Expense>(`/groups/${groupId}/expenses/${expenseId}`, { method: 'PATCH' }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.expenses(groupId) });
      qc.invalidateQueries({ queryKey: queryKeys.balances(groupId) });
      qc.invalidateQueries({ queryKey: queryKeys.suggestions(groupId) });
    },
  });
}

export function useCreateSettlement(groupId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: CreateSettlementRequest) =>
      apiFetch<Settlement>(`/groups/${groupId}/settlements`, {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.balances(groupId) });
      qc.invalidateQueries({ queryKey: queryKeys.suggestions(groupId) });
      qc.invalidateQueries({ queryKey: queryKeys.settlements(groupId) });
    },
  });
}
