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
          href="/auth/google/login"
          data-testid="signin-google-button"
          style={{
            display: 'block', padding: '0.75rem', marginBottom: '0.75rem',
            border: '1px solid #dadce0', borderRadius: 6, textDecoration: 'none',
            color: '#3c4043', fontWeight: 500,
          }}
        >
          Continue with Google
        </a>

        <a
          href="/auth/github/login"
          data-testid="signin-github-button"
          style={{
            display: 'block', padding: '0.75rem',
            border: '1px solid #dadce0', borderRadius: 6, textDecoration: 'none',
            color: '#3c4043', fontWeight: 500,
          }}
        >
          Continue with GitHub
        </a>
      </div>
    </div>
  );
}
