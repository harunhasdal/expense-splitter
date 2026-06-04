import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useGroup } from '@/api/hooks/useGroups';
import { useExpenses } from '@/api/hooks/useExpenses';
import ExpenseRow from '@/components/ExpenseRow';
import LoadingSkeleton from '@/components/LoadingSkeleton';
import type { Expense } from '@/api/types';

export default function ExpenseListPage() {
  const { id = '' } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { data: group } = useGroup(id);

  const [page, setPage] = useState(1);
  const [payerFilter, setPayerFilter] = useState('');
  const [includeArchived, setIncludeArchived] = useState(false);
  const [selectedExpense, setSelectedExpense] = useState<Expense | null>(null);

  const { data: expensePage, isLoading } = useExpenses(id, {
    payer_id: payerFilter || undefined,
    include_archived: includeArchived,
    page,
    page_size: 20,
  });

  const activeMembers = group?.members.filter((m) => !m.removed_at) ?? [];
  const totalPages = Math.ceil((expensePage?.total ?? 0) / 20);

  return (
    <div style={{ maxWidth: 800, margin: '0 auto', padding: '1.5rem' }}>
      <button onClick={() => navigate(`/groups/${id}`)} style={{ marginBottom: '1rem', cursor: 'pointer', background: 'none', border: 'none', color: '#1976d2' }}>
        ← Back to {group?.name ?? 'Group'}
      </button>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <h1 style={{ margin: 0 }}>Expenses</h1>
        <button
          onClick={() => navigate(`/groups/${id}/expenses/new`)}
          data-testid="expense-list-new-button"
          style={{ padding: '0.5rem 1rem', background: '#1976d2', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer' }}
        >
          + New Expense
        </button>
      </div>

      {/* Filters */}
      <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: '1rem', flexWrap: 'wrap' }}>
        <select
          value={payerFilter}
          onChange={(e) => { setPayerFilter(e.target.value); setPage(1); }}
          data-testid="expense-list-payer-filter"
          aria-label="Filter by payer"
          style={{ padding: '0.4rem' }}
        >
          <option value="">All payers</option>
          {activeMembers.map((m) => <option key={m.id} value={m.id}>{m.display_name}</option>)}
        </select>

        <label style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 14 }}>
          <input
            type="checkbox"
            checked={includeArchived}
            onChange={(e) => { setIncludeArchived(e.target.checked); setPage(1); }}
            data-testid="expense-list-show-archived"
          />
          Show archived
        </label>
      </div>

      {/* List */}
      {isLoading ? (
        <LoadingSkeleton variant="row" count={5} />
      ) : expensePage?.items.length === 0 ? (
        <p style={{ color: '#888', textAlign: 'center', padding: '2rem' }}>No expenses found.</p>
      ) : (
        <div style={{ border: '1px solid #e0e0e0', borderRadius: 8, overflow: 'hidden' }}>
          {expensePage?.items.map((expense) => (
            <ExpenseRow
              key={expense.id}
              expense={expense}
              members={group?.members ?? []}
              onClick={setSelectedExpense}
            />
          ))}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div style={{ display: 'flex', justifyContent: 'center', gap: 8, marginTop: '1rem' }}>
          <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1} data-testid="expense-list-prev">
            ← Previous
          </button>
          <span style={{ padding: '0.4rem' }}>{page} / {totalPages}</span>
          <button onClick={() => setPage((p) => Math.min(totalPages, p + 1))} disabled={page === totalPages} data-testid="expense-list-next">
            Next →
          </button>
        </div>
      )}

      {/* Read-only expense detail drawer */}
      {selectedExpense && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)', display: 'flex', justifyContent: 'flex-end', zIndex: 1000 }}>
          <div data-testid="expense-detail-drawer" style={{ background: '#fff', width: 360, padding: '1.5rem', overflowY: 'auto' }}>
            <button onClick={() => setSelectedExpense(null)} style={{ marginBottom: '1rem', cursor: 'pointer', background: 'none', border: 'none' }}>✕ Close</button>
            <h2 style={{ margin: '0 0 0.5rem' }}>{selectedExpense.description}</h2>
            <p><strong>Amount:</strong> {parseFloat(selectedExpense.amount).toFixed(2)} {selectedExpense.currency}</p>
            <p><strong>Date:</strong> {selectedExpense.expense_date}</p>
            <p><strong>Split type:</strong> {selectedExpense.split_type}</p>
            <h4 style={{ margin: '1rem 0 0.5rem' }}>Split Breakdown</h4>
            {selectedExpense.splits.map((s) => {
              const member = group?.members.find((m) => m.id === s.member_id);
              return (
                <div key={s.id} style={{ display: 'flex', justifyContent: 'space-between', padding: '0.25rem 0' }}>
                  <span>{member?.display_name ?? s.member_id.slice(0, 8)}</span>
                  <span>{parseFloat(s.computed_amount).toFixed(2)} {selectedExpense.currency}</span>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
