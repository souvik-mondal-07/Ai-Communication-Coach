import { useNavigate, useParams } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { FinalInterviewResult } from "@/features/interview/FinalInterviewResult";
import { InterviewSessionView } from "@/features/interview/InterviewSessionView";
import { useInterview } from "@/hooks/useInterview";

export default function InterviewSessionPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();
  const {
    session,
    lastResult,
    isLoadingSession,
    isSubmitting,
    isCompleting,
    error,
    elapsedSeconds,
    submitAnswer,
    complete,
    clearError,
  } = useInterview(sessionId);

  if (isLoadingSession) {
    return <p className="py-16 text-center text-sm text-text-muted">Loading interview…</p>;
  }

  if (!session) {
    return (
      <div className="mx-auto max-w-md py-16 text-center">
        <p className="text-sm text-danger">{error ?? "Interview not found."}</p>
        <button
          type="button"
          onClick={() => navigate("/interview")}
          className="mt-4 text-sm text-link hover:underline"
        >
          Back to Interview
        </button>
      </div>
    );
  }

  if (session.status === "completed") {
    return (
      <FinalInterviewResult
        session={session}
        onBack={() => navigate("/interview")}
        onPracticeAgain={() =>
          navigate("/interview", {
            state: {
              preset: {
                interviewType: session.interview_type,
                difficulty: session.difficulty,
                questionCount: session.question_count,
                mode: session.mode,
                revealFeedback: session.reveal_feedback,
              },
            },
          })
        }
      />
    );
  }

  if (session.status === "abandoned") {
    return (
      <div className="mx-auto max-w-md space-y-4 py-16 text-center">
        <h1 className="font-display text-lg font-semibold text-text-primary">Interview ended</h1>
        <p className="text-sm text-text-secondary">
          You ended this interview before answering any questions, so there was nothing to evaluate.
        </p>
        <Button onClick={() => navigate("/interview")}>Back to Interview</Button>
      </div>
    );
  }

  return (
    <InterviewSessionView
      session={session}
      lastResult={lastResult}
      isSubmitting={isSubmitting}
      isCompleting={isCompleting}
      error={error}
      elapsedSeconds={elapsedSeconds}
      onSubmit={submitAnswer}
      onEnd={complete}
      onDismissError={clearError}
    />
  );
}
