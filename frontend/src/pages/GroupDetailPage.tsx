import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useGroup } from '@/api/hooks/useGroups';
import { useBalances, useSettlementSuggestions } from '@/api/hooks/useBalances';
import BalanceTable from '@/components/BalanceTable';
import LoadingSkeleton from '@/components/LoadingSkeleton';
import SettlementCard from '@/components/SettlementCard';

type Tab = 'balances' | 'expenses';

export default function GroupDetailPage() {
  const { id = '' } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [tab, setTab] = useState<Tab>('balances');

  const { data: group, isLoading: groupLoading } = useGroup(id);
  const { data: balances, isLoading: balancesLoading } = useBalances(id);
  const { data: suggestions, isLoading: suggestionsLoading } = useSettlementSuggestions(id);

  if (groupLoading) return <LoadingSkeleton variant="card" count={2} />;
  if (!group) return <p>Group not found.</p>;

  const allSuggestions = suggestions
    ? Object.entries(suggestions.suggestions).flatMap(([, list]) => list)
    : [];

  return (
    <div style={{ maxWidth: 800, margin: '0 auto', padding: '1.5rem' }}>
      <button onClick={() => navigate('/dashboard')} style={{ marginBottom: '1rem', cursor: 'pointer', background: 'none', border: 'none', color: '#1976d2' }}>
        ← Back to Dashboard
      </button>
      <h1 style={{ margin: '0 0 0.5rem' }}>{group.name}</h1>
      <p style={{ color: '#666', marginTop: 0 }}>{group.members.filter((m) => !m.removed_at).length} members</p>

      {/* Tab bar */}
      <div style={{ display: 'flex', borderBottom: '2px solid #e0e0e0', marginBottom: '1.5rem' }}>
        {(['balances', 'expenses'] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => t === 'expenses' ? navigate(`/groups/${id}/expenses`) : setTab(t)}
            data-testid={`tab-${t}`}
            style={{
              padding: '0.5rem 1.25rem', border: 'none', background: 'none', cursor: 'pointer',
              borderBottom: tab === t ? '2px solid #1976d2' : 'none',
              color: tab === t ? '#1976d2' : '#555', fontWeight: tab === t ? 600 : 400,
              marginBottom: -2,
            }}
          >
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>

      {/* Balances tab */}
      {balancesLoading ? (
        <LoadingSkeleton variant="table" count={1} />
      ) : balances ? (
        <BalanceTable balances={balances} members={group.members} />
      ) : null}

      {/* Settlement suggestions */}
      {!suggestionsLoading && allSuggestions.length > 0 && (
        <div style={{ marginTop: '1.5rem' }}>
          <h3 style={{ margin: '0 0 0.75rem' }}>Settle Up</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {allSuggestions.map((s) => (
              <SettlementCard
                key={`${s.payer_id}-${s.payee_id}-${s.currency}`}
                suggestion={s}
                groupId={id}
              />
            ))}
          </div>
        </div>
      )}

      {/* Add expense button */}
      <div style={{ marginTop: '2rem' }}>
        <button
          onClick={() => navigate(`/groups/${id}/expenses/new`)}
          data-testid="group-detail-new-expense-button"
          style={{ padding: '0.6rem 1.25rem', background: '#1976d2', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer' }}
        >
          + Add Expense
        </button>
      </div>
    </div>
  );
}
