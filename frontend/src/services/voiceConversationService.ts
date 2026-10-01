import { api } from "@/services/api";
import type {
  CreateVoiceConversationInput,
  VoiceConversationConfig,
  VoiceConversationResponse,
  VoiceConversationSession,
  VoiceConversationSessionRow,
  VoiceConversationStartResponse,
  VoiceConversationSummary,
  TranscriptionMeta,
  TranscriptionResult,
} from "@/types/voiceConversation";

/**
 * Client for `/api/v1/voice-conversation`. Uses the shared Axios instance
 * (auth header, base URL, 401 handling). AI, speech-to-text and text-to-speech
 * all run on the backend; no provider key is ever present in the browser.
 */

interface ApiEnvelope<T> {
  success: boolean;
  message: string;
  data: T;
}

const BASE = "/voice-conversation";
/** Whisper, and Gemini + TTS, each run in their own request; allow well beyond the default. */
const TURN_TIMEOUT_MS = 120_000;

function extensionFor(mimeType: string): string {
  if (mimeType.includes("webm")) return "webm";
  if (mimeType.includes("mp4") || mimeType.includes("m4a")) return "m4a";
  if (mimeType.includes("ogg")) return "ogg";
  if (mimeType.includes("wav")) return "wav";
  return "webm";
}

export async function getConfig(): Promise<VoiceConversationConfig> {
  const { data } = await api.get<ApiEnvelope<VoiceConversationConfig>>(`${BASE}/config`);
  return data.data;
}

export async function createSession(input: CreateVoiceConversationInput): Promise<VoiceConversationSession> {
  const { data } = await api.post<ApiEnvelope<{ session: VoiceConversationSession }>>(`${BASE}/sessions`, input);
  return data.data.session;
}

export async function listSessions(
  page = 1,
  limit = 10
): Promise<{ sessions: VoiceConversationSessionRow[]; total: number }> {
  const { data } = await api.get<ApiEnvelope<{ sessions: VoiceConversationSessionRow[]; total: number }>>(
    `${BASE}/sessions`,
    { params: { page, limit } }
  );
  return data.data;
}

export async function getSession(sessionId: string): Promise<VoiceConversationSession> {
  const { data } = await api.get<ApiEnvelope<{ session: VoiceConversationSession }>>(
    `${BASE}/sessions/${encodeURIComponent(sessionId)}`
  );
  return data.data.session;
}

export async function startSession(sessionId: string): Promise<VoiceConversationStartResponse> {
  const { data } = await api.post<ApiEnvelope<VoiceConversationStartResponse>>(
    `${BASE}/sessions/${encodeURIComponent(sessionId)}/start`,
    undefined,
    { timeout: TURN_TIMEOUT_MS }
  );
  return data.data;
}

export interface TranscribeOptions {
  /** Answers already given; lets the server reject a duplicate/stale recording before Whisper runs. */
  expectedTurn: number;
  signal?: AbortSignal;
}

/**
 * Step 1 of an answer: upload the recording and get its transcript back.
 * Speech-to-text only -- the server runs no AI, makes no speech and saves nothing.
 * This is the only call that ever carries audio.
 */
export async function transcribe(
  sessionId: string,
  audio: Blob,
  { expectedTurn, signal }: TranscribeOptions
): Promise<TranscriptionResult> {
  const form = new FormData();
  // The server ignores the filename and identifies the audio from its bytes.
  form.append("audio", audio, `answer.${extensionFor(audio.type)}`);
  form.append("expected_turn", String(expectedTurn));
  // Override the client's JSON default so Axios sends real multipart.
  const { data } = await api.post<ApiEnvelope<TranscriptionResult>>(
    `${BASE}/sessions/${encodeURIComponent(sessionId)}/transcribe`,
    form,
    { headers: { "Content-Type": "multipart/form-data" }, timeout: TURN_TIMEOUT_MS, signal }
  );
  return data.data;
}

export interface RespondOptions {
  /** The transcript from `transcribe` (or the stored one, when retrying). */
  transcript: string;
  /** Answers already given; lets the server reject a duplicate/stale submission. */
  expectedTurn: number;
  /** Seconds from the AI finishing to the answer starting (pressure mode). */
  responseSeconds?: number;
  /** What transcription measured; sent back so the speaking analysis stays accurate. */
  meta?: TranscriptionMeta;
  signal?: AbortSignal;
}

/**
 * Step 2 of an answer: submit the transcript and get the AI's reply (+ speech).
 * Plain JSON, no audio -- so it is also the "Retry response" call, which can
 * therefore never trigger speech-to-text.
 */
export async function respond(
  sessionId: string,
  { transcript, expectedTurn, responseSeconds, meta, signal }: RespondOptions
): Promise<VoiceConversationResponse> {
  const body: Record<string, unknown> = { transcript, expected_turn: expectedTurn };
  if (responseSeconds !== undefined) body.response_seconds = Math.round(responseSeconds * 10) / 10;
  if (meta?.duration_seconds != null) body.duration_seconds = meta.duration_seconds;
  if (meta?.language) body.language = meta.language;
  if (meta?.pause_metrics) body.pause_metrics = meta.pause_metrics;
  const { data } = await api.post<ApiEnvelope<VoiceConversationResponse>>(
    `${BASE}/sessions/${encodeURIComponent(sessionId)}/respond`,
    body,
    { timeout: TURN_TIMEOUT_MS, signal }
  );
  return data.data;
}

export async function endSession(
  sessionId: string
): Promise<{ session: VoiceConversationSession; summary: VoiceConversationSummary | null }> {
  const { data } = await api.post<
    ApiEnvelope<{ session: VoiceConversationSession; summary: VoiceConversationSummary | null }>
  >(`${BASE}/sessions/${encodeURIComponent(sessionId)}/end`, undefined, { timeout: TURN_TIMEOUT_MS });
  return data.data;
}

/**
 * Fetch an AI audio clip through the authenticated client (an <audio src> tag
 * cannot send the Authorization header) and return a blob for playback.
 * `audioUrl` is the server-issued path, e.g. `/api/v1/voice-conversation/audio/<token>`.
 */
export async function fetchAudio(audioUrl: string): Promise<Blob> {
  const marker = `${BASE}/audio/`;
  const index = audioUrl.indexOf(marker);
  if (index === -1) throw new Error("Unexpected audio location.");
  const token = audioUrl.slice(index + marker.length);
  const { data } = await api.get<Blob>(`${BASE}/audio/${encodeURIComponent(token)}`, { responseType: "blob" });
  return data;
}
