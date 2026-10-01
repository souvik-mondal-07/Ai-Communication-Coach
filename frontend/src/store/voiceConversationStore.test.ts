import { AxiosError, type AxiosResponse } from "axios";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as service from "@/services/voiceConversationService";
import { useVoiceConversationStore } from "@/store/voiceConversationStore";
import {
  EMPTY_TRANSCRIPT_MESSAGE,
  isBlankTranscript,
  type TranscriptionResult,
  type VoiceConversationResponse,
  type VoiceConversationSession,
} from "@/types/voiceConversation";

/**
 * The store is where "STT happens once per recording" is enforced on the client:
 * transcribe → validate → store transcript → automatic AI submission → (on AI failure)
 * retry from the stored transcript. The HTTP service is mocked; nothing here touches
 * a network, a microphone, Whisper or Gemini.
 */
vi.mock("@/services/voiceConversationService", () => ({
  transcribe: vi.fn(),
  respond: vi.fn(),
  getSession: vi.fn(),
  getConfig: vi.fn(),
  createSession: vi.fn(),
  startSession: vi.fn(),
  endSession: vi.fn(),
  fetchAudio: vi.fn(),
  listSessions: vi.fn(),
}));

const transcribe = vi.mocked(service.transcribe);
const respond = vi.mocked(service.respond);
const getSession = vi.mocked(service.getSession);

const TRANSCRIPT = "I would investigate the suspicious login by checking the authentication logs.";

function session(overrides: Partial<VoiceConversationSession> = {}): VoiceConversationSession {
  return {
    session_id: "s1",
    mode: "cybersecurity",
    mode_label: "Cybersecurity Q&A",
    difficulty: "intermediate",
    topic: null,
    status: "active",
    started_at: null,
    last_activity_at: null,
    ended_at: null,
    turn_count: 1,
    user_turn_count: 0,
    assistant_turn_count: 1,
    max_session_turns: 20,
    linked_session: null,
    messages: [{ role: "assistant", text: "What is a SIEM?", timestamp: null, audio_available: true }],
    summary: null,
    ...overrides,
  };
}

function transcription(text: string, extra: Partial<TranscriptionResult> = {}): TranscriptionResult {
  return {
    transcript: text,
    is_empty: text.trim() === "",
    duration_seconds: 6,
    language: "en",
    pause_metrics: null,
    ...extra,
  };
}

function aiTurn(overrides: Partial<VoiceConversationResponse> = {}): VoiceConversationResponse {
  return {
    user_transcript: TRANSCRIPT,
    user_voice_analysis: null,
    ai_response: "Good. What would you check next?",
    audio_url: "/api/v1/voice-conversation/audio/tok",
    audio_error: null,
    turn_number: 1,
    conversation_complete: false,
    summary: null,
    mode_info: {},
    ...overrides,
  };
}

function httpError(status: number, errorCode: string): AxiosError {
  const response = { status, data: { error_code: errorCode, message: "x" } } as AxiosResponse;
  return new AxiosError("failed", "ERR_BAD_RESPONSE", undefined, undefined, response);
}

const blob = () => new Blob([new Uint8Array([1, 2, 3])], { type: "audio/webm" });
const store = () => useVoiceConversationStore.getState();

beforeEach(() => {
  vi.clearAllMocks();
  useVoiceConversationStore.getState().reset();
  useVoiceConversationStore.setState({ session: session() });
});

describe("transcript validation", () => {
  it.each([null, undefined, "", "   ", "\n", "\t", " \n\t "])(
  "treats %j as blank",
  (value: string | null | undefined) => {
    expect(isBlankTranscript(value)).toBe(true);
  });

  it("accepts real text", () => {
    expect(isBlankTranscript(TRANSCRIPT)).toBe(false);
  });
});

