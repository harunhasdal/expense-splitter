interface ConfirmationModalProps {
  isOpen: boolean;
  title: string;
  description: string;
  confirmLabel?: string;
  onConfirm: () => void;
  onCancel: () => void;
  isLoading?: boolean;
  children?: React.ReactNode;
}

export default function ConfirmationModal({
  isOpen, title, description, confirmLabel = 'Confirm',
  onConfirm, onCancel, isLoading, children,
}: ConfirmationModalProps) {
  if (!isOpen) return null;
  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={title}
      data-testid="confirmation-modal"
      style={{
        position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)',
        display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000,
      }}
    >
      <div style={{ background: '#fff', borderRadius: 8, padding: '1.5rem', minWidth: 320, maxWidth: 480 }}>
        <h2 style={{ margin: '0 0 0.5rem' }}>{title}</h2>
        <p style={{ margin: '0 0 1rem', color: '#555' }}>{description}</p>
        {children}
        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', marginTop: '1rem' }}>
          <button
            onClick={onCancel}
            disabled={isLoading}
            data-testid="confirmation-modal-cancel-button"
            style={{ padding: '0.5rem 1rem', cursor: 'pointer' }}
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            disabled={isLoading}
            data-testid="confirmation-modal-confirm-button"
            style={{ padding: '0.5rem 1rem', background: '#1976d2', color: '#fff', border: 'none', borderRadius: 4, cursor: 'pointer' }}
          >
            {isLoading ? 'Processing…' : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
