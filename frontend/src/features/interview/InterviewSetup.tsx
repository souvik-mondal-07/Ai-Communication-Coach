import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { InputModeToggle } from "@/features/voice/InputModeToggle";
import type { InputMode } from "@/features/voice/voiceTypes";
import { isVoiceSupported } from "@/hooks/useVoice";
import { cn } from "@/lib/utils";
import {
  INTERVIEW_DIFFICULTY_LABELS,
  INTERVIEW_TYPE_OPTIONS,
  QUESTION_COUNTS,
  type InterviewConfig,
  type InterviewDifficulty,
  type InterviewType,
} from "@/types/interview";

interface InterviewSetupProps {
  onStart: (config: InterviewConfig) => void | Promise<void>;
  isStarting: boolean;
  error: string | null;
  /** Prefill (e.g. "Practice Again" from a finished interview). */
  initial?: Partial<InterviewConfig>;
}

function Pill({
  selected,
  onClick,
  children,
  hint,
}: {
  selected: boolean;
  onClick: () => void;
  children: React.ReactNode;
  hint?: string;
}) {
  return (
    <button
      type="button"
      role="radio"
      aria-checked={selected}
      onClick={onClick}
      title={hint}
      className={cn(
        "rounded-[var(--radius-panel)] border px-3 py-1.5 text-sm transition-colors",
        selected
          ? "border-signal bg-signal/15 font-medium text-signal"
          : "border-border bg-surface-raised text-text-secondary hover:border-border-strong hover:text-text-primary"
      )}
    >
      {children}
    </button>
  );
}

function Group({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <fieldset className="space-y-2">
      <legend className="text-xs font-medium text-text-muted">{label}</legend>
      <div role="radiogroup" aria-label={label} className="flex flex-wrap gap-2">
        {children}
      </div>
    </fieldset>
  );
}

export function InterviewSetup({ onStart, isStarting, error, initial }: InterviewSetupProps) {
  const voiceSupported = isVoiceSupported();
  const [interviewType, setInterviewType] = useState<InterviewType>(initial?.interviewType ?? "cybersecurity");
  const [difficulty, setDifficulty] = useState<InterviewDifficulty>(initial?.difficulty ?? "intermediate");
  const [questionCount, setQuestionCount] = useState<number>(initial?.questionCount ?? 10);
  const [mode, setMode] = useState<InputMode>(initial?.mode === "voice" && voiceSupported ? "voice" : "text");
  const [revealFeedback, setRevealFeedback] = useState(initial?.revealFeedback ?? false);

  const selectedType = INTERVIEW_TYPE_OPTIONS.find((o) => o.value === interviewType);

  return (
    <Card>
      <CardContent className="space-y-5 py-5">
        <Group label="Interview Type">
          {INTERVIEW_TYPE_OPTIONS.map((option) => (
            <Pill
              key={option.value}
              selected={interviewType === option.value}
              onClick={() => setInterviewType(option.value)}
              hint={option.description}
            >
              {option.label}
            </Pill>
          ))}
        </Group>
        {selectedType && <p className="-mt-3 text-xs text-text-muted">{selectedType.description}</p>}

        <Group label="Difficulty">
          {(Object.keys(INTERVIEW_DIFFICULTY_LABELS) as InterviewDifficulty[]).map((value) => (
            <Pill key={value} selected={difficulty === value} onClick={() => setDifficulty(value)}>
              {INTERVIEW_DIFFICULTY_LABELS[value]}
            </Pill>
          ))}
        </Group>

        <Group label="Questions">
          {QUESTION_COUNTS.map((count) => (
            <Pill key={count} selected={questionCount === count} onClick={() => setQuestionCount(count)}>
              {count}
            </Pill>
          ))}
        </Group>

        <div className="space-y-2">
          <p className="text-xs font-medium text-text-muted">Mode</p>
          <InputModeToggle value={mode} onChange={setMode} voiceSupported={voiceSupported} />
          {!voiceSupported && (
            <p className="text-xs text-text-muted">
              Voice needs a browser with microphone recording support and a secure (https/localhost) connection.
            </p>
          )}
        </div>

        <label className="flex items-start gap-2 text-sm text-text-secondary">
          <input
            type="checkbox"
            className="mt-1"
            checked={revealFeedback}
            onChange={(e) => setRevealFeedback(e.target.checked)}
          />
          <span>
            Show feedback after each answer
            <span className="block text-xs text-text-muted">
              Real interviewers don't grade you mid-interview, so this is off by default. Detailed feedback is
              always available when the interview ends.
            </span>
          </span>
        </label>

        {error && (
          <p role="alert" className="rounded-[var(--radius-panel)] border border-danger/40 bg-danger/10 px-3 py-2 text-sm text-danger">
            {error}
          </p>
        )}

        <Button
          size="lg"
          disabled={isStarting}
          onClick={() => void onStart({ interviewType, difficulty, questionCount, mode, revealFeedback })}
        >
          {isStarting ? "Starting interview…" : "Start Interview"}
        </Button>
      </CardContent>
    </Card>
  );
}
