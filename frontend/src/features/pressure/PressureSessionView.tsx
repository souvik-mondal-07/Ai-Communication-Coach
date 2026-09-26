import { useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { InterviewProgress } from "@/features/interview/InterviewProgress";
import { PressureAnswer } from "@/features/pressure/PressureAnswer";
import { PressureChat } from "@/features/pressure/PressureChat";
import { PressureControls } from "@/features/pressure/PressureControls";
import { PressureHeader } from "@/features/pressure/PressureHeader";
import { PressureIndicator } from "@/features/pressure/PressureIndicator";
import { PressureQuestion } from "@/features/pressure/PressureQuestion";
import { PressureTimer } from "@/features/pressure/PressureTimer";
import type { InputMode, SendMessageOptions } from "@/features/voice/voiceTypes";
import { isVoiceSupported } from "@/hooks/useVoice";
import type { PressureResponseResult, PressureSessionView as SessionView } from "@/types/pressure";

interface SubmitExtras extends SendMessageOptions {
  timedOut?: boolean;
  responseDurationSeconds?: number;
}

interface PressureSessionViewProps {
  session: SessionView;
  lastResult: PressureResponseResult | null;
  isSubmitting: boolean;
  isCompleting: boolean;
  error: string | null;
  elapsedSeconds: number;
  secondsRemaining: number | null;
  timeLimitSeconds: number | null;
  onSubmit: (answer: string, options?: SubmitExtras) => Promise<void>;
  onEnd: () => void | Promise<void>;
  onDismissError: () => void;
}

/** The active pressure training session: one prompt at a time, a timer when the level has one, and live indicators. */
export function PressureSessionView({
  session,
  lastResult,
  isSubmitting,
  isCompleting,
  error,
  elapsedSeconds,
  secondsRemaining,
  timeLimitSeconds,
  onSubmit,
  onEnd,
  onDismissError,
}: PressureSessionViewProps) {
  const prompt = session.current_prompt;
  const [inputMode, setInputMode] = useState<InputMode>(
    session.input_mode === "voice" && isVoiceSupported() ? "voice" : "text"
  );
  const timedOut = timeLimitSeconds !== null && secondsRemaining === 0;

  return (
    <div className="mx-auto max-w-3xl space-y-4">
      <PressureHeader
        pressureLevel={session.pressure_level}
        mode={session.mode}
        difficulty={session.difficulty}
        elapsedSeconds={elapsedSeconds}
      />
      <InterviewProgress current={session.current_question_number} total={session.question_count} />

      {lastResult?.pressure_indicators && (
        <Card>
          <CardContent className="py-4">
            <PressureIndicator indicators={lastResult.pressure_indicators} />
          </CardContent>
        </Card>
      )}

      {error && (
        <div
          role="alert"
          className="flex items-start justify-between gap-3 rounded-[var(--radius-panel)] border border-danger/40 bg-danger/10 px-3 py-2 text-sm text-danger"
        >
          <span>{error}</span>
          <button type="button" onClick={onDismissError} className="text-xs underline">
            Dismiss
          </button>
        </div>
      )}

      {prompt && (
        <Card>
          <CardContent className="space-y-4 py-5">
            <PressureQuestion prompt={prompt} />
            {timeLimitSeconds !== null && (
              <PressureTimer secondsRemaining={secondsRemaining} timeLimitSeconds={timeLimitSeconds} />
            )}
            {/* Keyed by the prompt so the answer box (and timeout state) resets for each new prompt. */}
            <PressureAnswer
              key={`${prompt.question_number}-${prompt.follow_up_kind ?? "main"}`}
              inputMode={inputMode}
              onInputModeChange={setInputMode}
              isSubmitting={isSubmitting}
              onSubmit={onSubmit}
              timedOut={timedOut}
            />
          </CardContent>
        </Card>
      )}

      <PressureChat questions={session.questions} />
      <PressureControls answeredCount={session.answered_count} onEnd={onEnd} isEnding={isCompleting} />
    </div>
  );
}
