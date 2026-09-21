interface InterviewProgressProps {
  current: number;
  total: number;
}

/** "Question 3 of 10" with a progress bar. */
export function InterviewProgress({ current, total }: InterviewProgressProps) {
  const percent = Math.min(100, Math.round((current / total) * 100));
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between text-xs text-text-secondary">
        <span>
          Question {current} of {total}
        </span>
        <span>{percent}%</span>
      </div>
      <div
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={percent}
        aria-label="Interview progress"
        className="h-1.5 overflow-hidden rounded-full bg-surface-raised"
      >
        <div className="h-full rounded-full bg-signal transition-all" style={{ width: `${percent}%` }} />
      </div>
    </div>
  );
}
