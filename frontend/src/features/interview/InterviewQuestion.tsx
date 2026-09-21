import { useState } from "react";
import { AudioPlayer } from "@/features/voice/AudioPlayer";
import type { InputMode } from "@/features/voice/voiceTypes";
import { useVoiceCapabilities } from "@/hooks/useVoice";
import type { CurrentPrompt } from "@/types/interview";

interface InterviewQuestionProps {
  prompt: CurrentPrompt;
  inputMode: InputMode;
}

/** The single question currently being asked. In voice mode the interviewer can read it aloud (Step 8 TTS). */
export function InterviewQuestion({ prompt, inputMode }: InterviewQuestionProps) {
  const isVoice = inputMode === "voice";
  const capabilities = useVoiceCapabilities(isVoice);
  const ttsUnavailable = capabilities !== null && !capabilities.tts_available;
  const [autoPlay, setAutoPlay] = useState(false);

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2 text-xs text-text-muted">
        <span>{prompt.topic_label}</span>
        {prompt.is_follow_up && (
          <span className="rounded-full border border-signal/40 bg-signal/10 px-2 py-0.5 text-signal">
            Follow-up
          </span>
        )}
      </div>
      <p className="font-display text-lg leading-snug text-text-primary" data-testid="interview-question">
        “{prompt.question}”
      </p>

      {isVoice && (
        <div className="flex flex-wrap items-center gap-3">
          {ttsUnavailable ? (
            <p className="text-xs text-text-muted">Audio unavailable — text response is still available.</p>
          ) : (
            <>
              {/* Keyed by the question so each new question gets a fresh player. */}
              <AudioPlayer key={prompt.question} text={prompt.question} autoPlay={autoPlay} />
              <label className="flex items-center gap-1.5 text-xs text-text-secondary">
                <input type="checkbox" checked={autoPlay} onChange={(e) => setAutoPlay(e.target.checked)} />
                Read questions aloud automatically
              </label>
            </>
          )}
        </div>
      )}
    </div>
  );
}
