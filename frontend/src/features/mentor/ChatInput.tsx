import { type KeyboardEvent, useRef, useState } from "react";
import { SendHorizontal } from "lucide-react";

interface ChatInputProps {
  onSubmit: (message: string) => Promise<void>;
  disabled?: boolean;
}

export function ChatInput({ onSubmit, disabled }: ChatInputProps) {
  const [value, setValue] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const isBusy = disabled || isSubmitting;
  const canSubmit = value.trim().length > 0 && !isBusy;

  function autoGrow() {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
  }

  async function handleSubmit() {
    if (!canSubmit) return;
    const message = value;
    setIsSubmitting(true);
    try {
      await onSubmit(message);
      // Only clear on success — failed sends preserve the typed text.
      setValue("");
      requestAnimationFrame(autoGrow);
    } catch {
      // Text is preserved; the parent surfaces the error banner.
    } finally {
      setIsSubmitting(false);
    }
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void handleSubmit();
    }
  }

  return (
    <div className="flex items-end gap-2 border-t border-border bg-surface px-3 py-3 md:px-4">
      <label htmlFor="mentor-chat-input" className="sr-only">
        Ask your cybersecurity question
      </label>
      <textarea
        id="mentor-chat-input"
        ref={textareaRef}
        value={value}
        onChange={(e) => {
          setValue(e.target.value);
          autoGrow();
        }}
        onKeyDown={handleKeyDown}
        disabled={isBusy}
        rows={1}
        placeholder="Ask your cybersecurity question... (Enter to send, Shift+Enter for a new line)"
        className="max-h-[200px] flex-1 resize-none rounded-[var(--radius-panel)] border border-border bg-surface-raised px-3 py-2 text-sm text-text-primary placeholder:text-text-muted disabled:cursor-not-allowed disabled:opacity-60"
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
  );
}
