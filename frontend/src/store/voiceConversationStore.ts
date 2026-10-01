import axios from "axios";
import { create } from "zustand";
import * as voiceConversationService from "@/services/voiceConversationService";
import { getApiErrorMessage } from "@/utils/apiError";
import {
  EMPTY_TRANSCRIPT_MESSAGE,
  isBlankTranscript,
  type CreateVoiceConversationInput,
  type FailedResponse,
  type VoiceConversationConfig,
  type VoiceConversationResponse,
  type VoiceConversationSession,
  type VoiceConversationSummary,
} from "@/types/voiceConversation";

/**
 * State for the live voice conversation. Recording and playback are device
 * concerns and live in hooks; this store owns the session, the transcript and
 * the single "is the server busy" flag that prevents overlapping requests.
 *
 * One answer is two requests, chained automatically (there is no Send button):
 *
 *   submitRecordedAudio(audio)
 *     → transcribe        busy "transcribing"   (the only request that carries audio)
 *     → validate          blank → notice, back to ready; nothing reaches the AI
 *     → store transcript  `currentTranscript`
 *     → processTranscript busy "processing"     (Gemini + TTS; text only)
 *
 * If the AI step fails, the transcript is kept in `failedResponse` and
 * `retryResponse()` calls processTranscript again with that same text. The
 * retry path has no access to any audio, so it cannot run speech-to-text.
 */

type Busy = "loading" | "starting" | "transcribing" | "processing" | "ending" | null;

interface AiAudioRequest {
  /** Server-issued URL, or null when this reply has no audio. */
  url: string | null;
  /** Bumped for every new AI reply so the player reloads even for identical URLs. */
  seq: number;
}

interface VoiceConversationState {
  config: VoiceConversationConfig | null;
  session: VoiceConversationSession | null;
  summary: VoiceConversationSummary | null;
  busy: Busy;
  error: string | null;
  /** Spoken audio could not be produced for the latest reply (text is still shown). */
  audioNotice: string | null;
  aiAudio: AiAudioRequest;
  /** The transcript of the answer being processed (or whose AI reply failed). Cleared once the turn is saved. */
  currentTranscript: string | null;
  /** Shown instead of an error when nothing usable was heard. The learner can simply record again. */
  transcriptNotice: string | null;
  /**
   * An answer that was transcribed but not answered by the AI. Holds the transcript, never the
   * audio: "Retry response" re-submits this text and speech-to-text is not involved.
   */
  failedResponse: FailedResponse | null;

  loadConfig: () => Promise<void>;
  create: (input: CreateVoiceConversationInput) => Promise<string>;
  load: (sessionId: string) => Promise<void>;
  start: () => Promise<void>;
  /** A finished recording: transcribe it once, then (automatically) get the AI's reply. */
  submitRecordedAudio: (audio: Blob, responseSeconds?: number) => Promise<void>;
  /** Retry the AI step with the stored transcript. Sends no audio and never runs STT. */
  retryResponse: () => Promise<void>;
  discardFailedResponse: () => void;
  end: () => Promise<void>;
  clearError: () => void;
  reset: () => void;
}

const AUDIO_NOTICES: Record<string, string> = {
  TTS_NOT_CONFIGURED: "Spoken replies aren't set up on the server, so the mentor's reply is shown as text.",
  TTS_FAILED: "The spoken reply couldn't be generated this time. You can read it below.",
};

function errorCode(err: unknown): string | null {
  if (axios.isAxiosError(err)) {
    const code = (err.response?.data as { error_code?: unknown } | undefined)?.error_code;
    if (typeof code === "string") return code;
  }
  return null;
}

/** Messages worded for the voice flow; falls back to the server's own safe message. */
function voiceErrorMessage(err: unknown, fallback: string): string {
  if (axios.isAxiosError(err) && err.code === "ECONNABORTED") {
    return "That took too long. Please try again.";
  }
  switch (errorCode(err)) {
    case "AI_SERVICE_UNAVAILABLE":
      return "The AI mentor couldn't respond just now. Your answer wasn't lost, so please try again.";
    case "STT_FAILED":
    case "STT_UNAVAILABLE":
      return "Your recording couldn't be transcribed. Please record your answer again.";
    default:
      return getApiErrorMessage(err, fallback);
  }
}

// Codes where re-submitting the same transcript can't succeed, so no "Retry response" is offered.
const AI_NOT_RETRYABLE = new Set(["AUDIO_TOO_LONG", "SESSION_NOT_ACTIVE", "TURN_MISMATCH", "EMPTY_TRANSCRIPT"]);

function isCancelled(err: unknown): boolean {
  return axios.isCancel(err);
}

