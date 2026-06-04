export const queryKeys = {
  groups: (includeArchived?: boolean) =>
    ['groups', { includeArchived: includeArchived ?? false }] as const,
  group: (id: string) => ['groups', id] as const,
  expenses: (groupId: string, filters?: object) =>
    ['groups', groupId, 'expenses', filters ?? {}] as const,
  balances: (groupId: string) => ['groups', groupId, 'balances'] as const,
  suggestions: (groupId: string) => ['groups', groupId, 'suggestions'] as const,
  settlements: (groupId: string) => ['groups', groupId, 'settlements'] as const,
} as const;
