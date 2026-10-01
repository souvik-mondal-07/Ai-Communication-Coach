import { AlertTriangle, CheckCircle2, Hourglass, Loader2, Mic, PauseCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import { formatDuration } from "@/features/voice/formatDuration";
import type { VoiceUiState } from "@/types/voiceConversation";

interface VoiceStatusBannerProps {
  state: VoiceUiState;
  elapsedSeconds?: number;
  maxSeconds?: number;
}

interface Copy {
  text: string;
  tone: string;
  /** Lucide icon, for states without an emoji. */
  icon?: typeof Mic;
  /** Decorative emoji shown before the text (hidden from screen readers; the text says it all). */
  emoji?: string;
}

// The five answer-cycle states each have their own wording, so transcribing is never
// mistaken for processing: listening → transcribing → processing → AI speaking → ready.
const COPY: Record<VoiceUiState, Copy> = {
  idle: { text: "Not started", icon: Hourglass, tone: "text-text-muted" },
  starting: { text: "Starting the conversation…", icon: Loader2, tone: "text-text-secondary" },
  listening: { text: "Listening...", emoji: "🎙", tone: "text-danger" },
  transcribing: { text: "Transcribing...", emoji: "📝", tone: "text-text-secondary" },
  processing: { text: "Processing your answer...", emoji: "⚙️", tone: "text-text-secondary" },
  ai_speaking: { text: "AI is speaking...", emoji: "🔊", tone: "text-link" },
  ready: { text: "Ready for your response", emoji: "🎙", tone: "text-signal" },
  paused: { text: "Paused", icon: PauseCircle, tone: "text-warn" },
  error: { text: "Something went wrong", icon: AlertTriangle, tone: "text-danger" },
  completed: { text: "Conversation completed", icon: CheckCircle2, tone: "text-signal" },
};

/**
 * The single, always-visible statement of what the conversation is doing.
 * The text carries the meaning (not colour or emoji). Transcribing and
 * processing are separate states: speech-to-text, then the AI reply.
 */
export function VoiceStatusBanner({ state, elapsedSeconds = 0, maxSeconds }: VoiceStatusBannerProps) {
  const { text, icon: Icon, emoji, tone } = COPY[state];
  const spinning = state === "starting";
  const working = state === "transcribing" || state === "processing";
  return (
    <div
      role="status"
      aria-live="polite"
      className="flex flex-wrap items-center justify-center gap-x-3 gap-y-1 rounded-[var(--radius-panel)] border border-border bg-surface px-4 py-2.5"
    >
      <span className={cn("flex items-center gap-2 text-sm font-medium", tone)}>
        {emoji ? (
          <span aria-hidden="true" className={cn(working && "animate-pulse motion-reduce:animate-none")}>
            {emoji}
          </span>
        ) : Icon ? (
          <Icon size={16} aria-hidden="true" className={cn(spinning && "animate-spin motion-reduce:animate-none")} />
        ) : null}
        {text}
      </span>
      {state === "listening" && (
        <span className="font-mono text-sm tabular-nums text-text-primary">
          {formatDuration(elapsedSeconds)}
          {maxSeconds ? <span className="text-xs text-text-muted"> / {formatDuration(maxSeconds)} max</span> : null}
        </span>
      )}
    </div>
  );
}
