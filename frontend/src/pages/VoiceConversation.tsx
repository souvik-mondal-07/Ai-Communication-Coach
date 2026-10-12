import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Card, CardContent, CardTitle } from "@/components/ui/card";
import { ConversationHistory } from "@/features/voice-conversation/ConversationHistory";
import { ConversationSetup } from "@/features/voice-conversation/ConversationSetup";
import { useVoiceConversationStore } from "@/store/voiceConversationStore";
import { getApiErrorMessage } from "@/utils/apiError";
import type { CreateVoiceConversationInput } from "@/types/voiceConversation";
import { PageHeader } from "@/components/ui/page-header";

/** Landing page: choose a conversation type, or resume a recent one. */
export default function VoiceConversation() {
  const navigate = useNavigate();
  const create = useVoiceConversationStore((s) => s.create);
  const reset = useVoiceConversationStore((s) => s.reset);
  const loadConfig = useVoiceConversationStore((s) => s.loadConfig);
  const config = useVoiceConversationStore((s) => s.config);
  const [isStarting, setIsStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    reset();
    void loadConfig();
  }, [reset, loadConfig]);

  const handleStart = async (input: CreateVoiceConversationInput) => {
    setIsStarting(true);
    setError(null);
    try {
      const sessionId = await create(input);
      navigate(`/voice-conversation/${sessionId}`);
    } catch (err) {
      setError(getApiErrorMessage(err, "Could not create the conversation. Please try again."));
      setIsStarting(false);
    }
  };

  return (
    <div className="mx-auto w-full max-w-3xl space-y-6">
      <PageHeader title="Voice Conversation" description="Talk with your AI mentor. It speaks, you answer out loud, and it responds. Turn by turn." />

      {config && !config.stt_available && (
        <p role="alert" className="rounded-[var(--radius-panel)] border border-warn/40 bg-warn/10 px-3 py-2 text-sm text-warn">
          Speech recognition isn't available on the server right now, so spoken answers can't be transcribed.
        </p>
      )}
      {config && config.stt_available && !config.tts_available && (
        <p className="rounded-[var(--radius-panel)] border border-border bg-surface px-3 py-2 text-sm text-text-secondary">
          Spoken replies aren't configured, so the mentor's replies will appear as text. You can still answer by voice.
        </p>
      )}

      <ConversationSetup onStart={handleStart} isStarting={isStarting} error={error} />

      <Card>
        <CardContent className="space-y-3 py-5">
          <CardTitle>Recent conversations</CardTitle>
          <ConversationHistory />
        </CardContent>
      </Card>
    </div>
  );
}
