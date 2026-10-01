import { useEffect, useRef } from "react";
import { cn } from "@/lib/utils";
import type { VoiceConversationTurn } from "@/types/voiceConversation";

/** An answer that isn't part of the saved conversation yet. */
export interface PendingAnswer {
  /** Waiting for speech-to-text, the AI reply, or the AI reply failed. */
  phase: "transcribing" | "processing" | "failed";
  /** What speech-to-text produced; null while still transcribing. */
  transcript: string | null;
}

interface ConversationTranscriptProps {
  messages: VoiceConversationTurn[];
  /** The answer in progress, shown after the saved messages. */
  pending?: PendingAnswer | null;
}

const PENDING_NOTE: Record<PendingAnswer["phase"], string> = {
  transcribing: "Transcribing...",
  processing: "Processing your answer...",
  failed: "The AI couldn't respond yet. Your answer is saved. Use Retry response.",
};

/** Live transcript: updates in place after each turn, no page reload. */
export function ConversationTranscript({ messages, pending = null }: ConversationTranscriptProps) {
  const endRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const reduce = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    endRef.current?.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "end" });
  }, [messages.length, pending?.phase, pending?.transcript]);

  if (messages.length === 0 && !pending) {
    return <p className="py-8 text-center text-sm text-text-muted">The conversation will appear here.</p>;
  }

  return (
    <ol className="space-y-3" aria-label="Conversation transcript">
      {messages.map((message, index) => {
        const isUser = message.role === "user";
        return (
          <li key={`${index}-${message.timestamp ?? ""}`} className={cn("flex", isUser ? "justify-end" : "justify-start")}>
            <div
              className={cn(
                "max-w-[92%] rounded-[var(--radius-panel)] border px-3.5 py-2.5 text-sm leading-relaxed sm:max-w-[80%]",
                isUser ? "border-signal/40 bg-signal/10 text-text-primary" : "border-border bg-surface-raised text-text-primary"
              )}
            >
              <p className="mb-1 text-[11px] font-medium uppercase tracking-wide text-text-muted">{isUser ? "You" : "AI mentor"}</p>
              <p className="whitespace-pre-wrap break-words">{message.text}</p>
              {isUser && message.voice_analysis?.speaking_rate_wpm != null && (
                <p className="mt-1.5 text-[11px] text-text-muted">
                  {message.voice_analysis.word_count} words · {Math.round(message.voice_analysis.speaking_rate_wpm)} wpm
                </p>
              )}
            </div>
          </li>
        );
      })}
      {pending && (
        <li className="flex justify-end" aria-live="polite">
          <div className="max-w-[92%] rounded-[var(--radius-panel)] border border-dashed border-signal/40 px-3.5 py-2.5 text-sm leading-relaxed text-text-primary sm:max-w-[80%]">
            <p className="mb-1 text-[11px] font-medium uppercase tracking-wide text-text-muted">You</p>
            {pending.transcript ? <p className="whitespace-pre-wrap break-words">{pending.transcript}</p> : null}
            <p className={cn("text-xs text-text-muted", pending.transcript && "mt-1.5")}>{PENDING_NOTE[pending.phase]}</p>
          </div>
        </li>
      )}
      <div ref={endRef} />
    </ol>
  );
}
