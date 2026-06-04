import type { Member, SplitDetail, SplitType } from '@/api/types';

interface SplitTypeSelectorProps {
  splitType: SplitType;
  members: Member[];
  selectedMemberIds: string[];
  splitDetails: SplitDetail[];
  totalAmount: string;
  onChange: (type: SplitType, details: SplitDetail[]) => void;
  onMemberToggle: (memberId: string) => void;
}

const SPLIT_TYPES: SplitType[] = ['EQUAL', 'EXACT', 'PERCENTAGE', 'RATIO'];

export default function SplitTypeSelector({
  splitType, members, selectedMemberIds, splitDetails,
  totalAmount, onChange, onMemberToggle,
}: SplitTypeSelectorProps) {
  const total = parseFloat(totalAmount) || 0;
  const selectedMembers = members.filter((m) => selectedMemberIds.includes(m.id));

  const updateDetail = (memberId: string, value: string) => {
    const updated = splitDetails.map((d) =>
      d.member_id === memberId ? { ...d, value } : d
    );
    onChange(splitType, updated);
  };

  const splitSum = splitDetails
    .filter((d) => selectedMemberIds.includes(d.member_id))
    .reduce((acc, d) => acc + parseFloat(d.value ?? '0'), 0);

  const pctRemaining = (100 - splitSum).toFixed(2);
  const exactDiff = (total - splitSum).toFixed(2);
  const sumValid = splitType === 'EXACT'
    ? Math.abs(parseFloat(exactDiff)) < 0.02
    : splitType === 'PERCENTAGE'
    ? Math.abs(splitSum - 100) < 0.02
    : true;

  return (
    <div data-testid="split-type-selector">
      {/* Split type segmented control */}
      <div style={{ display: 'flex', gap: 4, marginBottom: '1rem' }}>
        {SPLIT_TYPES.map((type) => (
          <button
            key={type}
            type="button"
            onClick={() => onChange(type, splitDetails)}
            data-testid={`split-type-${type}-button`}
            style={{
              flex: 1, padding: '0.4rem',
              background: splitType === type ? '#1976d2' : '#f5f5f5',
              color: splitType === type ? '#fff' : '#333',
              border: '1px solid #ddd', borderRadius: 4, cursor: 'pointer',
            }}
          >
            {type === 'EQUAL' ? 'Equal' : type === 'EXACT' ? 'Exact' : type === 'PERCENTAGE' ? '%' : 'Ratio'}
          </button>
        ))}
      </div>

      {/* Member rows */}
      {members.map((m) => {
        const isSelected = selectedMemberIds.includes(m.id);
        const detail = splitDetails.find((d) => d.member_id === m.id);

        return (
          <div key={m.id} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
            <input
              type="checkbox"
              id={`member-${m.id}`}
              checked={isSelected}
              onChange={() => onMemberToggle(m.id)}
              aria-label={`Include ${m.display_name}`}
            />
            <label htmlFor={`member-${m.id}`} style={{ flex: 1 }}>{m.display_name}</label>

            {splitType !== 'EQUAL' && isSelected && (
              <input
                type="number"
                min="0"
                step={splitType === 'PERCENTAGE' ? '1' : '0.01'}
                value={detail?.value ?? ''}
                onChange={(e) => updateDetail(m.id, e.target.value)}
                data-testid={`split-detail-${m.id}-input`}
                aria-label={`${splitType === 'PERCENTAGE' ? 'Percentage' : splitType === 'EXACT' ? 'Amount' : 'Ratio'} for ${m.display_name}`}
                style={{ width: 90, padding: '0.3rem', borderColor: sumValid ? '#ccc' : '#c62828' }}
              />
            )}
          </div>
        );
      })}

      {/* Running sum indicator */}
      {splitType === 'EXACT' && (
        <p style={{ color: sumValid ? '#2e7d32' : '#c62828', fontSize: 13 }}>
          {sumValid ? `✓ Sums to ${total.toFixed(2)}` : `Remaining: ${exactDiff}`}
        </p>
      )}
      {splitType === 'PERCENTAGE' && (
        <p style={{ color: sumValid ? '#2e7d32' : '#c62828', fontSize: 13 }}>
          {sumValid ? '✓ Sums to 100%' : `${pctRemaining}% remaining`}
        </p>
      )}
    </div>
  );
}
