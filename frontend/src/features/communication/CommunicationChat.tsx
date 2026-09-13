import { type KeyboardEvent, useEffect, useRef, useState } from "react";
import { SendHorizontal, ShieldHalf } from "lucide-react";
import { MessageBubble } from "@/features/communication/MessageBubble";
import type { CommunicationMessage } from "@/features/communication/communicationTypes";

interface CommunicationChatProps {
  messages: CommunicationMessage[];
  aiLabel: string;
  onSend: (message: string) => Promise<void>;
  isSending: boolean;
  disabled?: boolean;
}

export function CommunicationChat({
  messages,
  aiLabel,
  onSend,
  isSending,
  disabled,
}: CommunicationChatProps) {
  const [value, setValue] = useState("");
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
          <MessageBubble key={idx} message={message} aiLabel={aiLabel} />
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
    </div>
  );
}
