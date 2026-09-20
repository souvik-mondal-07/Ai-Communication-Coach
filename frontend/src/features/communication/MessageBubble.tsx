import type { ReactNode } from "react";
import { Mic, ShieldHalf, UserRound } from "lucide-react";
import { cn } from "@/lib/utils";
import type { CommunicationMessage } from "@/features/communication/communicationTypes";

interface MessageBubbleProps {
  message: CommunicationMessage;
  aiLabel: string;
  /** Extra content under the bubble (e.g. an audio player for AI replies). */
  footer?: ReactNode;
}

export function MessageBubble({ message, aiLabel, footer }: MessageBubbleProps) {
  const analysis = message.input_type === "voice" ? message.voice_analysis : null;
  const isUser = message.role === "user";
  return (
    <div className={cn("flex gap-2.5", isUser && "flex-row-reverse")}>
      <div
        className={cn(
          "flex h-7 w-7 shrink-0 items-center justify-center rounded-[var(--radius-panel)]",
          isUser ? "bg-surface-raised text-text-secondary" : "bg-signal/15 text-signal"
        )}
        title={isUser ? "You" : aiLabel}
      >
        {isUser ? <UserRound size={14} /> : <ShieldHalf size={14} />}
      </div>
      <div className={cn("flex max-w-[80%] flex-col gap-1", isUser && "items-end")}>
        <div
          className={cn(
            "whitespace-pre-wrap rounded-[var(--radius-panel)] px-3.5 py-2.5 text-sm leading-relaxed",
            isUser
              ? "bg-signal/10 text-text-primary"
              : "border border-border bg-surface text-text-primary"
          )}
        >
          {message.content}
        </div>
        {isUser && message.input_type === "voice" && (
          <p className="flex flex-wrap items-center gap-x-2 text-[11px] text-text-muted">
            <span className="inline-flex items-center gap-1">
              <Mic size={11} /> Voice
            </span>
            {analysis && (
              <>
                <span>{analysis.word_count} words</span>
                {analysis.speaking_rate_wpm !== null && <span>{analysis.speaking_rate_wpm} WPM</span>}
                {analysis.total_filler_words > 0 && <span>{analysis.total_filler_words} filler</span>}
              </>
            )}
          </p>
        )}
        {footer}
      </div>
    </div>
  );
}
