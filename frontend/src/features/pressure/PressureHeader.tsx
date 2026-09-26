import { formatDuration } from "@/features/voice/formatDuration";
import { INTERVIEW_DIFFICULTY_LABELS, type InterviewDifficulty } from "@/types/interview";
import type { PressureLevel, PressureMode } from "@/types/pressure";

interface PressureHeaderProps {
  pressureLevel: PressureLevel;
  mode: PressureMode;
  difficulty: InterviewDifficulty;
  elapsedSeconds: number;
}

const LEVEL_LABELS: Record<PressureLevel, string> = {
  1: "Friendly",
  2: "Standard",
  3: "Challenging",
  4: "High Pressure",
  5: "Interview Simulation",
};

const MODE_LABELS: Record<PressureMode, string> = { interview: "Interview", communication: "Communication" };

/** Title plus the session's pressure level, mode, difficulty and elapsed time. */
export function PressureHeader({ pressureLevel, mode, difficulty, elapsedSeconds }: PressureHeaderProps) {
  return (
    <div className="flex flex-col gap-2 border-b border-border pb-3 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <h1 className="font-display text-xl font-semibold text-text-primary">Pressure Training</h1>
        <p className="mt-0.5 text-xs text-text-muted">
          Level {pressureLevel} — {LEVEL_LABELS[pressureLevel]} · {MODE_LABELS[mode]} ·{" "}
          {INTERVIEW_DIFFICULTY_LABELS[difficulty]}
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
