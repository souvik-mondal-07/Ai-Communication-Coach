import { useCallback, useEffect, useRef, useState } from "react";
import { getApiErrorMessage } from "@/utils/apiError";
import * as voiceService from "@/services/voiceService";
import type { TranscribeResult, VoiceCapabilities } from "@/features/voice/voiceTypes";

/**
 * Voice hooks (Step 8): microphone recording with MediaRecorder,
 * server-side transcription, and a lightweight capabilities lookup.
 *
 * Nothing is sent anywhere until the user stops recording, and the
 * transcript is only *returned* — the caller decides whether to send it.
 */

export type VoiceStatus = "idle" | "requesting" | "recording" | "transcribing" | "ready" | "error";
export type MicPermission = "unknown" | "granted" | "denied" | "unsupported";

export const DEFAULT_MAX_RECORDING_SECONDS = 180;

const MIME_CANDIDATES = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4", "audio/ogg;codecs=opus"];

export const MIC_DENIED_MESSAGE =
  "Microphone access is required for voice practice. Please allow microphone access in your browser settings.";
export const UNSUPPORTED_MESSAGE =
  "Voice recording isn't supported here. It needs a modern browser and a secure (https or localhost) connection. You can still practise in text mode.";

/** True when this browser can record audio (MediaRecorder + getUserMedia). */
export function isVoiceSupported(): boolean {
  return (
    typeof navigator !== "undefined" &&
    typeof navigator.mediaDevices?.getUserMedia === "function" &&
    typeof MediaRecorder !== "undefined"
  );
}

export function pickMimeType(): string | undefined {
  if (typeof MediaRecorder.isTypeSupported !== "function") return undefined;
  return MIME_CANDIDATES.find((type) => MediaRecorder.isTypeSupported(type));
}

export function micErrorMessage(err: unknown): { permission: MicPermission; message: string } {
  const name = err instanceof DOMException ? err.name : "";
  if (name === "NotAllowedError" || name === "SecurityError" || name === "PermissionDeniedError") {
    return { permission: "denied", message: MIC_DENIED_MESSAGE };
  }
  if (name === "NotFoundError" || name === "OverconstrainedError") {
    return { permission: "unknown", message: "No microphone was found. Please connect one and try again." };
  }
  if (name === "NotReadableError") {
    return {
      permission: "unknown",
      message: "Your microphone is in use by another application. Close it and try again.",
    };
  }
  return { permission: "unknown", message: "Could not start recording. Please try again." };
}

export function useVoice(options?: { maxSeconds?: number }) {
  const maxSeconds = options?.maxSeconds ?? DEFAULT_MAX_RECORDING_SECONDS;

  const [status, setStatus] = useState<VoiceStatus>("idle");
  const [permission, setPermission] = useState<MicPermission>(() =>
    isVoiceSupported() ? "unknown" : "unsupported"
  );
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [transcript, setTranscript] = useState<TranscribeResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const recorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  // Bumped whenever a recording is discarded, so a late transcription result
  // for a discarded recording is ignored.
  const runIdRef = useRef(0);

  const releaseMicrophone = useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
  }, []);

  const stopRecording = useCallback(() => {
    const recorder = recorderRef.current;
    if (recorder && recorder.state === "recording") recorder.stop();
  }, []);

  const startRecording = useCallback(async () => {
    if (!isVoiceSupported()) {
      setPermission("unsupported");
      setError(UNSUPPORTED_MESSAGE);
      setStatus("error");
      return;
    }

    setError(null);
    setTranscript(null);
    setElapsedSeconds(0);
    setStatus("requesting");
    const runId = ++runIdRef.current;

    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (err) {
      if (runId !== runIdRef.current) return;
      const { permission: nextPermission, message } = micErrorMessage(err);
      setPermission(nextPermission);
      setError(message);
      setStatus("error");
      return;
    }

    // Discarded while the permission prompt was open.
    if (runId !== runIdRef.current) {
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
      releaseMicrophone();
      setError("Recording isn't supported with this microphone or browser. Try text mode.");
      setStatus("error");
      return;
    }
    recorderRef.current = recorder;

    recorder.ondataavailable = (event: BlobEvent) => {
      if (event.data && event.data.size > 0) chunksRef.current.push(event.data);
    };

    recorder.onerror = () => {
      if (runId !== runIdRef.current) return;
      releaseMicrophone();
      setError("Recording failed. Please try again.");
      setStatus("error");
    };

    recorder.onstop = () => {
      releaseMicrophone();
      if (runId !== runIdRef.current) return; // discarded
      const blob = new Blob(chunksRef.current, { type: recorder.mimeType || "audio/webm" });
      chunksRef.current = [];
      if (blob.size === 0) {
        setError("Nothing was recorded. Please try again.");
        setStatus("error");
        return;
      }
      setStatus("transcribing");
      voiceService
        .transcribeAudio(blob)
        .then((result) => {
          if (runId !== runIdRef.current) return;
          setTranscript(result);
          setStatus("ready");
        })
        .catch((err) => {
          if (runId !== runIdRef.current) return;
          setError(
            getApiErrorMessage(err, "Couldn't transcribe your recording. Please try again or type instead.")
          );
          setStatus("error");
        });
    };

    const startedAt = Date.now();
    recorder.start();
    setStatus("recording");
    timerRef.current = setInterval(() => {
      const seconds = Math.floor((Date.now() - startedAt) / 1000);
      setElapsedSeconds(seconds);
      if (seconds >= maxSeconds) {
        stopRecording(); // auto-stop at the limit
      }
    }, 250);
  }, [maxSeconds, releaseMicrophone, stopRecording]);

  /** Throw away the recording / transcript and return to idle. */
  const discard = useCallback(() => {
    runIdRef.current += 1; // invalidates any in-flight recording or transcription
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
    releaseMicrophone();
    setTranscript(null);
    setError(null);
    setElapsedSeconds(0);
    setStatus("idle");
  }, [releaseMicrophone]);

  // Always release the microphone if the component goes away mid-recording.
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
    maxSeconds,
    transcript,
    error,
    isSupported: permission !== "unsupported",
    startRecording,
    stopRecording,
    discard,
  };
}

let cachedCapabilities: VoiceCapabilities | null = null;

/**
 * Server-side voice capabilities (is speech recognition / spoken-reply
 * synthesis configured, and the audio limits). `null` until loaded or if the
 * lookup fails — callers should then fall back to sensible defaults.
 */
export function useVoiceCapabilities(enabled: boolean): VoiceCapabilities | null {
  const [capabilities, setCapabilities] = useState<VoiceCapabilities | null>(cachedCapabilities);

  useEffect(() => {
    if (!enabled || cachedCapabilities) return;
    let cancelled = false;
    voiceService
      .getVoiceCapabilities()
      .then((result) => {
        cachedCapabilities = result;
        if (!cancelled) setCapabilities(result);
      })
      .catch(() => {
        /* keep defaults; individual actions report their own errors */
      });
    return () => {
      cancelled = true;
    };
  }, [enabled]);

  return capabilities;
}
