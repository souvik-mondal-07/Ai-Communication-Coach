import { useEffect } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { VoiceConversationPage } from "@/features/voice-conversation/VoiceConversationPage";
import { useVoiceConversationStore } from "@/store/voiceConversationStore";

/**
 * `/voice-conversation/:sessionId`. The id lives in the URL, so a page refresh
 * reloads the same session (never silently creating a new one); an active
 * session can be continued or ended explicitly.
 */
export default function VoiceConversationSessionPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();
  const load = useVoiceConversationStore((s) => s.load);
  const loadConfig = useVoiceConversationStore((s) => s.loadConfig);
  const session = useVoiceConversationStore((s) => s.session);
  const busy = useVoiceConversationStore((s) => s.busy);
  const error = useVoiceConversationStore((s) => s.error);
  const reset = useVoiceConversationStore((s) => s.reset);

  useEffect(() => {
    void loadConfig();
  }, [loadConfig]);

  useEffect(() => {
    if (!sessionId) return;
    // Already in memory (just created here): no refetch, which would reset the audio state.
    if (useVoiceConversationStore.getState().session?.session_id !== sessionId) void load(sessionId);
  }, [sessionId, load]);

  const matches = session?.session_id === sessionId;

  if (!matches) {
    if (busy === "loading" || (!error && sessionId)) {
      return <p className="py-10 text-center text-sm text-text-muted">Loading conversation…</p>;
    }
    return (
      <div className="mx-auto max-w-md space-y-3 py-10 text-center">
        <p role="alert" className="text-sm text-danger">
          {error ?? "This conversation could not be found."}
        </p>
        <Link to="/voice-conversation" className="text-sm text-link underline">
          Back to Voice Conversation
        </Link>
      </div>
    );
  }

  return (
    <VoiceConversationPage
      onNewConversation={() => {
        reset();
        navigate("/voice-conversation");
      }}
    />
  );
}
