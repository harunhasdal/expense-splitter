export default function SignInPage() {
  return (
    <div
      style={{
        minHeight: '100vh', display: 'flex', alignItems: 'center',
        justifyContent: 'center', background: '#f5f5f5',
      }}
    >
      <div
        style={{
          background: '#fff', borderRadius: 12, padding: '2.5rem',
          width: 360, boxShadow: '0 2px 16px rgba(0,0,0,0.1)', textAlign: 'center',
        }}
      >
        <h1 style={{ margin: '0 0 0.25rem', fontSize: '1.5rem' }}>Expense Splitter</h1>
        <p style={{ margin: '0 0 2rem', color: '#666' }}>Sign in to continue</p>

        <a
          href="/auth/login"
          data-testid="signin-button"
          style={{
            display: 'block', padding: '0.75rem',
            background: '#0066cc', borderRadius: 6, textDecoration: 'none',
            color: '#fff', fontWeight: 500,
          }}
        >
          Sign in
        </a>
      </div>
    </div>
  );
}
