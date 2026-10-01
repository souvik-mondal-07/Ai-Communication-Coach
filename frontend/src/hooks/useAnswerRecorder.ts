import { useCallback, useEffect, useRef, useState } from "react";
import {
  isVoiceSupported,
  micErrorMessage,
  pickMimeType,
  UNSUPPORTED_MESSAGE,
} from "@/hooks/useVoice";
import type { MicPermission } from "@/types/voiceConversation";

/**
 * Microphone recorder for voice conversations (MediaRecorder).
 *
 * Unlike `useVoice` (Step 8) it does not transcribe: the finished recording is
 * handed to `onRecorded` exactly once. The conversation store then transcribes
 * it and submits the transcript to the AI automatically (there is no Send step).
 *
 * - The microphone is requested only when the user presses the button, and
 *   released the moment recording ends.
 * - `stop()` finishes the answer and hands it over; `cancel()` throws it away.
 *   Only `stop()` (or hitting the time limit, which the UI announces) delivers audio.
 * - One recording is delivered at most once, even if `onstop` fires twice.
 * - A second recording cannot start while one is active or being requested.
 */

export type RecorderStatus = "idle" | "requesting" | "recording";

interface Options {
  maxSeconds: number;
  onRecorded: (audio: Blob, info: { durationSeconds: number }) => void;
}

export function useAnswerRecorder({ maxSeconds, onRecorded }: Options) {
  const [status, setStatus] = useState<RecorderStatus>("idle");
  const [permission, setPermission] = useState<MicPermission>(() =>
    isVoiceSupported() ? "unknown" : "unavailable"
  );
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const recorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const runIdRef = useRef(0);
  const busyRef = useRef(false);
  /** The run whose recording was already delivered; guards against a repeated `onstop`. */
  const deliveredRunRef = useRef(0);
  const onRecordedRef = useRef(onRecorded);
  useEffect(() => {
    onRecordedRef.current = onRecorded;
  }, [onRecorded]);

  const release = useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
  }, []);

  const stop = useCallback(() => {
    const recorder = recorderRef.current;
    if (recorder && recorder.state === "recording") recorder.stop();
  }, []);

  const cancel = useCallback(() => {
    runIdRef.current += 1; // the pending onstop (if any) now ignores its audio
    const recorder = recorderRef.current;
    if (recorder && recorder.state !== "inactive") {
      try {
        recorder.stop();
      } catch {
        /* already stopped */
      }
    }
    recorderRef.current = null;
    chunksRef.current = [];
    release();
    busyRef.current = false;
    setElapsedSeconds(0);
    setStatus("idle");
  }, [release]);

  const start = useCallback(async () => {
    if (busyRef.current) return; // one recording at a time
    if (!isVoiceSupported()) {
      setPermission("unavailable");
      setError(UNSUPPORTED_MESSAGE);
      return;
    }
    busyRef.current = true;
    setError(null);
    setElapsedSeconds(0);
    setStatus("requesting");
    const runId = ++runIdRef.current;

    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (err) {
      if (runId !== runIdRef.current) return;
      const { permission: next, message } = micErrorMessage(err);
      const name = err instanceof DOMException ? err.name : "";
      setPermission(
        next === "denied"
          ? "denied"
          : name === "NotFoundError" || name === "OverconstrainedError"
            ? "unavailable"
            : "unknown"
      );
      setError(message);
      busyRef.current = false;
      setStatus("idle");
      return;
    }

    if (runId !== runIdRef.current) {
      // Cancelled while the permission prompt was open.
      stream.getTracks().forEach((track) => track.stop());
      return;
    }

    setPermission("granted");
    streamRef.current = stream;
    chunksRef.current = [];

    let recorder: MediaRecorder;
    try {
      const mimeType = pickMimeType();
      recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
    } catch {
      release();
      busyRef.current = false;
      setError("Recording isn't supported with this microphone or browser.");
      setStatus("idle");
      return;
    }
    recorderRef.current = recorder;

    recorder.ondataavailable = (event: BlobEvent) => {
      if (event.data && event.data.size > 0) chunksRef.current.push(event.data);
    };
    recorder.onerror = () => {
      if (runId !== runIdRef.current) return;
      release();
      busyRef.current = false;
      setError("Recording failed. Please try again.");
      setStatus("idle");
    };

    const startedAt = Date.now();
    recorder.onstop = () => {
      release();
      busyRef.current = false;
      setStatus("idle");
      if (runId !== runIdRef.current) return; // cancelled: audio is discarded
      if (deliveredRunRef.current === runId) return; // already delivered: never hand the same recording over twice
      deliveredRunRef.current = runId;
      const blob = new Blob(chunksRef.current, { type: recorder.mimeType || "audio/webm" });
      chunksRef.current = [];
      recorderRef.current = null;
      if (blob.size === 0) {
        setError("Nothing was recorded. Please try again.");
        return;
      }
      onRecordedRef.current(blob, { durationSeconds: (Date.now() - startedAt) / 1000 });
    };

    recorder.start();
    setStatus("recording");
    timerRef.current = setInterval(() => {
      const seconds = Math.floor((Date.now() - startedAt) / 1000);
      setElapsedSeconds(seconds);
      if (seconds >= maxSeconds) stop(); // hard limit: the UI shows the maximum while recording
    }, 250);
  }, [maxSeconds, release, stop]);

  // Always release the microphone if the page goes away mid-recording.
  useEffect(() => {
    return () => {
      runIdRef.current += 1;
      const recorder = recorderRef.current;
      if (recorder && recorder.state !== "inactive") {
        try {
          recorder.stop();
        } catch {
          /* already stopped */
        }
      }
      if (timerRef.current) clearInterval(timerRef.current);
      streamRef.current?.getTracks().forEach((track) => track.stop());
    };
  }, []);

  return {
    status,
    permission,
    elapsedSeconds,
    error,
    clearError: () => setError(null),
    isSupported: permission !== "unavailable",
    start,
    stop,
    cancel,
  };
}
