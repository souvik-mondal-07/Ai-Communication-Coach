interface ScoreCardProps {
  label: string;
  /** null = not measurable (shown as an em dash, never a fake zero). */
  score: number | null;
}

function scoreColor(score: number | null): string {
  if (score === null) return "text-text-muted";
  if (score >= 80) return "text-signal";
  if (score >= 60) return "text-warn";
  return "text-danger";
}

export function ScoreCard({ label, score }: ScoreCardProps) {
  return (
    <div className="rounded-[var(--radius-panel)] border border-border bg-surface-raised px-3 py-2.5 text-center">
      <p className={`font-display text-xl font-semibold ${scoreColor(score)}`}>{score ?? "—"}</p>
      <p className="mt-0.5 text-[11px] text-text-muted">{label}</p>
    </div>
  );
}
