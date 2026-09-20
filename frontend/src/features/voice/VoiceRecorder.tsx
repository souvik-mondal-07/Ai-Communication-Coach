import { Button } from "@/components/ui/button";
import { RecordingIndicator } from "@/features/voice/RecordingIndicator";
import type { VoiceStatus } from "@/hooks/useVoice";

interface VoiceRecorderProps {
  status: VoiceStatus;
  elapsedSeconds: number;
  maxSeconds: number;
  onStart: () => void;
  onStop: () => void;
  disabled?: boolean;
}

/** Start/stop control plus the live recording indicator. Purely presentational. */
export function VoiceRecorder({
  status,
  elapsedSeconds,
  maxSeconds,
  onStart,
  onStop,
  disabled,
}: VoiceRecorderProps) {
  if (status === "recording") {
    return (
      <div className="flex flex-wrap items-center justify-between gap-3">
        <RecordingIndicator elapsedSeconds={elapsedSeconds} maxSeconds={maxSeconds} />
        <Button variant="danger" onClick={onStop}>
          Stop Recording
        </Button>
      </div>
    );
  }

  if (status === "transcribing") {
    return (
      <p className="py-1.5 text-sm text-text-secondary" role="status" aria-live="polite">
        Transcribing...
      </p>
    );
  }

  return (
    <Button onClick={onStart} disabled={disabled || status === "requesting"}>
      {status === "requesting" ? "Waiting for microphone..." : "🎙 Start Recording"}
    </Button>
  );
}
