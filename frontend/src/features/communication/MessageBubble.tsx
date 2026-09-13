import { ShieldHalf, UserRound } from "lucide-react";
import { cn } from "@/lib/utils";
import type { CommunicationMessage } from "@/features/communication/communicationTypes";

interface MessageBubbleProps {
  message: CommunicationMessage;
  aiLabel: string;
}

export function MessageBubble({ message, aiLabel }: MessageBubbleProps) {
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
      <div
        className={cn(
          "max-w-[80%] whitespace-pre-wrap rounded-[var(--radius-panel)] px-3.5 py-2.5 text-sm leading-relaxed",
          isUser
            ? "bg-signal/10 text-text-primary"
            : "border border-border bg-surface text-text-primary"
        )}
      >
        {message.content}
      </div>
    </div>
  );
}
