import type { CurrencyBalances, Member } from '@/api/types';

function memberName(members: Member[], memberId: string): string {
  return members.find((m) => m.id === memberId)?.display_name ?? memberId.slice(0, 8);
}

function formatAmount(amount: string): string {
  const n = parseFloat(amount);
  const prefix = n > 0 ? '+' : '';
  return `${prefix}${n.toFixed(2)}`;
}

function amountColor(amount: string): string {
  const n = parseFloat(amount);
  if (n > 0) return '#2e7d32';
  if (n < 0) return '#c62828';
  return '#555';
}

interface BalanceTableProps {
  balances: CurrencyBalances;
  members: Member[];
}

export default function BalanceTable({ balances, members }: BalanceTableProps) {
  const currencies = Object.keys(balances.balances);

  if (currencies.length === 0) {
    return <p style={{ color: '#555' }}>All settled up! ✓</p>;
  }

  return (
    <div data-testid="balance-table">
      {currencies.map((currency) => (
        <div key={currency} style={{ marginBottom: '1.5rem' }}>
          <h4 style={{ margin: '0 0 0.5rem', color: '#555' }}>{currency}</h4>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '2px solid #e0e0e0' }}>
                <th style={{ textAlign: 'left', padding: '0.5rem', fontWeight: 600 }}>Member</th>
                <th style={{ textAlign: 'right', padding: '0.5rem', fontWeight: 600 }}>Balance</th>
              </tr>
            </thead>
            <tbody>
              {balances.balances[currency].map((b) => (
                <tr
                  key={b.member_id}
                  data-testid={`balance-row-${b.member_id}`}
                  style={{ borderBottom: '1px solid #f0f0f0' }}
                >
                  <td style={{ padding: '0.5rem' }}>
                    {b.display_name || memberName(members, b.member_id)}
                  </td>
                  <td style={{ padding: '0.5rem', textAlign: 'right', color: amountColor(b.net_amount), fontWeight: 500 }}>
                    {formatAmount(b.net_amount)} {currency}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}
    </div>
  );
}