describe("automatic submission", () => {
  it("transcribes once, then sends the transcript to the AI with no manual step", async () => {
    transcribe.mockResolvedValue(transcription(TRANSCRIPT));
    respond.mockResolvedValue(aiTurn());

    await store().submitRecordedAudio(blob(), 4.2);

    expect(transcribe).toHaveBeenCalledTimes(1);
    expect(respond).toHaveBeenCalledTimes(1);
    const [sessionId, options] = respond.mock.calls[0];
    expect(sessionId).toBe("s1");
    expect(options).toMatchObject({ transcript: TRANSCRIPT, expectedTurn: 0, responseSeconds: 4.2 });
    expect(options.meta?.duration_seconds).toBe(6);

    const state = store();
    expect(state.busy).toBeNull();
    expect(state.currentTranscript).toBeNull(); // now part of the saved conversation
    expect(state.failedResponse).toBeNull();
    expect(state.session?.messages.map((m) => m.role)).toEqual(["assistant", "user", "assistant"]);
    expect(state.session?.messages[1].text).toBe(TRANSCRIPT);
    expect(state.session?.user_turn_count).toBe(1);
    expect(state.aiAudio.url).toBe("/api/v1/voice-conversation/audio/tok");
  });

  it("shows transcribing, then processing, as separate phases", async () => {
    const phases: Array<string | null> = [];
    const unsubscribe = useVoiceConversationStore.subscribe((s) => {
      if (phases.at(-1) !== s.busy) phases.push(s.busy);
    });
    transcribe.mockResolvedValue(transcription(TRANSCRIPT));
    respond.mockResolvedValue(aiTurn());

    await store().submitRecordedAudio(blob());
    unsubscribe();

    expect(phases).toEqual(["transcribing", "processing", null]);
  });

  it("exposes the transcript while the AI is working", async () => {
    transcribe.mockResolvedValue(transcription(TRANSCRIPT));
    let seen: string | null = null;
    respond.mockImplementation(async () => {
      seen = store().currentTranscript;
      return aiTurn();
    });
    await store().submitRecordedAudio(blob());
    expect(seen).toBe(TRANSCRIPT);
  });
});

describe("empty transcript", () => {
  it.each(["", "   ", "\n", "\t"])(
  "never reaches the AI for %j",
  async (text: string) => {
    transcribe.mockResolvedValue(transcription(text));

    await store().submitRecordedAudio(blob());

    expect(respond).not.toHaveBeenCalled(); // no Gemini, no TTS, no AI turn
    const state = store();
    expect(state.transcriptNotice).toBe("I couldn't hear a clear response. Please try again.");
    expect(state.transcriptNotice).toBe(EMPTY_TRANSCRIPT_MESSAGE);
    expect(state.error).toBeNull();
    expect(state.busy).toBeNull(); // ready to record again immediately
    expect(state.currentTranscript).toBeNull();
    expect(state.failedResponse).toBeNull();
    expect(state.session?.messages).toHaveLength(1);
    expect(state.session?.user_turn_count).toBe(0);
  });

  it("treats a server-flagged empty result as empty even if the text looks non-blank", async () => {
    transcribe.mockResolvedValue(transcription("anything", { is_empty: true }));
    await store().submitRecordedAudio(blob());
    expect(respond).not.toHaveBeenCalled();
    expect(store().transcriptNotice).toBe(EMPTY_TRANSCRIPT_MESSAGE);
  });

  it("lets the learner record again straight away", async () => {
    transcribe.mockResolvedValueOnce(transcription("  "));
    await store().submitRecordedAudio(blob());
    transcribe.mockResolvedValueOnce(transcription(TRANSCRIPT));
    respond.mockResolvedValue(aiTurn());

    await store().submitRecordedAudio(blob());

    expect(transcribe).toHaveBeenCalledTimes(2);
    expect(respond).toHaveBeenCalledTimes(1);
    expect(store().transcriptNotice).toBeNull();
    expect(store().session?.user_turn_count).toBe(1);
  });

  it("also handles the server refusing a blank transcript", async () => {
    transcribe.mockResolvedValue(transcription(TRANSCRIPT));
    respond.mockRejectedValue(httpError(422, "EMPTY_TRANSCRIPT"));
    await store().submitRecordedAudio(blob());
    expect(store().transcriptNotice).toBe(EMPTY_TRANSCRIPT_MESSAGE);
    expect(store().failedResponse).toBeNull();
    expect(store().error).toBeNull();
  });
});

