import { ShieldCheck } from "lucide-react";
import { TranscriptPreview } from "@/features/voice/TranscriptPreview";
import { VoiceRecorder } from "@/features/voice/VoiceRecorder";
import type { AudioMetadata, SendMessageOptions } from "@/features/voice/voiceTypes";
import { DEFAULT_MAX_RECORDING_SECONDS, useVoice, useVoiceCapabilities } from "@/hooks/useVoice";

interface VoiceControlsProps {
  onSendVoice: (message: string, options: SendMessageOptions) => Promise<void>;
  isSending: boolean;
  disabled?: boolean;
}

/**
 * The voice-mode input area: record -> transcript preview -> send.
 * The user always reviews the transcript (and may edit or discard it) before
 * anything is sent to the AI.
 */
export function VoiceControls({ onSendVoice, isSending, disabled }: VoiceControlsProps) {
  const capabilities = useVoiceCapabilities(true);
  const maxSeconds = Math.min(
    DEFAULT_MAX_RECORDING_SECONDS,
    capabilities?.max_audio_seconds ?? DEFAULT_MAX_RECORDING_SECONDS
  );
  const voice = useVoice({ maxSeconds });

  const sttUnavailable = capabilities !== null && !capabilities.stt_available;

  async function handleSend(text: string, edited: boolean) {
    if (!voice.transcript) return;
    const audioMetadata: AudioMetadata = {
      duration_seconds: voice.transcript.duration_seconds,
      language: voice.transcript.language,
      pause_metrics: voice.transcript.pause_metrics,
    };
    try {
      await onSendVoice(text, { inputType: "voice", audioMetadata, transcriptEdited: edited });
      voice.discard();
    } catch {
      // The store reports the error; keep the transcript so the user can retry.
    }
  }

  return (
    <div className="space-y-3">
      {sttUnavailable ? (
        <p className="rounded-[var(--radius-panel)] border border-warn/40 bg-warn/10 px-3 py-2 text-sm text-warn">
          Speech recognition isn't available on this server. Switch to Text mode to keep practising.
        </p>
      ) : voice.status === "ready" && voice.transcript ? (
        <TranscriptPreview
          transcript={voice.transcript}
          onSend={handleSend}
          onDiscard={voice.discard}
          isSending={isSending}
        />
      ) : (
        <VoiceRecorder
          status={voice.status}
          elapsedSeconds={voice.elapsedSeconds}
          maxSeconds={voice.maxSeconds}
          onStart={() => void voice.startRecording()}
          onStop={voice.stopRecording}
          disabled={disabled || isSending}
        />
      )}

      {voice.error && (
        <p
          role="alert"
          className="rounded-[var(--radius-panel)] border border-danger/40 bg-danger/10 px-3 py-2 text-sm text-danger"
        >
          {voice.error}
        </p>
      )}

      <p className="flex items-start gap-1.5 text-[11px] leading-snug text-text-muted">
        <ShieldCheck size={12} className="mt-px shrink-0" />
        <span>
          Privacy: your recording is transcribed on the server and deleted straight away — only the
          transcript and speaking metrics are saved. Only the transcript text goes to the AI. If spoken
          replies are enabled, the AI's reply text is sent to the configured speech provider.
        </span>
      </p>
    </div>
  );
}
