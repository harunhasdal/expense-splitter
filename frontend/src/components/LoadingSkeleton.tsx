const style: Record<string, React.CSSProperties> = {
  skeleton: { background: '#e0e0e0', borderRadius: 4, animation: 'pulse 1.5s ease-in-out infinite' },
  card: { height: 120, marginBottom: 12 },
  row: { height: 48, marginBottom: 8 },
  table: { height: 200, marginBottom: 8 },
};

export default function LoadingSkeleton({
  variant,
  count = 3,
}: {
  variant: 'card' | 'row' | 'table';
  count?: number;
}) {
  return (
    <>
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} style={{ ...style.skeleton, ...style[variant] }} data-testid={`skeleton-${variant}`} />
      ))}
    </>
  );
}
