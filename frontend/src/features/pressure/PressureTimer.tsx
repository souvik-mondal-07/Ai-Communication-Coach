import { formatDuration } from "@/features/voice/formatDuration";
import { cn } from "@/lib/utils";

interface PressureTimerProps {
  secondsRemaining: number | null;
  timeLimitSeconds: number | null;
}

/**
 * A visible countdown. Purely a UI convenience — the backend independently
 * measures how long the answer actually took, so nothing here needs to be
 * tamper-proof (see `usePressure.ts`).
 */
export function PressureTimer({ secondsRemaining, timeLimitSeconds }: PressureTimerProps) {
  if (timeLimitSeconds === null || secondsRemaining === null) {
    return <p className="text-xs text-text-muted">No time limit for this question.</p>;
  }

  const expired = secondsRemaining <= 0;
  const low = !expired && secondsRemaining <= Math.max(5, Math.round(timeLimitSeconds * 0.2));

  return (
    <div className="flex items-center gap-2">
      <span className="text-xs text-text-muted">Time remaining</span>
      <span
        role="timer"
        aria-live="polite"
        className={cn(
          "font-mono text-sm tabular-nums",
          expired ? "font-semibold text-danger" : low ? "font-semibold text-warn" : "text-text-secondary"
        )}
      >
        {expired ? "Time's up" : formatDuration(secondsRemaining)}
      </span>
    </div>
  );
}