describe("AI failure after successful transcription", () => {
  it("keeps the transcript and offers a retry that needs no audio", async () => {
    transcribe.mockResolvedValue(transcription(TRANSCRIPT));
    respond.mockRejectedValue(httpError(503, "AI_SERVICE_UNAVAILABLE"));

    await store().submitRecordedAudio(blob(), 3);

    const state = store();
    expect(state.error).toBeTruthy();
    expect(state.currentTranscript).toBe(TRANSCRIPT);
    expect(state.failedResponse).toMatchObject({ transcript: TRANSCRIPT, expectedTurn: 0, responseSeconds: 3 });
    expect(state.failedResponse).not.toHaveProperty("audio"); // nothing to re-send
    expect(state.busy).toBeNull();
    expect(state.session?.messages).toHaveLength(1); // nothing half-saved
  });

  it("does not offer a retry for errors a retry cannot fix", async () => {
    getSession.mockResolvedValue(session({ user_turn_count: 1 }));
    transcribe.mockResolvedValue(transcription(TRANSCRIPT));
    respond.mockRejectedValue(httpError(409, "TURN_MISMATCH"));

    await store().submitRecordedAudio(blob());

    expect(store().failedResponse).toBeNull();
    expect(getSession).toHaveBeenCalledWith("s1"); // resynced with the server
  });
});

describe("Retry response", () => {
  async function failFirst() {
    transcribe.mockResolvedValue(transcription(TRANSCRIPT));
    respond.mockRejectedValueOnce(httpError(503, "AI_SERVICE_UNAVAILABLE"));
    await store().submitRecordedAudio(blob(), 2.5);
  }

  it("does NOT run speech-to-text again", async () => {
    await failFirst();
    expect(transcribe).toHaveBeenCalledTimes(1);
    expect(respond).toHaveBeenCalledTimes(1);

    respond.mockResolvedValueOnce(aiTurn());
    await store().retryResponse();

    expect(transcribe).toHaveBeenCalledTimes(1); // STT count did not increase
    expect(respond).toHaveBeenCalledTimes(2); // the AI was called a second time
  });

  it("re-submits the exact original transcript, timing and metadata", async () => {
    await failFirst();
    respond.mockResolvedValueOnce(aiTurn());
    await store().retryResponse();

    const first = respond.mock.calls[0][1];
    const retry = respond.mock.calls[1][1];
    expect(retry.transcript).toBe(TRANSCRIPT);
    expect(retry).toMatchObject({ transcript: first.transcript, expectedTurn: 0, responseSeconds: 2.5 });
    expect(retry.meta).toEqual(first.meta);
    expect(Object.values(retry).some((v) => v instanceof Blob)).toBe(false); // no audio is sent
  });

  it("completes the turn and clears the failure", async () => {
    await failFirst();
    respond.mockResolvedValueOnce(aiTurn());
    await store().retryResponse();

    const state = store();
    expect(state.failedResponse).toBeNull();
    expect(state.currentTranscript).toBeNull();
    expect(state.error).toBeNull();
    expect(state.session?.messages.map((m) => m.role)).toEqual(["assistant", "user", "assistant"]);
    expect(state.session?.user_turn_count).toBe(1);
  });

  it("keeps the transcript when the retry fails too", async () => {
    await failFirst();
    respond.mockRejectedValueOnce(httpError(503, "AI_SERVICE_UNAVAILABLE"));
    await store().retryResponse();

    expect(store().failedResponse?.transcript).toBe(TRANSCRIPT);
    expect(transcribe).toHaveBeenCalledTimes(1);

    respond.mockResolvedValueOnce(aiTurn());
    await store().retryResponse();
    expect(store().session?.user_turn_count).toBe(1);
    expect(transcribe).toHaveBeenCalledTimes(1);
    expect(respond).toHaveBeenCalledTimes(3);
  });

  it("does nothing when there is nothing to retry", async () => {
    await store().retryResponse();
    expect(transcribe).not.toHaveBeenCalled();
    expect(respond).not.toHaveBeenCalled();
  });

  it("a double click creates only one AI submission", async () => {
    await failFirst();
    respond.mockResolvedValue(aiTurn());
    await Promise.all([store().retryResponse(), store().retryResponse()]);
    expect(respond).toHaveBeenCalledTimes(2); // the failed attempt + exactly one retry
    expect(transcribe).toHaveBeenCalledTimes(1);
  });

  it("discarding the failed answer removes the stored transcript", async () => {
    await failFirst();
    store().discardFailedResponse();
    expect(store().failedResponse).toBeNull();
    expect(store().currentTranscript).toBeNull();
    await store().retryResponse();
    expect(respond).toHaveBeenCalledTimes(1);
  });
});

