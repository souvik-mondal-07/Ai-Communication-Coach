import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { isVoiceSupported } from "@/hooks/useVoice";
import { cn } from "@/lib/utils";
import {
  VOICE_DIFFICULTY_LABELS,
  VOICE_MODE_DESCRIPTIONS,
  VOICE_MODE_LABELS,
  type CreateVoiceConversationInput,
  type VoiceConversationMode,
  type VoiceDifficulty,
  type VoiceInterviewType,
} from "@/types/voiceConversation";

const MODES: VoiceConversationMode[] = ["general", "cybersecurity", "practice", "communication", "interview", "pressure"];
const DIFFICULTIES: VoiceDifficulty[] = ["beginner", "intermediate", "advanced"];
const INTERVIEW_TYPES: { value: VoiceInterviewType; label: string }[] = [
  { value: "cybersecurity", label: "Cybersecurity" },
  { value: "technical", label: "Technical" },
  { value: "hr", label: "HR" },
  { value: "scenario_based", label: "Scenario" },
  { value: "mixed", label: "Mixed" },
];
const QUESTION_COUNTS = [5, 10, 15];
const PRESSURE_LEVELS = [1, 2, 3, 4, 5];

function Pill({ selected, onClick, children }: { selected: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      type="button"
      role="radio"
      aria-checked={selected}
      onClick={onClick}
      className={cn(
        "rounded-[var(--radius-panel)] border px-3 py-1.5 text-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-signal",
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

interface ConversationSetupProps {
  onStart: (input: CreateVoiceConversationInput) => void | Promise<void>;
  isStarting: boolean;
  error: string | null;
}

export function ConversationSetup({ onStart, isStarting, error }: ConversationSetupProps) {
  const [mode, setMode] = useState<VoiceConversationMode>("cybersecurity");
  const [difficulty, setDifficulty] = useState<VoiceDifficulty>("intermediate");
  const [topic, setTopic] = useState("");
  const [interviewType, setInterviewType] = useState<VoiceInterviewType>("cybersecurity");
  const [questionCount, setQuestionCount] = useState(5);
  const [pressureLevel, setPressureLevel] = useState(2);
  const supported = isVoiceSupported();

  const needsTopic = mode === "practice";
  const structured = mode === "interview" || mode === "pressure";
  const canStart = !isStarting && (!needsTopic || topic.trim().length > 0);

  const submit = () => {
    const input: CreateVoiceConversationInput = { mode, difficulty };
    const trimmed = topic.trim();
    if (trimmed && (mode === "practice" || mode === "general" || mode === "cybersecurity")) input.topic = trimmed;
    if (structured) {
      input.interview_type = interviewType;
      input.question_count = questionCount;
    }
    if (mode === "pressure") input.pressure_level = pressureLevel;
    void onStart(input);
  };

  return (
    <Card>
      <CardContent className="space-y-5 py-5">
        <Group label="Conversation type">
          {MODES.map((value) => (
            <Pill key={value} selected={mode === value} onClick={() => setMode(value)}>
              {VOICE_MODE_LABELS[value]}
            </Pill>
          ))}
        </Group>
        <p className="-mt-3 text-xs text-text-muted">{VOICE_MODE_DESCRIPTIONS[mode]}</p>

        <Group label="Difficulty">
          {DIFFICULTIES.map((value) => (
            <Pill key={value} selected={difficulty === value} onClick={() => setDifficulty(value)}>
              {VOICE_DIFFICULTY_LABELS[value]}
            </Pill>
          ))}
        </Group>

        {structured && (
          <>
            <Group label="Interview focus">
              {INTERVIEW_TYPES.map((option) => (
                <Pill key={option.value} selected={interviewType === option.value} onClick={() => setInterviewType(option.value)}>
                  {option.label}
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
          </>
        )}

        {mode === "pressure" && (
          <Group label="Pressure level">
            {PRESSURE_LEVELS.map((level) => (
              <Pill key={level} selected={pressureLevel === level} onClick={() => setPressureLevel(level)}>
                Level {level}
              </Pill>
            ))}
          </Group>
        )}

        {(mode === "practice" || mode === "general" || mode === "cybersecurity") && (
          <div className="space-y-1.5">
            <label htmlFor="voice-topic" className="text-xs font-medium text-text-muted">
              Topic {needsTopic ? "(required)" : "(optional)"}
            </label>
            <input
              id="voice-topic"
              type="text"
              value={topic}
              maxLength={120}
              onChange={(e) => setTopic(e.target.value)}
              placeholder="e.g. SQL injection, incident response…"
              className="w-full rounded-[var(--radius-panel)] border border-border bg-surface-raised px-3 py-2 text-sm text-text-primary placeholder:text-text-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-signal"
            />
          </div>
        )}

        {!supported && (
          <p role="alert" className="rounded-[var(--radius-panel)] border border-warn/40 bg-warn/10 px-3 py-2 text-sm text-warn">
            This browser can't record audio here. Voice conversation needs a modern browser and a secure (https or localhost)
            connection.
          </p>
        )}
        {error && (
          <p role="alert" className="rounded-[var(--radius-panel)] border border-danger/40 bg-danger/10 px-3 py-2 text-sm text-danger">
            {error}
          </p>
        )}

        <p className="text-xs text-text-muted">
          You'll press the microphone for each answer. Your recording is transcribed and then deleted; the transcript is saved with
          the conversation.
        </p>

        <Button size="lg" disabled={!canStart || !supported} onClick={submit}>
          {isStarting ? "Creating…" : "Start voice conversation"}
        </Button>
      </CardContent>
    </Card>
  );
}
