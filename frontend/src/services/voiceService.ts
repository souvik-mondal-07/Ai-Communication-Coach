import axios from "axios";
import { api } from "@/services/api";
import type { TranscribeResult, VoiceCapabilities } from "@/features/voice/voiceTypes";

/**
 * Client for the voice endpoints. Talks only to FastAPI (`/api/v1/voice/...`):
 * transcription runs on the backend (local Whisper) and speech synthesis uses
 * a backend-configured provider. No AI or speech provider key ever reaches
 * the browser.
 */

interface ApiEnvelope<T> {
  success: boolean;
  message: string;
  data: T;
}

function extensionFor(mimeType: string): string {
  if (mimeType.includes("webm")) return "webm";
  if (mimeType.includes("mp4") || mimeType.includes("m4a")) return "m4a";
  if (mimeType.includes("ogg")) return "ogg";
  if (mimeType.includes("wav")) return "wav";
  return "webm";
}

export async function getVoiceCapabilities(): Promise<VoiceCapabilities> {
  const { data } = await api.get<ApiEnvelope<VoiceCapabilities>>("/voice/capabilities");
  return data.data;
}

/** Upload a recording and get back the transcript (the server deletes the audio). */
export async function transcribeAudio(audio: Blob): Promise<TranscribeResult> {
  const form = new FormData();
  // The server ignores the filename and identifies the audio from its bytes.
  form.append("audio", audio, `recording.${extensionFor(audio.type)}`);
  // The shared client defaults to `application/json`, which makes Axios
  // JSON-serialise a FormData body (dropping the file). Overriding the header
  // sends it as real multipart; the browser adds the boundary.
  const { data } = await api.post<ApiEnvelope<TranscribeResult>>("/voice/transcribe", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data.data;
}

/** Synthesize `text` to speech. Rejects if TTS is unavailable. */
export async function synthesizeSpeech(text: string): Promise<Blob> {
  try {
    const { data } = await api.post<Blob>(
      "/voice/synthesize",
      { text },
      { responseType: "blob" }
    );
    return data;
  } catch (err) {
    // Error bodies arrive as JSON inside a Blob; callers only need to know it failed.
    if (axios.isAxiosError(err)) throw new Error("Text-to-speech is unavailable.");
    throw err;
  }
}
