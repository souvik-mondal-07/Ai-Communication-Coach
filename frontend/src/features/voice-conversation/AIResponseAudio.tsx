import { Loader2, Play, RotateCcw, Square } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { AiAudioState } from "@/hooks/useAiAudio";

interface AIResponseAudioProps {
  state: AiAudioState;
  onPlay: () => void;
  onStop: () => void;
  /** Server could not produce speech for this reply. */
  notice: string | null;
}

/** Play / stop / replay controls for the AI's latest spoken reply. */
export function AIResponseAudio({ state, onPlay, onStop, notice }: AIResponseAudioProps) {
  if (notice) {
    return (
      <p role="status" className="text-xs text-text-muted">
        {notice}
      </p>
    );
  }
  if (state === "none") return null;
  if (state === "loading") {
    return (
      <p role="status" className="flex items-center gap-2 text-xs text-text-muted">
        <Loader2 size={14} className="animate-spin motion-reduce:animate-none" aria-hidden="true" />
        Preparing audio…
      </p>
    );
  }
  if (state === "failed") {
    return (
      <p role="status" className="text-xs text-text-muted">
        The audio couldn't be played. You can read the reply below.
      </p>
    );
  }
  if (state === "playing") {
    return (
      <Button variant="secondary" size="sm" onClick={onStop} aria-label="Stop the AI's spoken reply">
        <Square size={13} fill="currentColor" aria-hidden="true" /> Stop audio
      </Button>
    );
  }
  return (
    <div className="flex flex-wrap items-center gap-2">
      <Button
        variant={state === "blocked" ? "primary" : "secondary"}
        size="sm"
        onClick={onPlay}
        aria-label={state === "ready" ? "Replay the AI's spoken reply" : "Play the AI's spoken reply"}
      >
        {state === "ready" ? <RotateCcw size={13} aria-hidden="true" /> : <Play size={13} aria-hidden="true" />}
        {state === "ready" ? "Replay" : "Play"}
      </Button>
      {state === "blocked" && (
        <span className="text-xs text-text-muted">Your browser blocked autoplay. Press Play to hear the reply.</span>
      )}
    </div>
  );
}
