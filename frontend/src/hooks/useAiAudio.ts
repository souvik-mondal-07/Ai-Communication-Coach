import { useCallback, useEffect, useRef, useState } from "react";
import { fetchAudio } from "@/services/voiceConversationService";

/**
 * Plays the AI's spoken reply.
 *
 * The server issues a short-lived, per-user audio URL. This hook fetches it
 * once through the authenticated client, keeps the blob in memory so the reply
 * can be replayed after the server copy has expired, and plays it.
 *
 * `blocked` means the browser refused autoplay (no user gesture yet): the UI
 * shows a Play button rather than retrying on its own. Audio is never replayed
 * automatically.
 */

export type AiAudioState =
  | "none" // no audio for the latest reply (TTS off/failed)
  | "loading"
  | "playing"
  | "paused"
  | "blocked"
  | "ready" // loaded, finished or stopped; can be replayed
  | "failed";

interface Options {
  autoPlay: boolean;
  /** Called when playback ends naturally or the user stops it (not on errors). */
  onFinished?: () => void;
}

export function useAiAudio({ autoPlay, onFinished }: Options) {
  const [state, setState] = useState<AiAudioState>("none");
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const objectUrlRef = useRef<string | null>(null);
  const loadIdRef = useRef(0);
  const onFinishedRef = useRef(onFinished);
  useEffect(() => {
    onFinishedRef.current = onFinished;
  }, [onFinished]);

  const teardown = useCallback(() => {
    const audio = audioRef.current;
    if (audio) {
      audio.onended = null;
      audio.onpause = null;
      audio.onerror = null;
      audio.pause();
    }
    audioRef.current = null;
    if (objectUrlRef.current) {
      URL.revokeObjectURL(objectUrlRef.current);
      objectUrlRef.current = null;
    }
  }, []);

  const attemptPlay = useCallback(async (audio: HTMLAudioElement, loadId: number) => {
    try {
      await audio.play();
      if (loadId === loadIdRef.current) setState("playing");
    } catch (err) {
      if (loadId !== loadIdRef.current) return;
      setState(err instanceof DOMException && err.name === "NotAllowedError" ? "blocked" : "failed");
    }
  }, []);

  /** Replace whatever is loaded with the audio at `audioUrl` (or clear it when null). */
  const load = useCallback(
    async (audioUrl: string | null) => {
      const loadId = ++loadIdRef.current;
      teardown();
      if (!audioUrl) {
        setState("none");
        return;
      }
      setState("loading");
      try {
        const blob = await fetchAudio(audioUrl);
        if (loadId !== loadIdRef.current) return;
        const objectUrl = URL.createObjectURL(blob);
        objectUrlRef.current = objectUrl;
        const audio = new Audio(objectUrl);
        audio.onended = () => {
          if (loadId !== loadIdRef.current) return;
          setState("ready");
          onFinishedRef.current?.();
        };
        audio.onpause = () => {
          if (loadId === loadIdRef.current && !audio.ended) {
            setState((s) => (s === "playing" ? "paused" : s));
          }
        };
        audio.onerror = () => {
          if (loadId === loadIdRef.current) setState("failed");
        };
        audioRef.current = audio;
        if (autoPlay) await attemptPlay(audio, loadId);
        else setState("ready");
      } catch {
        if (loadId === loadIdRef.current) setState("failed");
      }
    },
    [attemptPlay, autoPlay, teardown]
  );

  /** Play, resume, or replay from the start when finished. */
  const play = useCallback(async () => {
    const audio = audioRef.current;
    if (!audio) return;
    if (audio.ended) audio.currentTime = 0;
    await attemptPlay(audio, loadIdRef.current);
  }, [attemptPlay]);

  const pause = useCallback(() => audioRef.current?.pause(), []);

  /** Stop speaking now. The conversation stays valid; the reply can still be replayed. */
  const stop = useCallback(() => {
    const audio = audioRef.current;
    if (!audio) return;
    const wasActive = !audio.paused;
    audio.pause();
    audio.currentTime = 0;
    setState("ready");
    if (wasActive) onFinishedRef.current?.();
  }, []);

  useEffect(() => {
    return () => {
      loadIdRef.current += 1;
      teardown();
    };
  }, [teardown]);

  return { state, load, play, pause, stop };
}
