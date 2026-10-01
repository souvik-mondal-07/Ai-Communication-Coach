import { useCallback, useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { AIResponseAudio } from "@/features/voice-conversation/AIResponseAudio";
import { ConversationHeader } from "@/features/voice-conversation/ConversationHeader";
import { ConversationSummary } from "@/features/voice-conversation/ConversationSummary";
import { ConversationTranscript, type PendingAnswer } from "@/features/voice-conversation/ConversationTranscript";
import { MicrophoneButton, type MicButtonState } from "@/features/voice-conversation/MicrophoneButton";
import { VoiceStatusBanner } from "@/features/voice-conversation/VoiceStatusBanner";
import { useAiAudio } from "@/hooks/useAiAudio";
import { useAnswerRecorder } from "@/hooks/useAnswerRecorder";
import { MIC_DENIED_MESSAGE } from "@/hooks/useVoice";
import { useVoiceConversationStore } from "@/store/voiceConversationStore";
import type { VoiceUiState } from "@/types/voiceConversation";

const DEFAULT_MAX_RECORDING_SECONDS = 120;

interface VoiceConversationPageProps {
  onNewConversation: () => void;
}

/**
 * The live conversation: AI speaks → user presses the mic and answers → stopping the
 * recording transcribes it → the transcript is submitted to the AI automatically →
 * the AI's reply is spoken → repeat. There is no Send button; the user only controls
 * the microphone. If the AI step fails, "Retry response" re-submits the stored
 * transcript -- it never records or transcribes again.
 */
export function VoiceConversationPage({ onNewConversation }: VoiceConversationPageProps) {
  const session = useVoiceConversationStore((s) => s.session);
  const summary = useVoiceConversationStore((s) => s.summary);
  const busy = useVoiceConversationStore((s) => s.busy);
  const error = useVoiceConversationStore((s) => s.error);
  const audioNotice = useVoiceConversationStore((s) => s.audioNotice);
  const aiAudio = useVoiceConversationStore((s) => s.aiAudio);
  const failedResponse = useVoiceConversationStore((s) => s.failedResponse);
  const currentTranscript = useVoiceConversationStore((s) => s.currentTranscript);
  const transcriptNotice = useVoiceConversationStore((s) => s.transcriptNotice);
  const config = useVoiceConversationStore((s) => s.config);
  const start = useVoiceConversationStore((s) => s.start);
  const submitRecordedAudio = useVoiceConversationStore((s) => s.submitRecordedAudio);
  const retryResponse = useVoiceConversationStore((s) => s.retryResponse);
  const discardFailedResponse = useVoiceConversationStore((s) => s.discardFailedResponse);
  const end = useVoiceConversationStore((s) => s.end);
  const clearError = useVoiceConversationStore((s) => s.clearError);

  const [confirmEnd, setConfirmEnd] = useState(false);
  // When the AI finished speaking: pressure mode reports how long the answer took from here.
  const promptReadyAtRef = useRef<number | null>(null);

  const maxSeconds = config?.max_recording_seconds ?? DEFAULT_MAX_RECORDING_SECONDS;
  const autoPlay = config?.auto_play ?? true;

  const markPromptReady = useCallback(() => {
    promptReadyAtRef.current = Date.now();
  }, []);

  const audio = useAiAudio({ autoPlay, onFinished: markPromptReady });

  const handleRecorded = useCallback(
    (blob: Blob) => {
      const readyAt = promptReadyAtRef.current;
      const responseSeconds = readyAt ? Math.max(0, (Date.now() - readyAt) / 1000) : undefined;
      // Transcription starts immediately; the transcript is then sent on automatically.
      void submitRecordedAudio(blob, responseSeconds);
    },
    [submitRecordedAudio]
  );

  const recorder = useAnswerRecorder({ maxSeconds, onRecorded: handleRecorded });

  // A new AI reply: load (and, where allowed, play) its audio. No audio => the prompt is ready now.
  const { load: loadAudio } = audio;
  useEffect(() => {
    if (aiAudio.seq === 0) return;
    promptReadyAtRef.current = aiAudio.url ? null : Date.now();
    void loadAudio(aiAudio.url);
  }, [aiAudio.seq, aiAudio.url, loadAudio]);

  // Leaving the conversation (or ending it) silences the AI.
  const { stop: stopAudio } = audio;
  const status = session?.status;
  useEffect(() => {
    if (status === "completed" || status === "abandoned") stopAudio();
  }, [status, stopAudio]);

  if (!session) return null;

  const finished = session.status === "completed" || session.status === "abandoned";
  const notStarted = session.status === "created";
  const transcribing = busy === "transcribing";
  const processing = busy === "processing";
  const listening = recorder.status === "recording";
  const requesting = recorder.status === "requesting";
  // The reply's audio is being fetched or played: the AI is (about to be) speaking.
  const aiSpeaking = audio.state === "playing" || audio.state === "loading";

  let uiState: VoiceUiState;
  if (finished) uiState = "completed";
  else if (busy === "starting") uiState = "starting";
  else if (transcribing) uiState = "transcribing";
  else if (processing || busy === "ending") uiState = "processing";
  else if (listening || requesting) uiState = "listening";
  else if (error) uiState = "error";
  else if (aiSpeaking) uiState = "ai_speaking";
  else if (audio.state === "paused") uiState = "paused";
  else if (notStarted) uiState = "idle";
  else uiState = "ready";

  const micState: MicButtonState = (() => {
    if (listening) return "listening";
    if (requesting) return "requesting";
    if (transcribing) return "transcribing";
    if (processing || busy === "ending" || busy === "starting") return "processing";
    if (!recorder.isSupported || recorder.permission === "denied") return "disabled";
    return "start";
  })();

  // The answer in progress, shown under the saved messages.
  const pendingAnswer: PendingAnswer | null = transcribing
    ? { phase: "transcribing", transcript: null }
    : currentTranscript
      ? { phase: failedResponse ? "failed" : "processing", transcript: currentTranscript }
      : null;

  const handleStartRecording = () => {
    // Don't record the AI's own voice through the speakers.
    if (aiSpeaking) audio.stop();
    clearError();
    // Recording a new answer replaces one whose AI reply failed.
    if (failedResponse) discardFailedResponse();
    void recorder.start();
  };

  const recorderMessage =
    recorder.permission === "denied"
      ? `${MIC_DENIED_MESSAGE} Then reload this page and press the microphone again.`
      : recorder.error;

  const answerLocked = transcribing || processing || busy === "ending" || busy === "starting";

  return (
    <div className="mx-auto w-full max-w-3xl space-y-5">
      <ConversationHeader session={session} />

      {finished ? (
        <>
          <ConversationSummary summary={summary} onNew={onNewConversation} />
          <Card>
            <CardContent className="py-4">
              <ConversationTranscript messages={session.messages} />
            </CardContent>
          </Card>
        </>
      ) : (
        <>
          <VoiceStatusBanner state={uiState} elapsedSeconds={recorder.elapsedSeconds} maxSeconds={maxSeconds} />

          {notStarted ? (
            <Card>
              <CardContent className="flex flex-col items-center gap-4 py-8 text-center">
                <p className="max-w-md text-sm text-text-secondary">
                  The mentor will speak first. Make sure your volume is up, then answer out loud with the microphone button.
                </p>
                <Button size="lg" disabled={busy !== null} onClick={() => void start()}>
                  {busy === "starting" ? "Starting…" : "Begin conversation"}
                </Button>
              </CardContent>
            </Card>
          ) : (
            <>
              <Card>
                <CardContent className="max-h-[48vh] min-h-40 overflow-y-auto py-4">
                  <ConversationTranscript messages={session.messages} pending={pendingAnswer} />
                </CardContent>
              </Card>

              <div className="flex min-h-8 justify-center">
                <AIResponseAudio state={audio.state} onPlay={() => void audio.play()} onStop={audio.stop} notice={audioNotice} />
              </div>

              {transcriptNotice && !error && (
                <div
                  role="status"
                  className="rounded-[var(--radius-panel)] border border-warn/40 bg-warn/10 px-3 py-2.5 text-sm text-warn"
                >
                  <p>{transcriptNotice}</p>
                </div>
              )}

              {(error || recorderMessage) && (
                <div
                  role="alert"
                  className="space-y-2 rounded-[var(--radius-panel)] border border-danger/40 bg-danger/10 px-3 py-2.5 text-sm text-danger"
                >
                  <p>{error ?? recorderMessage}</p>
                  {failedResponse && (
                    <div className="flex flex-wrap gap-2">
                      <Button size="sm" onClick={() => void retryResponse()} disabled={answerLocked}>
                        Retry response
                      </Button>
                      <Button size="sm" variant="secondary" onClick={discardFailedResponse} disabled={answerLocked}>
                        Record a new answer
                      </Button>
                    </div>
                  )}
                </div>
              )}

              <div className="flex flex-col items-center gap-3 py-2">
                <MicrophoneButton
                  state={micState}
                  onStart={handleStartRecording}
                  onStop={recorder.stop}
                  disabledReason={
                    recorder.permission === "denied"
                      ? "Microphone access is blocked. Allow it in your browser settings."
                      : "No usable microphone is available."
                  }
                />
                {listening && (
                  <Button variant="ghost" size="sm" onClick={recorder.cancel}>
                    Cancel recording
                  </Button>
                )}
              </div>
            </>
          )}

          {!notStarted && (
            <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border pt-4">
              <p className="text-xs text-text-muted">
                {session.user_turn_count} / {session.max_session_turns} answers
              </p>
              {confirmEnd ? (
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-sm text-text-secondary">End and get your summary?</span>
                  <Button
                    variant="danger"
                    size="sm"
                    disabled={answerLocked || listening}
                    onClick={() => {
                      setConfirmEnd(false);
                      void end();
                    }}
                  >
                    Yes, end
                  </Button>
                  <Button variant="secondary" size="sm" onClick={() => setConfirmEnd(false)}>
                    Keep going
                  </Button>
                </div>
              ) : (
                <Button variant="secondary" size="sm" disabled={answerLocked || listening} onClick={() => setConfirmEnd(true)}>
                  End conversation
                </Button>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}
