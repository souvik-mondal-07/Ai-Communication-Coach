import { formatDuration } from "@/features/voice/formatDuration";
import {
  INTERVIEW_DIFFICULTY_LABELS,
  INTERVIEW_TYPE_LABELS,
  type InterviewDifficulty,
  type InterviewType,
} from "@/types/interview";

interface InterviewHeaderProps {
  interviewType: InterviewType;
  difficulty: InterviewDifficulty;
  elapsedSeconds: number;
}

/** Title plus the interview's type, difficulty and elapsed time (informational, not a countdown). */
export function InterviewHeader({ interviewType, difficulty, elapsedSeconds }: InterviewHeaderProps) {
  return (
    <div className="flex flex-col gap-2 border-b border-border pb-3 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <h1 className="font-display text-xl font-semibold text-text-primary">Cybersecurity Interview</h1>
        <p className="mt-0.5 text-xs text-text-muted">
          {INTERVIEW_TYPE_LABELS[interviewType]} · {INTERVIEW_DIFFICULTY_LABELS[difficulty]}
        </p>
      </div>
      <p className="text-xs text-text-muted">
        Elapsed{" "}
        <span className="font-mono text-sm tabular-nums text-text-secondary" aria-label="Elapsed time">
          {formatDuration(elapsedSeconds)}
        </span>
      </p>
    </div>
  );
}
