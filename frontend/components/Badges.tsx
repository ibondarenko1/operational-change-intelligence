export function RiskBadge({ level }: { level: string }) {
  return <span className={`badge risk-${level}`}>{level}</span>;
}

export function OutcomeBadge({ outcome, incident }: { outcome: string; incident?: boolean }) {
  const className = outcome === "failed" || incident ? "badge outcome-failed" : "badge outcome-success";
  return <span className={className}>{incident ? `${outcome} + incident` : outcome}</span>;
}
