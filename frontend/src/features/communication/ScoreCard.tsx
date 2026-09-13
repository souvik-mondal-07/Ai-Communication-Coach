interface ScoreCardProps {
  label: string;
  score: number;
}

function scoreColor(score: number): string {
  if (score >= 80) return "text-signal";
  if (score >= 60) return "text-warn";
  return "text-danger";
}

export function ScoreCard({ label, score }: ScoreCardProps) {
  return (
    <div className="rounded-[var(--radius-panel)] border border-border bg-surface-raised px-3 py-2.5 text-center">
      <p className={`font-display text-xl font-semibold ${scoreColor(score)}`}>{score}</p>
      <p className="mt-0.5 text-[11px] text-text-muted">{label}</p>
    </div>
  );
}
