import { useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { CtfWorkspace } from "@/features/cybersecurity/ctf/CtfWorkspace";
import { useCtfStore } from "@/store/ctfStore";

export default function CtfSession() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();
  const {
    session,
    isLoadingSession,
    isSendingMessage,
    isRequestingHint,
    isCompleting,
    error,
    loadSession,
    sendMessage,
    requestHint,
    complete,
    clearError,
    reset,
  } = useCtfStore();

  useEffect(() => {
    if (sessionId) void loadSession(sessionId);
    return () => reset();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId]);

  if (isLoadingSession) {
    return <p className="py-16 text-center text-sm text-text-muted">Loading challenge session…</p>;
  }

  if (!session) {
    return (
      <div className="mx-auto max-w-md py-16 text-center">
        <p className="text-sm text-danger">{error ?? "Session not found."}</p>
        <button
          type="button"
          onClick={() => navigate("/ctf")}
          className="mt-4 text-sm text-link hover:underline"
        >
          Back to CTF &amp; Lab Mentor
        </button>
      </div>
    );
  }

  return (
    <CtfWorkspace
      session={session}
      onSendMessage={sendMessage}
      onRequestHint={(level) => void requestHint(level)}
      onComplete={complete}
      isSendingMessage={isSendingMessage}
      isRequestingHint={isRequestingHint}
      isCompleting={isCompleting}
      error={error}
      onDismissError={clearError}
    />
  );
}
