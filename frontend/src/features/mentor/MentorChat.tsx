import { useEffect, useRef } from "react";
import { ShieldHalf } from "lucide-react";
import { ChatInput } from "@/features/mentor/ChatInput";
import { LevelSelector } from "@/features/mentor/LevelSelector";
import { MessageBubble } from "@/features/mentor/MessageBubble";
import { MENTOR_EXAMPLE_PROMPTS } from "@/features/mentor/mentorTypes";
import { ModeSelector } from "@/features/mentor/ModeSelector";
import { useChat } from "@/hooks/useChat";

export function MentorChat() {
  const {
    messages,
    isLoading,
    error,
    mode,
    level,
    setMode,
    setLevel,
    sendMessage,
    clearError,
  } = useChat();

  const scrollAnchorRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollAnchorRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length, isLoading]);

  async function handleSend(message: string) {
    await sendMessage(message);
  }

  function handleExampleClick(prompt: string) {
    void sendMessage(prompt);
  }

  return (
    <div className="flex h-[calc(100vh-8.5rem)] flex-col overflow-hidden rounded-[var(--radius-panel)] border border-border bg-surface md:h-[calc(100vh-7.5rem)]">
      {/* Header */}
      <div className="border-b border-border px-4 py-3.5 md:px-6">
        <h2 className="font-display text-base font-semibold text-text-primary">
          AI Cybersecurity Mentor
        </h2>
        <p className="text-xs text-text-muted">Learn • Practice • Troubleshoot</p>
      </div>

      {/* Messages */}
      <div className="flex-1 space-y-4 overflow-y-auto px-4 py-5 md:px-6">
        {messages.length === 0 ? (
          <EmptyState onExampleClick={handleExampleClick} disabled={isLoading} />
        ) : (
          messages.map((message) => <MessageBubble key={message.id} message={message} />)
        )}

        {isLoading && <TypingIndicator />}

        <div ref={scrollAnchorRef} />
      </div>

      {/* Error banner */}
      {error && (
        <div className="mx-4 mb-3 flex items-center justify-between gap-3 rounded-[var(--radius-panel)] border border-danger/40 bg-danger/10 px-3 py-2 text-sm text-danger md:mx-6">
          <span>{error}</span>
          <button
            type="button"
            onClick={clearError}
            className="shrink-0 text-xs underline hover:no-underline"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Controls */}
      <div className="flex flex-wrap items-center gap-3 border-t border-border px-4 py-2.5 md:px-6">
        <ModeSelector value={mode} onChange={setMode} disabled={isLoading} />
        <LevelSelector value={level} onChange={setLevel} disabled={isLoading} />
      </div>

      {/* Input */}
      <ChatInput onSubmit={handleSend} disabled={isLoading} />
    </div>
  );
}

function TypingIndicator() {
  return (
    <div className="flex items-center gap-3">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-[var(--radius-panel)] bg-signal/15 text-signal">
        <ShieldHalf size={16} />
      </div>
      <div className="flex items-center gap-1.5 rounded-[var(--radius-panel)] border border-border bg-surface px-3.5 py-2.5">
        <span className="text-sm text-text-muted">Mentor is thinking</span>
        <span className="flex gap-0.5">
          <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-text-muted [animation-delay:-0.3s]" />
          <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-text-muted [animation-delay:-0.15s]" />
          <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-text-muted" />
        </span>
      </div>
    </div>
  );
}

function EmptyState({
  onExampleClick,
  disabled,
}: {
  onExampleClick: (prompt: string) => void;
  disabled: boolean;
}) {
  return (
    <div className="flex h-full flex-col items-center justify-center py-8 text-center">
      <div className="mb-3 flex h-11 w-11 items-center justify-center rounded-[var(--radius-panel)] bg-signal/10 text-signal">
        <ShieldHalf size={22} />
      </div>
      <h3 className="text-sm font-semibold text-text-primary">
        Ask your mentor anything cybersecurity
      </h3>
      <p className="mt-1 max-w-sm text-xs text-text-secondary">
        Try one of these, or type your own question below.
      </p>
      <div className="mt-4 flex w-full max-w-md flex-col gap-2">
        {MENTOR_EXAMPLE_PROMPTS.map((prompt) => (
          <button
            key={prompt}
            type="button"
            disabled={disabled}
            onClick={() => onExampleClick(prompt)}
            className="rounded-[var(--radius-panel)] border border-border bg-surface-raised px-3 py-2 text-left text-sm text-text-secondary transition-colors hover:border-border-strong hover:text-text-primary disabled:cursor-not-allowed disabled:opacity-50"
          >
            {prompt}
          </button>
        ))}
      </div>
    </div>
  );
}
