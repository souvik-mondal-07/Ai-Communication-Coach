import { useNavigate, useParams } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { PressureResult } from "@/features/pressure/PressureResult";
import { PressureSessionView } from "@/features/pressure/PressureSessionView";
import { SelfReport } from "@/features/pressure/SelfReport";
import { usePressure } from "@/hooks/usePressure";

export default function PressureSessionPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();
  const {
    session,
    lastResult,
    isLoadingSession,
    isSubmitting,
    isCompleting,
    isSavingSelfReport,
    error,
    elapsedSeconds,
    secondsRemaining,
    timeLimitSeconds,
    submitAnswer,
    complete,
    submitSelfReport,
    clearError,
  } = usePressure(sessionId);

  if (isLoadingSession) {
    return <p className="py-16 text-center text-sm text-text-muted">Loading pressure training session…</p>;
  }

  if (!session) {
    return (
      <div className="mx-auto max-w-md py-16 text-center">
        <p className="text-sm text-danger">{error ?? "Pressure training session not found."}</p>
        <button
          type="button"
          onClick={() => navigate("/pressure-training")}
          className="mt-4 text-sm text-link hover:underline"
        >
          Back to Pressure Training
        </button>
      </div>
    );
  }

  if (session.status === "completed") {
    return (
      <div className="space-y-5">
        <PressureResult
          session={session}
          onBack={() => navigate("/pressure-training")}
          onPracticeAgain={() => navigate("/pressure-training")}
        />
        <div className="mx-auto max-w-3xl">
          <SelfReport
            onSubmit={submitSelfReport}
            isSaving={isSavingSelfReport}
            savedValue={session.self_reported_difficulty}
          />
        </div>
      </div>
    );
  }

  if (session.status === "abandoned") {
    return (
      <div className="mx-auto max-w-md space-y-4 py-16 text-center">
        <Card>
          <CardContent className="space-y-4 py-8">
            <h1 className="font-display text-lg font-semibold text-text-primary">Session ended</h1>
            <p className="text-sm text-text-secondary">
              You ended this session before answering any questions, so there was nothing to evaluate.
            </p>
            <Button onClick={() => navigate("/pressure-training")}>Back to Pressure Training</Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <PressureSessionView
      session={session}
      lastResult={lastResult}
      isSubmitting={isSubmitting}
      isCompleting={isCompleting}
      error={error}
      elapsedSeconds={elapsedSeconds}
      secondsRemaining={secondsRemaining}
      timeLimitSeconds={timeLimitSeconds}
      onSubmit={submitAnswer}
      onEnd={complete}
      onDismissError={clearError}
    />
  );
}
