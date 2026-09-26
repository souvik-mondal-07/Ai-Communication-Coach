import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { InputModeToggle } from "@/features/voice/InputModeToggle";
import type { InputMode } from "@/features/voice/voiceTypes";
import { PressureLevelCard } from "@/features/pressure/PressureLevelCard";
import { isVoiceSupported } from "@/hooks/useVoice";
import * as pressureService from "@/services/pressureService";
import { cn } from "@/lib/utils";
import { INTERVIEW_DIFFICULTY_LABELS, QUESTION_COUNTS, type InterviewDifficulty } from "@/types/interview";
import type { PressureConfig, PressureLevelInfo, PressureMode } from "@/types/pressure";

interface PressureSetupProps {
  onStart: (config: PressureConfig) => void | Promise<void>;
  isStarting: boolean;
  error: string | null;
}

const MODE_OPTIONS: { value: PressureMode; label: string; description: string }[] = [
  { value: "interview", label: "Interview", description: "Cybersecurity/technical interview questions" },
  { value: "communication", label: "Communication", description: "Behavioral / HR-style pressure practice" },
];

function Pill({
  selected,
  onClick,
  children,
}: {
  selected: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      role="radio"
      aria-checked={selected}
      onClick={onClick}
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

export function PressureSetup({ onStart, isStarting, error }: PressureSetupProps) {
  const voiceSupported = isVoiceSupported();
  const [levels, setLevels] = useState<PressureLevelInfo[] | null>(null);
  const [levelsError, setLevelsError] = useState<string | null>(null);
  const [pressureLevel, setPressureLevel] = useState<PressureConfig["pressureLevel"]>(2);
  const [mode, setMode] = useState<PressureMode>("interview");
  const [difficulty, setDifficulty] = useState<InterviewDifficulty>("intermediate");
  const [questionCount, setQuestionCount] = useState<number>(10);
  const [inputMode, setInputMode] = useState<InputMode>("text");

  useEffect(() => {
    let cancelled = false;
    pressureService
      .getPressureLevels()
      .then((data) => {
        if (!cancelled) setLevels(data);
      })
      .catch(() => {
        if (!cancelled) setLevelsError("Couldn't load pressure levels. Please refresh the page.");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <Card>
      <CardContent className="space-y-5 py-5">
        <div>
          <p className="mb-2 text-xs font-medium text-text-muted">Pressure Level</p>
          {levelsError && <p className="text-sm text-danger">{levelsError}</p>}
          {!levels && !levelsError && <p className="text-sm text-text-muted">Loading levels…</p>}
          {levels && (
            <div role="radiogroup" aria-label="Pressure level" className="grid gap-2 sm:grid-cols-2">
              {levels.map((level) => (
                <PressureLevelCard
                  key={level.pressure_level}
                  level={level}
                  selected={pressureLevel === level.pressure_level}
                  onSelect={() => setPressureLevel(level.pressure_level)}
                />
              ))}
            </div>
          )}
        </div>

        <Group label="Practice Type">
          {MODE_OPTIONS.map((option) => (
            <Pill key={option.value} selected={mode === option.value} onClick={() => setMode(option.value)}>
              {option.label}
            </Pill>
          ))}
        </Group>
        <p className="-mt-3 text-xs text-text-muted">{MODE_OPTIONS.find((o) => o.value === mode)?.description}</p>

        <Group label="Difficulty">
          {(Object.keys(INTERVIEW_DIFFICULTY_LABELS) as InterviewDifficulty[]).map((value) => (
            <Pill key={value} selected={difficulty === value} onClick={() => setDifficulty(value)}>
              {INTERVIEW_DIFFICULTY_LABELS[value]}
            </Pill>
          ))}
        </Group>

        <Group label="Questions">
          {QUESTION_COUNTS.filter((c) => c <= 15).map((count) => (
            <Pill key={count} selected={questionCount === count} onClick={() => setQuestionCount(count)}>
              {count}
            </Pill>
          ))}
        </Group>

        <div className="space-y-2">
          <p className="text-xs font-medium text-text-muted">Mode</p>
          <InputModeToggle value={inputMode} onChange={setInputMode} voiceSupported={voiceSupported} />
          {!voiceSupported && (
            <p className="text-xs text-text-muted">
              Voice needs a browser with microphone recording support and a secure (https/localhost) connection.
            </p>
          )}
        </div>

        {error && (
          <p role="alert" className="rounded-[var(--radius-panel)] border border-danger/40 bg-danger/10 px-3 py-2 text-sm text-danger">
            {error}
          </p>
        )}

        <Button
          size="lg"
          disabled={isStarting || !levels}
          onClick={() =>
            void onStart({
              pressureLevel,
              mode,
              interviewType: "mixed",
              difficulty,
              questionCount,
              inputMode,
            })
          }
        >
          {isStarting ? "Starting…" : "Start Pressure Training"}
        </Button>
      </CardContent>
    </Card>
  );
}
