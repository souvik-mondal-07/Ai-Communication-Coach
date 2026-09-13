import { useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { CommunicationSession } from "@/features/communication/CommunicationSession";
import { useCommunicationStore } from "@/store/communicationStore";

export default function CommunicationSessionPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();
  const {
    session,
    isLoadingSession,
    isSendingMessage,
    isCompleting,
    error,
    loadSession,
    sendMessage,
    complete,
    clearError,
    reset,
  } = useCommunicationStore();

  useEffect(() => {
    if (sessionId) void loadSession(sessionId);
    return () => reset();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId]);

  if (isLoadingSession) {
    return <p className="py-16 text-center text-sm text-text-muted">Loading practice session…</p>;
  }

  if (!session) {
    return (
      <div className="mx-auto max-w-md py-16 text-center">
        <p className="text-sm text-danger">{error ?? "Session not found."}</p>
        <button
          type="button"
          onClick={() => navigate("/communication")}
          className="mt-4 text-sm text-link hover:underline"
        >
          Back to Communication Coach
        </button>
      </div>
    );
  }

  return (
    <CommunicationSession
      session={session}
      onSendMessage={sendMessage}
      onComplete={complete}
      isSendingMessage={isSendingMessage}
      isCompleting={isCompleting}
      error={error}
      onDismissError={clearError}
    />
  );
}
