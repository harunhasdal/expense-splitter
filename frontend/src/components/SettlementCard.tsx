import { useState } from 'react';
import type { SettlementSuggestion } from '@/api/types';
import { useCreateSettlement } from '@/api/hooks/useMutations';
import ConfirmationModal from './ConfirmationModal';

interface SettlementCardProps {
  suggestion: SettlementSuggestion;
  groupId: string;
}

export default function SettlementCard({ suggestion, groupId }: SettlementCardProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [customAmount, setCustomAmount] = useState(suggestion.amount);
  const createSettlement = useCreateSettlement(groupId);

  const handleConfirm = () => {
    createSettlement.mutate(
      {
        payer_id: suggestion.payer_id,
        payee_id: suggestion.payee_id,
        amount: customAmount,
        currency: suggestion.currency,
      },
      { onSuccess: () => setIsOpen(false) },
    );
  };

  return (
    <div
      data-testid={`settlement-card-${suggestion.payer_id}-${suggestion.payee_id}`}
      style={{
        border: '1px solid #e0e0e0', borderRadius: 8, padding: '1rem',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        opacity: createSettlement.isPending ? 0.6 : 1,
      }}
    >
      <span>
        <strong>{suggestion.payer_name || suggestion.payer_id.slice(0, 8)}</strong>
        {' owes '}
        <strong>{suggestion.payee_name || suggestion.payee_id.slice(0, 8)}</strong>
        {` ${parseFloat(suggestion.amount).toFixed(2)} ${suggestion.currency}`}
      </span>
      <button
        onClick={() => setIsOpen(true)}
        disabled={createSettlement.isPending}
        data-testid="settlement-card-settle-button"
        style={{ padding: '0.4rem 0.8rem', background: '#1976d2', color: '#fff', border: 'none', borderRadius: 4, cursor: 'pointer' }}
      >
        {createSettlement.isPending ? 'Settling…' : 'Mark as settled'}
      </button>

      <ConfirmationModal
        isOpen={isOpen}
        title="Confirm Settlement"
        description={`${suggestion.payer_name || 'Payer'} pays ${suggestion.payee_name || 'Payee'}`}
        confirmLabel="Confirm"
        onConfirm={handleConfirm}
        onCancel={() => setIsOpen(false)}
        isLoading={createSettlement.isPending}
      >
        <div style={{ marginBottom: '0.5rem' }}>
          <label htmlFor="settlement-amount" style={{ display: 'block', marginBottom: 4 }}>
            Amount ({suggestion.currency})
          </label>
          <input
            id="settlement-amount"
            type="number"
            min="0.01"
            step="0.01"
            value={customAmount}
            onChange={(e) => setCustomAmount(e.target.value)}
            data-testid="settlement-amount-input"
            style={{ width: '100%', padding: '0.4rem', boxSizing: 'border-box' }}
          />
        </div>
      </ConfirmationModal>
    </div>
  );
}
