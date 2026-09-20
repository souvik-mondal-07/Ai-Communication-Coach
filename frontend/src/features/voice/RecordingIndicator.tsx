import { formatDuration } from "@/features/voice/formatDuration";

interface RecordingIndicatorProps {
  elapsedSeconds: number;
  maxSeconds: number;
}

export function RecordingIndicator({ elapsedSeconds, maxSeconds }: RecordingIndicatorProps) {
  return (
    <div className="flex items-center gap-3" role="status" aria-live="polite">
      <span className="flex items-center gap-1.5 text-sm font-medium text-danger">
        <span aria-hidden="true" className="animate-pulse">
          🔴
        </span>
        Recording...
      </span>
      <span className="font-mono text-sm tabular-nums text-text-primary">
        {formatDuration(elapsedSeconds)}
      </span>
      <span className="text-xs text-text-muted">(max {formatDuration(maxSeconds)})</span>
    </div>
  );
}
