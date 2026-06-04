import type { Expense, Member } from '@/api/types';

interface ExpenseRowProps {
  expense: Expense;
  members: Member[];
  onClick: (expense: Expense) => void;
}

const SPLIT_LABELS: Record<string, string> = {
  EQUAL: 'Equal',
  EXACT: 'Exact',
  PERCENTAGE: '%',
  RATIO: 'Ratio',
};

export default function ExpenseRow({ expense, members, onClick }: ExpenseRowProps) {
  const payer = members.find((m) => m.id === expense.payer_id);
  const isArchived = !!expense.archived_at;

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={() => onClick(expense)}
      onKeyDown={(e) => e.key === 'Enter' && onClick(expense)}
      data-testid={`expense-row-${expense.id}`}
      style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '0.75rem', borderBottom: '1px solid #f0f0f0', cursor: 'pointer',
        opacity: isArchived ? 0.6 : 1,
      }}
    >
      <div style={{ flex: 1 }}>
        <span style={{ textDecoration: isArchived ? 'line-through' : 'none', fontWeight: 500 }}>
          {expense.description.length > 40 ? expense.description.slice(0, 40) + '…' : expense.description}
        </span>
        {isArchived && (
          <span style={{ marginLeft: 8, fontSize: 11, color: '#888', border: '1px solid #ccc', padding: '1px 4px', borderRadius: 3 }}>
            Archived
          </span>
        )}
        <div style={{ fontSize: 12, color: '#666', marginTop: 2 }}>
          Paid by {payer?.display_name ?? 'Unknown'} · {expense.expense_date}
        </div>
      </div>
      <div style={{ textAlign: 'right', marginLeft: '1rem' }}>
        <div style={{ fontWeight: 500 }}>
          {parseFloat(expense.amount).toFixed(2)} {expense.currency}
        </div>
        <span style={{ fontSize: 11, background: '#e3f2fd', color: '#1565c0', padding: '2px 6px', borderRadius: 3 }}>
          {SPLIT_LABELS[expense.split_type] ?? expense.split_type}
        </span>
      </div>
    </div>
  );
}
