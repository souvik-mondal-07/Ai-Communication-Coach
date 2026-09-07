import { useNavigate } from "react-router-dom";
import { CheckCircle2, ShieldHalf } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { AnswerFeedback } from "@/features/cybersecurity/AnswerFeedback";
import { QuestionCard } from "@/features/cybersecurity/QuestionCard";
import { usePracticeStore } from "@/store/practiceStore";

export function PracticeSession() {
  const navigate = useNavigate();
  const {
    sessionId,
    topicSlug,
    topicTitle,
    questions,
    currentQuestionIndex,
    results,
    finalResult,
    isLoading,
    error,
    submitCurrentAnswer,
    goToNextQuestion,
    complete,
    reset,
    clearError,
  } = usePracticeStore();

  if (!sessionId) {
    return (
      <div className="mx-auto max-w-md py-16 text-center">
        <p className="text-sm text-text-secondary">No active practice session.</p>
        <Button className="mt-4" onClick={() => navigate("/cybersecurity")}>
          Back to Topics
        </Button>
      </div>
    );
  }

  if (finalResult) {
    return (
      <div className="mx-auto max-w-xl space-y-5 py-6 text-center">
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-[var(--radius-panel)] bg-signal/15 text-signal">
          <CheckCircle2 size={24} />
        </div>
        <h1 className="font-display text-xl font-semibold text-text-primary">
          Practice Complete
        </h1>

        <Card>
          <CardContent className="grid grid-cols-2 gap-4 py-6 text-left">
            <div>
              <p className="text-xs text-text-muted">Score</p>
              <p className="mt-1 font-display text-2xl font-semibold text-text-primary">
                {finalResult.score}%
              </p>
            </div>
            <div>
              <p className="text-xs text-text-muted">Correct</p>
              <p className="mt-1 font-display text-2xl font-semibold text-text-primary">
                {finalResult.correct_answers} / {finalResult.questions_answered}
              </p>
            </div>
            <div className="col-span-2">
              <p className="text-xs text-text-muted">Topic</p>
              <p className="mt-1 text-sm text-text-secondary">
                {finalResult.topic_title} ({finalResult.category})
              </p>
            </div>

            {finalResult.weak_areas.length === 0 ? (
              <div className="col-span-2">
                <p className="text-xs font-medium text-text-muted">Strengths</p>
                <p className="mt-1 text-sm text-signal">
                  ✓ Solid grasp of {finalResult.category.toLowerCase()} fundamentals
                </p>
              </div>
            ) : (
              <div className="col-span-2">
                <p className="text-xs font-medium text-text-muted">Needs Improvement</p>
                <ul className="mt-1 space-y-1">
                  {finalResult.recommendations.map((rec) => (
                    <li key={rec} className="text-sm text-warn">
                      • {rec}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </CardContent>
        </Card>

        <div className="flex flex-col justify-center gap-2 sm:flex-row">
          <Button
            variant="secondary"
            onClick={() => {
              reset();
              navigate("/cybersecurity");
            }}
          >
            Back to Topics
          </Button>
          <Button
            onClick={() => {
              const slug = topicSlug;
              reset();
              if (slug) navigate(`/cybersecurity/${slug}`);
            }}
          >
            Practice Again
          </Button>
        </div>
      </div>
    );
  }

  const currentQuestion = questions[currentQuestionIndex];
  const currentResult = currentQuestion ? results[currentQuestion.question_id] : undefined;
  const isLastQuestion = currentQuestionIndex === questions.length - 1;

  if (isLoading && questions.length === 0) {
    return (
      <div className="mx-auto max-w-md py-20 text-center">
        <div className="mx-auto mb-3 flex h-10 w-10 animate-pulse items-center justify-center rounded-[var(--radius-panel)] bg-signal/15 text-signal">
          <ShieldHalf size={20} />
        </div>
        <p className="text-sm text-text-secondary">Generating practice questions…</p>
      </div>
    );
  }

  async function handleNext() {
    if (isLastQuestion) {
      try {
        await complete();
      } catch {
        // Error surfaced via the banner below; stay on this screen to retry.
      }
    } else {
      goToNextQuestion();
    }
  }

  return (
    <div className="mx-auto max-w-2xl space-y-5">
      <div>
        <p className="text-xs font-medium text-signal">{topicTitle}</p>
        <h1 className="mt-1 text-lg font-semibold text-text-primary">
          Question {currentQuestionIndex + 1} of {questions.length}
        </h1>
      </div>

      {error && (
        <div className="flex items-center justify-between gap-3 rounded-[var(--radius-panel)] border border-danger/40 bg-danger/10 px-3 py-2 text-sm text-danger">
          <span>{error}</span>
          <button type="button" onClick={clearError} className="shrink-0 text-xs underline hover:no-underline">
            Dismiss
          </button>
        </div>
      )}

      <Card>
        <CardContent className="py-5">
          {currentQuestion && !currentResult && (
            <QuestionCard
              question={currentQuestion}
              isSubmitting={isLoading}
              onSubmit={async (answer) => {
                try {
                  await submitCurrentAnswer(answer);
                } catch {
                  // Error surfaced via the banner above; the question stays
                  // visible so the user can retry.
                }
              }}
            />
          )}

          {currentQuestion && currentResult && (
            <AnswerFeedback
              result={currentResult}
              isLastQuestion={isLastQuestion}
              onNext={() => void handleNext()}
            />
          )}
        </CardContent>
      </Card>
    </div>
  );
}
