import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useGroup } from '@/api/hooks/useGroups';
import { useCreateExpense } from '@/api/hooks/useMutations';
import SplitTypeSelector from '@/components/SplitTypeSelector';
import type { SplitDetail, SplitType } from '@/api/types';

const TODAY = new Date().toISOString().slice(0, 10);

export default function ExpenseFormPage() {
  const { id = '' } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { data: group } = useGroup(id);
  const createExpense = useCreateExpense(id);

  const [description, setDescription] = useState('');
  const [amount, setAmount] = useState('');
  const [currency, setCurrency] = useState('GBP');
  const [expenseDate, setExpenseDate] = useState(TODAY);
  const [payerId, setPayerId] = useState('');
  const [splitType, setSplitType] = useState<SplitType>('EQUAL');
  const [selectedMemberIds, setSelectedMemberIds] = useState<string[]>([]);
  const [splitDetails, setSplitDetails] = useState<SplitDetail[]>([]);
  const [error, setError] = useState('');

  const activeMembers = group?.members.filter((m) => !m.removed_at) ?? [];

  // Initialise selected members when group loads
  if (activeMembers.length > 0 && selectedMemberIds.length === 0) {
    setSelectedMemberIds(activeMembers.map((m) => m.id));
    setSplitDetails(activeMembers.map((m) => ({ member_id: m.id, value: null })));
    if (!payerId && activeMembers[0]) setPayerId(activeMembers[0].id);
  }

  const toggleMember = (memberId: string) => {
    setSelectedMemberIds((prev) =>
      prev.includes(memberId) ? prev.filter((id) => id !== memberId) : [...prev, memberId],
    );
  };

  const handleSplitChange = (type: SplitType, details: SplitDetail[]) => {
    setSplitType(type);
    setSplitDetails(details);
  };

  const isValid =
    description.trim() &&
    parseFloat(amount) > 0 &&
    expenseDate <= TODAY &&
    payerId &&
    selectedMemberIds.length > 0;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    createExpense.mutate(
      {
        description: description.trim(),
        amount,
        currency,
        expense_date: expenseDate,
        payer_id: payerId,
        split_type: splitType,
        split_details: splitDetails.filter((d) => selectedMemberIds.includes(d.member_id)),
      },
      {
        onSuccess: () => navigate(`/groups/${id}`),
        onError: (err) => setError(err.message),
      },
    );
  };

  return (
    <div style={{ maxWidth: 600, margin: '0 auto', padding: '1.5rem' }}>
      <button onClick={() => navigate(`/groups/${id}`)} style={{ marginBottom: '1rem', cursor: 'pointer', background: 'none', border: 'none', color: '#1976d2' }}>
        ← Back
      </button>
      <h1 style={{ margin: '0 0 1.5rem' }}>Add Expense</h1>

      <form onSubmit={handleSubmit} data-testid="expense-form" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        <div>
          <label htmlFor="description" style={{ display: 'block', fontWeight: 500, marginBottom: 4 }}>Description *</label>
          <input id="description" type="text" maxLength={255} required value={description} onChange={(e) => setDescription(e.target.value)} data-testid="expense-form-description-input" style={{ width: '100%', padding: '0.5rem', boxSizing: 'border-box' }} />
        </div>

        <div style={{ display: 'flex', gap: 8 }}>
          <div style={{ flex: 1 }}>
            <label htmlFor="amount" style={{ display: 'block', fontWeight: 500, marginBottom: 4 }}>Amount *</label>
            <input id="amount" type="number" min="0.01" step="0.01" required value={amount} onChange={(e) => setAmount(e.target.value)} data-testid="expense-form-amount-input" style={{ width: '100%', padding: '0.5rem', boxSizing: 'border-box' }} />
          </div>
          <div style={{ width: 100 }}>
            <label htmlFor="currency" style={{ display: 'block', fontWeight: 500, marginBottom: 4 }}>Currency</label>
            <select id="currency" value={currency} onChange={(e) => setCurrency(e.target.value)} data-testid="expense-form-currency-select" style={{ width: '100%', padding: '0.5rem' }}>
              {['GBP', 'USD', 'EUR', 'JPY', 'AUD', 'CAD', 'CHF', 'CNY', 'SEK', 'NOK'].map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </div>
        </div>

        <div>
          <label htmlFor="expense-date" style={{ display: 'block', fontWeight: 500, marginBottom: 4 }}>Date *</label>
          <input id="expense-date" type="date" max={TODAY} required value={expenseDate} onChange={(e) => setExpenseDate(e.target.value)} data-testid="expense-form-date-input" style={{ padding: '0.5rem' }} />
        </div>

        <div>
          <label htmlFor="payer" style={{ display: 'block', fontWeight: 500, marginBottom: 4 }}>Who paid? *</label>
          <select id="payer" value={payerId} onChange={(e) => setPayerId(e.target.value)} data-testid="expense-form-payer-select" style={{ width: '100%', padding: '0.5rem' }}>
            <option value="">Select payer</option>
            {activeMembers.map((m) => <option key={m.id} value={m.id}>{m.display_name}</option>)}
          </select>
        </div>

        <div>
          <p style={{ fontWeight: 500, margin: '0 0 0.5rem' }}>Split</p>
          <SplitTypeSelector
            splitType={splitType}
            members={activeMembers}
            selectedMemberIds={selectedMemberIds}
            splitDetails={splitDetails}
            totalAmount={amount}
            onChange={handleSplitChange}
            onMemberToggle={toggleMember}
          />
        </div>

        {error && <p style={{ color: '#c62828' }}>{error}</p>}

        <button
          type="submit"
          disabled={!isValid || createExpense.isPending}
          data-testid="expense-form-submit-button"
          style={{ padding: '0.75rem', background: !isValid ? '#ccc' : '#1976d2', color: '#fff', border: 'none', borderRadius: 6, cursor: !isValid ? 'not-allowed' : 'pointer', fontWeight: 600 }}
        >
          {createExpense.isPending ? 'Saving…' : 'Record Expense'}
        </button>
      </form>
    </div>
  );
}