describe("duplicate protection", () => {
  it("the same recording delivered twice in a row is transcribed once", async () => {
    transcribe.mockResolvedValue(transcription(TRANSCRIPT));
    respond.mockResolvedValue(aiTurn());
    const recording = blob();

    await Promise.all([store().submitRecordedAudio(recording), store().submitRecordedAudio(recording)]);

    expect(transcribe).toHaveBeenCalledTimes(1);
    expect(respond).toHaveBeenCalledTimes(1);
  });

  it("the same recording delivered again after it finished is still ignored", async () => {
    transcribe.mockResolvedValue(transcription(TRANSCRIPT));
    respond.mockResolvedValue(aiTurn());
    const recording = blob();

    await store().submitRecordedAudio(recording);
    await store().submitRecordedAudio(recording);

    expect(transcribe).toHaveBeenCalledTimes(1);
    expect(respond).toHaveBeenCalledTimes(1);
    expect(store().session?.user_turn_count).toBe(1);
  });

  it("a different recording while one is being worked on is ignored", async () => {
    let release: (value: TranscriptionResult) => void = () => {};
    transcribe.mockReturnValue(new Promise<TranscriptionResult>((resolve) => (release = resolve)));
    respond.mockResolvedValue(aiTurn());

    const first = store().submitRecordedAudio(blob());
    await store().submitRecordedAudio(blob()); // arrives mid-transcription
    release(transcription(TRANSCRIPT));
    await first;

    expect(transcribe).toHaveBeenCalledTimes(1);
    expect(respond).toHaveBeenCalledTimes(1);
  });

  it("a recording failing to transcribe can't be re-delivered as a second attempt", async () => {
    transcribe.mockRejectedValue(httpError(503, "STT_FAILED"));
    const recording = blob();
    await store().submitRecordedAudio(recording);
    await store().submitRecordedAudio(recording);
    expect(transcribe).toHaveBeenCalledTimes(1);
  });
});

describe("speech-to-text failure", () => {
  it("reports the error, creates no transcript, and never reaches the AI", async () => {
    transcribe.mockRejectedValue(httpError(503, "STT_FAILED"));

    await store().submitRecordedAudio(blob());

    const state = store();
    expect(state.error).toBeTruthy();
    expect(respond).not.toHaveBeenCalled();
    expect(state.failedResponse).toBeNull(); // nothing to retry without a transcript
    expect(state.currentTranscript).toBeNull();
    expect(state.busy).toBeNull();
  });

  it("is ignored when there is no active session", async () => {
    useVoiceConversationStore.setState({ session: null });
    await store().submitRecordedAudio(blob());
    expect(transcribe).not.toHaveBeenCalled();
  });
});

describe("TTS failure", () => {
  it("keeps the AI text and shows a notice", async () => {
    transcribe.mockResolvedValue(transcription(TRANSCRIPT));
    respond.mockResolvedValue(aiTurn({ audio_url: null, audio_error: "TTS_FAILED" }));

    await store().submitRecordedAudio(blob());

    const state = store();
    expect(state.session?.messages.at(-1)?.text).toBe("Good. What would you check next?");
    expect(state.audioNotice).toBeTruthy();
    expect(state.aiAudio.url).toBeNull();
    expect(state.error).toBeNull();
    expect(state.failedResponse).toBeNull();
    expect(state.session?.status).toBe("active"); // still usable
  });
});

describe("conversation continuity", () => {
  it("sends the new expected turn on the following answer", async () => {
    transcribe.mockResolvedValue(transcription(TRANSCRIPT));
    respond.mockResolvedValueOnce(aiTurn({ turn_number: 1 }));
    await store().submitRecordedAudio(blob());

    respond.mockResolvedValueOnce(aiTurn({ turn_number: 2, user_transcript: "Second answer" }));
    transcribe.mockResolvedValueOnce(transcription("Second answer"));
    await store().submitRecordedAudio(blob());

    expect(transcribe.mock.calls[0][2].expectedTurn).toBe(0);
    expect(transcribe.mock.calls[1][2].expectedTurn).toBe(1);
    expect(respond.mock.calls[1][1].expectedTurn).toBe(1);
    expect(store().session?.messages).toHaveLength(5);
  });
});