/**
 * Recordings already handed to `submitRecordedAudio`. A recorder that reports the same
 * Blob twice (double stop, repeated callback, re-render) is ignored even after the first
 * submission has finished. Weak, so it never keeps audio alive.
 */
const submittedRecordings = new WeakSet<Blob>();

function applyTurn(
  session: VoiceConversationSession,
  response: VoiceConversationResponse
): VoiceConversationSession {
  const now = new Date().toISOString();
  const messages = [...session.messages];
  if (response.user_transcript !== undefined) {
    messages.push({
      role: "user",
      text: response.user_transcript,
      timestamp: now,
      voice_analysis: response.user_voice_analysis ?? null,
      duration_seconds: response.user_voice_analysis?.duration_seconds ?? null,
    });
  }
  messages.push({ role: "assistant", text: response.ai_response, timestamp: now, audio_available: !!response.audio_url });
  return {
    ...session,
    messages,
    user_turn_count: response.turn_number,
    assistant_turn_count: session.assistant_turn_count + 1,
    turn_count: session.turn_count + (response.user_transcript !== undefined ? 2 : 1),
    status: response.conversation_complete ? "completed" : "active",
    summary: response.summary ?? session.summary,
  };
}

export const useVoiceConversationStore = create<VoiceConversationState>((set, get) => {
  /** Bumped when the conversation is replaced/reset so a late response can't touch the new state. */
  let epoch = 0;
  let inFlight: AbortController | null = null;

  const begin = () => {
    inFlight?.abort();
    inFlight = new AbortController();
    return { signal: inFlight.signal, epoch };
  };

  /**
   * Transcript → AI → TTS. Text only. Used by the automatic path right after
   * transcription AND by "Retry response" with the stored transcript.
   * The caller owns `busy`; this never touches audio or speech-to-text.
   */
  const processTranscript = async (
    sessionId: string,
    answer: FailedResponse,
    run: { signal: AbortSignal; epoch: number }
  ): Promise<void> => {
    set({ busy: "processing", error: null, audioNotice: null, currentTranscript: answer.transcript });
    try {
      const response = await voiceConversationService.respond(sessionId, {
        transcript: answer.transcript,
        expectedTurn: answer.expectedTurn,
        responseSeconds: answer.responseSeconds,
        meta: answer.meta,
        signal: run.signal,
      });
      const current = get().session;
      if (run.epoch !== epoch || !current || current.session_id !== sessionId) return;
      set((state) => ({
        session: applyTurn(current, response),
        summary: response.summary ?? state.summary,
        currentTranscript: null,
        failedResponse: null,
        aiAudio: { url: response.audio_url, seq: state.aiAudio.seq + 1 },
        audioNotice: response.audio_error ? (AUDIO_NOTICES[response.audio_error] ?? null) : null,
      }));
    } catch (err) {
      if (isCancelled(err) || run.epoch !== epoch) return;
      const code = errorCode(err);
      if (code === "EMPTY_TRANSCRIPT") {
        set({ transcriptNotice: EMPTY_TRANSCRIPT_MESSAGE, currentTranscript: null, failedResponse: null });
        return;
      }
      const retryable = !(code && AI_NOT_RETRYABLE.has(code));
      set({
        error: voiceErrorMessage(err, "The AI couldn't respond. Please try again."),
        // The transcript survives the failure: that's all a retry needs.
        failedResponse: retryable ? answer : null,
        currentTranscript: retryable ? answer.transcript : null,
      });
      // Out of sync (e.g. a duplicate submit, or a reply that arrived after a timeout): pull the server's view.
      if (code === "TURN_MISMATCH") void get().load(sessionId);
    }
  };

  const submitRecordedAudio = async (audio: Blob, responseSeconds?: number): Promise<void> => {
    const { session, busy } = get();
    if (!session || busy) return; // never two requests at once
    if (submittedRecordings.has(audio)) return; // this recording was already handed in
    submittedRecordings.add(audio);

    const sessionId = session.session_id;
    const expectedTurn = session.user_turn_count;
    const run = begin();
    set({
      busy: "transcribing",
      error: null,
      audioNotice: null,
      transcriptNotice: null,
      currentTranscript: null,
      failedResponse: null,
    });
    try {
      // 1) Speech-to-text, exactly once for this recording.
      let transcription;
      try {
        transcription = await voiceConversationService.transcribe(sessionId, audio, {
          expectedTurn,
          signal: run.signal,
        });
      } catch (err) {
        if (isCancelled(err) || run.epoch !== epoch) return;
        const code = errorCode(err);
        set({ error: voiceErrorMessage(err, "Your recording couldn't be transcribed. Please record again.") });
        if (code === "TURN_MISMATCH") void get().load(sessionId);
        return; // no transcript exists, so there is nothing to retry: the learner records again
      }
      if (run.epoch !== epoch || get().session?.session_id !== sessionId) return;

      // 2) Validate. A blank transcript never reaches the AI, TTS or the conversation history.
      if (transcription.is_empty || isBlankTranscript(transcription.transcript)) {
        set({ transcriptNotice: EMPTY_TRANSCRIPT_MESSAGE });
        return;
      }

      // 3) Keep the transcript, then submit it automatically (no Send button).
      const answer: FailedResponse = {
        transcript: transcription.transcript.trim(),
        expectedTurn,
        responseSeconds,
        meta: {
          duration_seconds: transcription.duration_seconds,
          language: transcription.language,
          pause_metrics: transcription.pause_metrics,
        },
      };
      set({ currentTranscript: answer.transcript });
      await processTranscript(sessionId, answer, run);
    } finally {
      if (run.epoch === epoch) set({ busy: null });
    }
  };

  const retryResponse = async (): Promise<void> => {
    const { session, busy, failedResponse } = get();
    if (!session || busy || !failedResponse) return; // one retry at a time
    const run = begin();
    set({ failedResponse: null }); // a second click while this runs finds nothing to retry
    try {
      await processTranscript(session.session_id, failedResponse, run);
    } finally {
      if (run.epoch === epoch) set({ busy: null });
    }
  };

  return {
    config: null,
    session: null,
    summary: null,
    busy: null,
    error: null,
    audioNotice: null,
    aiAudio: { url: null, seq: 0 },
    currentTranscript: null,
    transcriptNotice: null,
    failedResponse: null,

    loadConfig: async () => {
      try {
        set({ config: await voiceConversationService.getConfig() });
      } catch {
        /* defaults are used; the page still works */
      }
    },

    create: async (input) => {
      set({ busy: "loading", error: null });
      try {
        const session = await voiceConversationService.createSession(input);
        epoch += 1;
        set({
          session,
          summary: null,
          failedResponse: null,
          currentTranscript: null,
          transcriptNotice: null,
          aiAudio: { url: null, seq: 0 },
        });
        return session.session_id;
      } finally {
        set({ busy: null });
      }
    },

    load: async (sessionId) => {
      if (get().session?.session_id !== sessionId) {
        // Switching conversations: nothing in flight or kept for the old one may carry over.
        epoch += 1;
        inFlight?.abort();
        inFlight = null;
        set({ currentTranscript: null, transcriptNotice: null, failedResponse: null });
      }
      set({ busy: "loading", error: null });
      try {
        const session = await voiceConversationService.getSession(sessionId);
        set((state) => ({
          session,
          summary: session.summary,
          // A different session must not keep the previous one's audio.
          aiAudio: state.session?.session_id === sessionId ? state.aiAudio : { url: null, seq: state.aiAudio.seq + 1 },
        }));
      } catch (err) {
        set({ session: null, error: getApiErrorMessage(err, "Could not load this conversation.") });
      } finally {
        set({ busy: null });
      }
    },

    start: async () => {
      const { session, busy } = get();
      if (!session || busy) return;
      set({ busy: "starting", error: null, audioNotice: null });
      try {
        const result = await voiceConversationService.startSession(session.session_id);
        set((state) => ({
          session: result.session,
          aiAudio: { url: result.audio_url, seq: state.aiAudio.seq + 1 },
          audioNotice: result.audio_error ? (AUDIO_NOTICES[result.audio_error] ?? null) : null,
        }));
      } catch (err) {
        set({ error: voiceErrorMessage(err, "Could not start the conversation. Please try again.") });
      } finally {
        set({ busy: null });
      }
    },

    submitRecordedAudio,

    retryResponse,

    discardFailedResponse: () => set({ failedResponse: null, currentTranscript: null, error: null }),

    end: async () => {
      const { session, busy } = get();
      if (!session || busy) return;
      set({ busy: "ending", error: null });
      try {
        const result = await voiceConversationService.endSession(session.session_id);
        set({
          session: result.session,
          summary: result.summary,
          failedResponse: null,
          currentTranscript: null,
          transcriptNotice: null,
          aiAudio: { url: null, seq: get().aiAudio.seq + 1 },
        });
      } catch (err) {
        set({ error: voiceErrorMessage(err, "Could not end the conversation. Please try again.") });
      } finally {
        set({ busy: null });
      }
    },

    clearError: () => set({ error: null, transcriptNotice: null }),

    reset: () => {
      epoch += 1;
      inFlight?.abort(); // a late transcription/AI reply must not land in the next conversation
      inFlight = null;
      set({
        session: null,
        summary: null,
        busy: null,
        error: null,
        audioNotice: null,
        currentTranscript: null,
        transcriptNotice: null,
        failedResponse: null,
        aiAudio: { url: null, seq: get().aiAudio.seq + 1 },
      });
    },
  };
});
