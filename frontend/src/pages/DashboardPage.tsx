import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useGroups } from '@/api/hooks/useGroups';
import { useCreateGroup } from '@/api/hooks/useMutations';
import GroupCard from '@/components/GroupCard';
import LoadingSkeleton from '@/components/LoadingSkeleton';

export default function DashboardPage() {
  const navigate = useNavigate();
  const [includeArchived, setIncludeArchived] = useState(false);
  const [showNewGroup, setShowNewGroup] = useState(false);
  const [groupName, setGroupName] = useState('');
  const [groupDesc, setGroupDesc] = useState('');

  const { data: groups, isLoading, isError } = useGroups(includeArchived);
  const createGroup = useCreateGroup();

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!groupName.trim()) return;
    createGroup.mutate(
      { name: groupName.trim(), description: groupDesc.trim() || undefined },
      {
        onSuccess: () => {
          setShowNewGroup(false);
          setGroupName('');
          setGroupDesc('');
        },
      },
    );
  };

  return (
    <div style={{ maxWidth: 800, margin: '0 auto', padding: '1.5rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <h1 style={{ margin: 0 }}>My Groups</h1>
        <button
          onClick={() => setShowNewGroup(true)}
          data-testid="dashboard-new-group-button"
          style={{ padding: '0.5rem 1rem', background: '#1976d2', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer' }}
        >
          + New Group
        </button>
      </div>

      <label style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: '1rem', fontSize: 14, color: '#555' }}>
        <input
          type="checkbox"
          checked={includeArchived}
          onChange={(e) => setIncludeArchived(e.target.checked)}
          data-testid="dashboard-show-archived-toggle"
        />
        Show archived
      </label>

      {isLoading && <LoadingSkeleton variant="card" count={3} />}
      {isError && <p style={{ color: '#c62828' }}>Failed to load groups. Please refresh.</p>}
      {groups?.length === 0 && (
        <div style={{ textAlign: 'center', padding: '3rem', color: '#888' }}>
          <p style={{ fontSize: '1.1rem', margin: '0 0 1rem' }}>No groups yet</p>
          <button
            onClick={() => setShowNewGroup(true)}
            data-testid="dashboard-first-group-button"
            style={{ padding: '0.5rem 1.25rem', background: '#1976d2', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer' }}
          >
            Create your first group
          </button>
        </div>
      )}

      <div style={{ display: 'grid', gap: '0.75rem' }}>
        {groups?.map((group) => (
          <GroupCard key={group.id} group={group} onSelect={(id) => navigate(`/groups/${id}`)} />
        ))}
      </div>

      {showNewGroup && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
          <form
            onSubmit={handleCreate}
            data-testid="new-group-form"
            style={{ background: '#fff', borderRadius: 8, padding: '1.5rem', width: 400 }}
          >
            <h2 style={{ margin: '0 0 1rem' }}>New Group</h2>
            <label htmlFor="group-name" style={{ display: 'block', marginBottom: 4, fontWeight: 500 }}>Name *</label>
            <input
              id="group-name"
              type="text"
              maxLength={100}
              required
              value={groupName}
              onChange={(e) => setGroupName(e.target.value)}
              data-testid="new-group-name-input"
              style={{ width: '100%', padding: '0.5rem', boxSizing: 'border-box', marginBottom: '1rem' }}
            />
            <label htmlFor="group-desc" style={{ display: 'block', marginBottom: 4, fontWeight: 500 }}>Description</label>
            <textarea
              id="group-desc"
              maxLength={500}
              value={groupDesc}
              onChange={(e) => setGroupDesc(e.target.value)}
              data-testid="new-group-desc-input"
              style={{ width: '100%', padding: '0.5rem', boxSizing: 'border-box', marginBottom: '1rem', resize: 'vertical' }}
            />
            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
              <button type="button" onClick={() => setShowNewGroup(false)}>Cancel</button>
              <button
                type="submit"
                disabled={!groupName.trim() || createGroup.isPending}
                data-testid="new-group-submit-button"
                style={{ padding: '0.5rem 1rem', background: '#1976d2', color: '#fff', border: 'none', borderRadius: 4, cursor: 'pointer' }}
              >
                {createGroup.isPending ? 'Creating…' : 'Create'}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
