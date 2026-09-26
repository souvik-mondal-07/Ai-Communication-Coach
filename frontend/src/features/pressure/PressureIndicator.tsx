import type { PressureIndicators } from "@/types/pressure";

interface PressureIndicatorProps {
  indicators: PressureIndicators | null;
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[var(--radius-panel)] border border-border bg-surface-raised px-3 py-2">
      <p className="text-[11px] text-text-muted">{label}</p>
      <p className="text-sm font-medium text-text-primary">{value}</p>
    </div>
  );
}

/**
 * Neutral, observable metrics from the answer just given — never a
 * "nervousness meter". Only shows metrics that were actually measurable.
 */
export function PressureIndicator({ indicators }: PressureIndicatorProps) {
  if (!indicators) return null;

  return (
    <div className="space-y-1.5">
      <p className="text-xs font-medium text-text-muted">Communication Indicators</p>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
        {indicators.speaking_rate_wpm !== null && (
          <Metric label="Speaking Rate" value={`${indicators.speaking_rate_wpm} WPM`} />
        )}
        <Metric label="Filler Words" value={String(indicators.total_filler_words)} />
        {indicators.duration_seconds !== null && (
          <Metric label="Response Time" value={`${Math.round(indicators.duration_seconds)} sec`} />
        )}
        <Metric label="Word Count" value={String(indicators.word_count)} />
        {indicators.long_pauses !== null && <Metric label="Long Pauses" value={String(indicators.long_pauses)} />}
      </div>
    </div>
  );
}
