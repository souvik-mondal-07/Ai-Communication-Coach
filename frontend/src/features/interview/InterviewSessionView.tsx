import { useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { InterviewAnswer } from "@/features/interview/InterviewAnswer";
import { InterviewChat } from "@/features/interview/InterviewChat";
import { InterviewControls } from "@/features/interview/InterviewControls";
import { InterviewHeader } from "@/features/interview/InterviewHeader";
import { InterviewProgress } from "@/features/interview/InterviewProgress";
import { InterviewQuestion } from "@/features/interview/InterviewQuestion";
import type { InputMode, SendMessageOptions } from "@/features/voice/voiceTypes";
import { isVoiceSupported } from "@/hooks/useVoice";
import type { AnswerResult, InterviewSessionView as SessionView } from "@/types/interview";

interface InterviewSessionViewProps {
  session: SessionView;
  lastResult: AnswerResult | null;
  isSubmitting: boolean;
  isCompleting: boolean;
  error: string | null;
  elapsedSeconds: number;
  onSubmit: (answer: string, options?: SendMessageOptions) => Promise<void>;
  onEnd: () => void | Promise<void>;
  onDismissError: () => void;
}

/** The active interview: one question at a time, answer input, progress, and end control. */
export function InterviewSessionView({
  session,
  lastResult,
  isSubmitting,
  isCompleting,
  error,
  elapsedSeconds,
  onSubmit,
  onEnd,
  onDismissError,
}: InterviewSessionViewProps) {
  const prompt = session.current_prompt;
  const [inputMode, setInputMode] = useState<InputMode>(
    session.mode === "voice" && isVoiceSupported() ? "voice" : "text"
  );
  const live = session.reveal_feedback ? lastResult?.evaluation : null;

  return (
    <div className="mx-auto max-w-3xl space-y-4">
      <InterviewHeader
        interviewType={session.interview_type}
        difficulty={session.difficulty}
        elapsedSeconds={elapsedSeconds}
      />
      <InterviewProgress current={session.current_question_number} total={session.question_count} />

      {live && (
        <div
          role="status"
          className="rounded-[var(--radius-panel)] border border-border bg-surface-raised px-3 py-2.5 text-sm text-text-secondary"
        >
          <p className="text-xs font-medium text-text-muted">
            Feedback on your last answer — technical {live.technical_score} · communication{" "}
            {live.communication_score}
          </p>
          <p className="mt-1">{live.feedback}</p>
          <p className="mt-1">{live.communication_feedback}</p>
        </div>
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
            <InterviewQuestion prompt={prompt} inputMode={inputMode} />
            {/* Keyed by the prompt so the answer box resets for each new question. */}
            <InterviewAnswer
              key={`${prompt.question_number}-${prompt.follow_up_index ?? "main"}`}
              inputMode={inputMode}
              onInputModeChange={setInputMode}
              isSubmitting={isSubmitting}
              onSubmit={onSubmit}
            />
          </CardContent>
        </Card>
      )}

      <InterviewChat questions={session.questions} />
      <InterviewControls answeredCount={session.answered_count} onEnd={onEnd} isEnding={isCompleting} />
    </div>
  );
}
