import type { Group } from '@/api/types';

interface GroupCardProps {
  group: Group;
  onSelect: (groupId: string) => void;
}

export default function GroupCard({ group, onSelect }: GroupCardProps) {
  const activeMembers = group.members.filter((m) => !m.removed_at).length;

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={() => onSelect(group.id)}
      onKeyDown={(e) => e.key === 'Enter' && onSelect(group.id)}
      data-testid={`group-card-${group.id}`}
      aria-label={`Open group ${group.name}`}
      style={{
        border: '1px solid #e0e0e0', borderRadius: 8, padding: '1rem',
        cursor: 'pointer', background: group.archived_at ? '#f5f5f5' : '#fff',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <h3 style={{ margin: 0 }}>{group.name}</h3>
        {group.archived_at && (
          <span style={{ fontSize: 12, color: '#888', border: '1px solid #ccc', padding: '2px 6px', borderRadius: 4 }}>
            Archived
          </span>
        )}
      </div>
      <p style={{ margin: '0.25rem 0 0', color: '#666', fontSize: 14 }}>
        {activeMembers} member{activeMembers !== 1 ? 's' : ''}
      </p>
    </div>
  );
}
