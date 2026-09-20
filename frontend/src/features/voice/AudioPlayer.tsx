import { useCallback, useEffect, useRef, useState } from "react";
import { Loader2, Pause, Play, RotateCcw } from "lucide-react";
import * as voiceService from "@/services/voiceService";

interface AudioPlayerProps {
  /** The AI reply to speak. */
  text: string;
  /** Start playing as soon as this mounts (used for the newest AI reply). */
  autoPlay?: boolean;
}

type PlayerState = "idle" | "loading" | "playing" | "paused" | "error";

// Only one AI voice plays at a time.
let activeAudio: HTMLAudioElement | null = null;

/**
 * Play / pause / replay for one AI reply. Audio is fetched from the backend
 * only when first played, kept in memory for replay, and never persisted.
 * If speech synthesis is unavailable the text reply is unaffected.
 */
export function AudioPlayer({ text, autoPlay }: AudioPlayerProps) {
  const [state, setState] = useState<PlayerState>("idle");
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const urlRef = useRef<string | null>(null);
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      audioRef.current?.pause();
      if (activeAudio === audioRef.current) activeAudio = null;
      if (urlRef.current) URL.revokeObjectURL(urlRef.current);
    };
  }, []);

  const play = useCallback(async () => {
    try {
      if (!audioRef.current) {
        setState("loading");
        const blob = await voiceService.synthesizeSpeech(text);
        if (!mountedRef.current) return;
        const url = URL.createObjectURL(blob);
        urlRef.current = url;
        const audio = new Audio(url);
        audio.onended = () => mountedRef.current && setState("idle");
        audio.onpause = () => {
          if (mountedRef.current && !audio.ended) setState((s) => (s === "playing" ? "paused" : s));
        };
        audio.onerror = () => mountedRef.current && setState("error");
        audioRef.current = audio;
      }

      const audio = audioRef.current;
      if (activeAudio && activeAudio !== audio) activeAudio.pause();
      activeAudio = audio;
      if (audio.ended) audio.currentTime = 0;
      await audio.play();
      if (mountedRef.current) setState("playing");
    } catch (err) {
      if (!mountedRef.current) return;
      // Browsers may block autoplay until the user interacts — not an error.
      if (err instanceof DOMException && err.name === "NotAllowedError") {
        setState("paused");
        return;
      }
      setState("error");
    }
  }, [text]);

  // Deferred so no state is set synchronously inside the effect body.
  useEffect(() => {
    if (!autoPlay) return;
    const timer = setTimeout(() => void play(), 0);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoPlay]);

  function handlePause() {
    audioRef.current?.pause();
  }

  function handleReplay() {
    if (audioRef.current) audioRef.current.currentTime = 0;
    void play();
  }

  if (state === "error") {
    return (
      <p className="text-xs text-text-muted" role="status">
        Audio unavailable — text response is still available.
      </p>
    );
  }

  const buttonClass =
    "inline-flex items-center gap-1.5 rounded-[var(--radius-panel)] border border-border px-2 py-1 text-xs text-text-secondary transition-colors hover:border-border-strong hover:text-text-primary disabled:opacity-60";

  return (
    <div className="flex items-center gap-1.5">
      {state === "loading" ? (
        <button type="button" disabled className={buttonClass}>
          <Loader2 size={12} className="animate-spin" /> Loading audio…
        </button>
      ) : state === "playing" ? (
        <button type="button" onClick={handlePause} className={buttonClass}>
          <Pause size={12} /> Pause
        </button>
      ) : (
        <button type="button" onClick={() => void play()} className={buttonClass}>
          <Play size={12} /> {state === "paused" ? "Resume" : "▶ Play AI Response"}
        </button>
      )}
      {(state === "playing" || state === "paused") && (
        <button type="button" onClick={handleReplay} className={buttonClass} aria-label="Replay">
          <RotateCcw size={12} /> Replay
        </button>
      )}
    </div>
  );
}
