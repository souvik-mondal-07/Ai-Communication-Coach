import { useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ShieldHalf } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { AnswerFeedback } from "@/features/cybersecurity/AnswerFeedback";
import {
  DIFFICULTY_LABELS,
  MODE_LABELS,
  QUESTION_TYPE_LABELS,
} from "@/features/cybersecurity/cybersecurityTypes";
import { PracticeHints } from "@/features/cybersecurity/practice/PracticeHints";
import { PracticeSummary } from "@/features/cybersecurity/practice/PracticeSummary";
import { PracticeTimer } from "@/features/cybersecurity/practice/PracticeTimer";
import { answeredCount, progressBar } from "@/features/cybersecurity/practice/practiceUtils";
import { QuestionCard } from "@/features/cybersecurity/QuestionCard";
import { usePracticeStore } from "@/store/practiceStore";

const MAX_HINTS = 3;

function Badge({ children }: { children: React.ReactNode }) {
  return (
    <span className="rounded-full border border-border px-2 py-0.5 text-[11px] text-text-secondary">{children}</span>
  );
}

export function PracticeSession() {
  const navigate = useNavigate();
  const { sessionId } = useParams<{ sessionId: string }>();
  const {
    session, currentIndex, drafts, deadlineMs, isLoading, isSubmitting, isHintLoading, isAdvancing, error,
    load, setDraft, submitCurrentAnswer, requestHint, revealExplanation, goToNext, complete, reset, clearError,
  } = usePracticeStore();

  // Resume: after a refresh (or opening from History) the store is empty, so ask the server.
  useEffect(() => {
    if (sessionId && usePracticeStore.getState().session?.session_id !== sessionId) {
      void load(sessionId);
    }
  }, [sessionId, load]);

  const loadedHere = session !== null && session.session_id === sessionId;

  if (!loadedHere) {
    if (isLoading || (!error && sessionId)) {
      return (
        <div className="mx-auto max-w-md py-20 text-center">
          <div className="mx-auto mb-3 flex h-10 w-10 animate-pulse items-center justify-center rounded-[var(--radius-panel)] bg-signal/15 text-signal">
            <ShieldHalf size={20} />
          </div>
          <p className="text-sm text-text-secondary">Loading your practice session…</p>
        </div>
      );
    }
    return (
      <div className="mx-auto max-w-md py-16 text-center">
        <p className="text-sm text-text-secondary">{error ?? "No active practice session."}</p>
        <Button className="mt-4" onClick={() => navigate("/practice")}>
          Back to Practice
        </Button>
      </div>
    );
  }

  if (session.status === "completed" && session.summary) {
    return (
      <PracticeSummary
        summary={session.summary}
        onBack={() => {
          reset();
          navigate("/practice");
        }}
        onPracticeAgain={() => {
          const slug = session.topic_slug;
          const legacySingleTopic = session.mode === "topic" && session.categories.length === 1 && slug;
          reset();
          navigate(legacySingleTopic ? `/cybersecurity/${slug}` : "/practice");
        }}
        onOpenRecommendation={(route) => {
          reset();
          navigate(route);
        }}
      />
    );
  }

  const question = session.questions[currentIndex];
  const result = question?.result ?? null;
  const total = session.question_count;
  const isLast = currentIndex >= total - 1;
  const draft = question ? (drafts[question.question_id] ?? "") : "";

  // Timer reached zero: save what's typed (the server allows a short grace window), then finish.
  async function handleExpire() {
    const state = usePracticeStore.getState();
    const q = state.session?.questions[state.currentIndex];
    const text = q ? (state.drafts[q.question_id] ?? "").trim() : "";
    if (q && !q.answered && text) {
      try {
        await state.submitCurrentAnswer(text);
      } catch {
        // Nothing more to do: completing below still saves every earlier answer.
      }
    }
    try {
      await usePracticeStore.getState().complete();
    } catch {
      // The error banner offers a retry.
    }
  }

  return (
    <div className="mx-auto max-w-2xl space-y-5">
      <div className="space-y-2">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <p className="text-xs font-medium text-signal">{MODE_LABELS[session.mode]} practice</p>
          {deadlineMs !== null && <PracticeTimer deadlineMs={deadlineMs} onExpire={() => void handleExpire()} />}
        </div>
        <h1 className="text-lg font-semibold text-text-primary">
          Question {Math.min(currentIndex + 1, total)} of {total}
        </h1>
        <p className="font-mono text-xs text-text-muted" aria-label="Progress">
          {progressBar(answeredCount(session), total)}
        </p>
        {question && (
          <div className="flex flex-wrap gap-1.5">
            {question.topic_title && <Badge>Topic: {question.topic_title}</Badge>}
            {question.difficulty && <Badge>{DIFFICULTY_LABELS[question.difficulty]}</Badge>}
            <Badge>{QUESTION_TYPE_LABELS[question.type]}</Badge>
            {session.difficulty_mode === "adaptive" && <Badge>Adaptive</Badge>}
          </div>
        )}
        {session.note && <p className="text-xs text-text-secondary">{session.note}</p>}
      </div>

      {error && (
        <div className="flex items-center justify-between gap-3 rounded-[var(--radius-panel)] border border-danger/40 bg-danger/10 px-3 py-2 text-sm text-danger">
          <span>{error}</span>
          <div className="flex shrink-0 gap-3 text-xs">
            {session.status === "in_progress" && !question && (
              <button type="button" onClick={() => void complete()} className="underline hover:no-underline">
                Finish session
              </button>
            )}
            <button type="button" onClick={clearError} className="underline hover:no-underline">
              Dismiss
            </button>
          </div>
        </div>
      )}

      <Card>
        <CardContent className="space-y-4 py-5">
          {question && !result && (
            <>
              <QuestionCard
                question={question}
                value={draft}
                onChange={(text) => setDraft(question.question_id, text)}
                isSubmitting={isSubmitting}
                onSubmit={async (answer) => {
                  try {
                    await submitCurrentAnswer(answer);
                  } catch {
                    // Surfaced via the banner; the draft stays so the user can retry.
                  }
                }}
              />
              <PracticeHints
                question={question}
                maxHints={MAX_HINTS}
                isBusy={isHintLoading || isSubmitting}
                onHint={() => void requestHint()}
                onReveal={() => void revealExplanation()}
              />
            </>
          )}

          {question && result && (
            <AnswerFeedback
              result={result}
              isLastQuestion={isLast}
              isBusy={isAdvancing}
              onNext={() => void goToNext()}
            />
          )}

          {!question && <p className="text-sm text-text-secondary">This session has no questions yet.</p>}
        </CardContent>
      </Card>

      {session.status === "in_progress" && answeredCount(session) > 0 && !isLast && (
        <div className="text-right">
          <button
            type="button"
            disabled={isAdvancing || isSubmitting}
            onClick={() => void complete().catch(() => undefined)}
            className="text-xs text-text-muted underline hover:text-text-secondary disabled:opacity-50"
          >
            End session early
          </button>
        </div>
      )}
    </div>
  );
}
