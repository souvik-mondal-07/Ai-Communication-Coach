import { AlertTriangle, CheckCircle2, Cog, FileText, Hourglass, Loader2, Mic, PauseCircle, Volume2 } from "lucide-react";
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
  /** Lucide icon shown before the text (decorative: the text says it all). */
  icon: typeof Mic;
  /** Extra motion class, only applied while that state is active. */
  motion?: string;
}

// The five answer-cycle states each have their own wording, so transcribing is never
// mistaken for processing: listening → transcribing → processing → AI speaking → ready.
const COPY: Record<VoiceUiState, Copy> = {
  idle: { text: "Not started", icon: Hourglass, tone: "text-text-muted" },
  starting: { text: "Starting the conversation…", icon: Loader2, tone: "text-text-secondary" },
  listening: { text: "Listening...", icon: Mic, tone: "text-danger", motion: "animate-pulse" },
  transcribing: { text: "Transcribing...", icon: FileText, tone: "text-text-secondary", motion: "animate-pulse" },
  processing: { text: "Processing your answer...", icon: Cog, tone: "text-text-secondary", motion: "animate-spin" },
  ai_speaking: { text: "AI is speaking...", icon: Volume2, tone: "text-link", motion: "animate-pulse" },
  ready: { text: "Ready for your response", icon: Mic, tone: "text-success" },
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
  const { text, icon: Icon, tone, motion } = COPY[state];
  const spinning = state === "starting";
  return (
    <div
      role="status"
      aria-live="polite"
      className={cn("flex flex-wrap items-center justify-center gap-x-3 gap-y-1 rounded-[var(--radius-panel)] border px-4 py-2.5 transition-colors duration-300", state === "error" ? "border-danger/50 bg-danger/10" : state === "listening" ? "border-danger/40 bg-surface" : "border-border bg-surface")}
    >
      <span className={cn("flex items-center gap-2 text-sm font-medium", tone)}>
        <Icon size={16} aria-hidden="true" className={cn(spinning && "animate-spin", motion, "motion-reduce:animate-none")} />
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
