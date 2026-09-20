import { type KeyboardEvent, useEffect, useRef, useState } from "react";
import { SendHorizontal, ShieldHalf } from "lucide-react";
import { MessageBubble } from "@/features/communication/MessageBubble";
import type { CommunicationMessage } from "@/features/communication/communicationTypes";
import { AudioPlayer } from "@/features/voice/AudioPlayer";
import { VoiceControls } from "@/features/voice/VoiceControls";
import type { InputMode, SendMessageOptions } from "@/features/voice/voiceTypes";
import { useVoiceCapabilities } from "@/hooks/useVoice";

interface CommunicationChatProps {
  messages: CommunicationMessage[];
  aiLabel: string;
  onSend: (message: string, options?: SendMessageOptions) => Promise<void>;
  isSending: boolean;
  disabled?: boolean;
  /** "text" is the Step 7 experience; "voice" swaps the input for the microphone flow. */
  inputMode?: InputMode;
}

export function CommunicationChat({
  messages,
  aiLabel,
  onSend,
  isSending,
  disabled,
  inputMode = "text",
}: CommunicationChatProps) {
  const [value, setValue] = useState("");
  const isVoice = inputMode === "voice";
  const capabilities = useVoiceCapabilities(isVoice);
  const ttsUnavailable = capabilities !== null && !capabilities.tts_available;
  const [autoPlayReplies, setAutoPlayReplies] = useState(false);
  // Index of the AI reply that should auto-play (set right after a voice send).
  const [autoPlayIndex, setAutoPlayIndex] = useState<number | null>(null);
  const scrollAnchorRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollAnchorRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length, isSending]);

  const isBusy = isSending || disabled;
  const canSubmit = value.trim().length > 0 && !isBusy;

  async function handleSubmit() {
    if (!canSubmit) return;
    const message = value;
    setValue("");
    try {
      await onSend(message);
    } catch {
      setValue(message);
    }
  }

  async function handleSendVoice(message: string, options: SendMessageOptions) {
    // A send appends the user's message then the AI reply.
    const replyIndex = messages.length + 1;
    await onSend(message, options);
    setAutoPlayIndex(replyIndex);
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void handleSubmit();
    }
  }

  return (
    <div className="flex h-full flex-col">
      <div className="mb-3 flex-1 space-y-4 overflow-y-auto">
        {messages.map((message, idx) => (
          <MessageBubble
            key={idx}
            message={message}
            aiLabel={aiLabel}
            footer={
              isVoice && message.role === "assistant" && !ttsUnavailable ? (
                <AudioPlayer text={message.content} autoPlay={autoPlayReplies && idx === autoPlayIndex} />
              ) : undefined
            }
          />
        ))}
        {isSending && (
          <div className="flex items-center gap-2.5">
            <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-[var(--radius-panel)] bg-signal/15 text-signal">
              <ShieldHalf size={14} />
            </div>
            <div className="rounded-[var(--radius-panel)] border border-border bg-surface px-3.5 py-2.5 text-sm text-text-muted">
              {aiLabel} is typing…
            </div>
          </div>
        )}
        <div ref={scrollAnchorRef} />
      </div>

      {isVoice ? (
        <div className="space-y-2 border-t border-border pt-3">
          {ttsUnavailable ? (
            <p className="text-xs text-text-muted">
              Audio unavailable — text response is still available.
            </p>
          ) : (
            <label className="flex items-center gap-2 text-xs text-text-secondary">
              <input
                type="checkbox"
                checked={autoPlayReplies}
                onChange={(e) => setAutoPlayReplies(e.target.checked)}
              />
              Auto-play AI replies
            </label>
          )}
          <VoiceControls onSendVoice={handleSendVoice} isSending={isSending} disabled={disabled} />
        </div>
      ) : (
      <div className="flex items-end gap-2 border-t border-border pt-3">
        <label htmlFor="communication-chat-input" className="sr-only">
          Your response
        </label>
        <textarea
          id="communication-chat-input"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isBusy}
          rows={2}
          placeholder={
            disabled
              ? "This session is complete."
              : "Type your response... (Enter to send, Shift+Enter for a new line)"
          }
          className="max-h-40 flex-1 resize-none rounded-[var(--radius-panel)] border border-border bg-surface-raised px-3 py-2 text-sm text-text-primary placeholder:text-text-muted disabled:cursor-not-allowed disabled:opacity-60"
        />
        <button
          type="button"
          onClick={() => void handleSubmit()}
          disabled={!canSubmit}
          aria-label="Send message"
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-[var(--radius-panel)] bg-signal text-[#08120f] transition-colors hover:bg-signal/90 disabled:cursor-not-allowed disabled:opacity-40"
        >
          <SendHorizontal size={16} />
        </button>
      </div>
      )}
    </div>
  );
}
