import { Link, useNavigate } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EvaluationPanel } from "@/features/communication/EvaluationPanel";
import { MessageBubble } from "@/features/communication/MessageBubble";
import type { SessionDetail } from "@/features/communication/communicationTypes";
import type { CtfSessionDetail } from "@/features/cybersecurity/ctf/ctfTypes";
import { FinalInterviewResult } from "@/features/interview/FinalInterviewResult";
import { QuestionReview } from "@/features/interview/QuestionReview";
import { PressureResult } from "@/features/pressure/PressureResult";
import { ConversationSummary } from "@/features/voice-conversation/ConversationSummary";
import { ConversationTranscript } from "@/features/voice-conversation/ConversationTranscript";
import { PracticeDetail, type PracticeDetailData } from "@/features/history/PracticeDetail";
import { TYPE_META } from "@/features/history/historyMeta";
import { formatDateTime } from "@/utils/formatters";
import type { InterviewSessionView } from "@/types/interview";
import type { PressureSessionView } from "@/types/pressure";
import type { HistoryActivityType } from "@/types/history";
import type { VoiceConversationSession } from "@/types/voiceConversation";

interface Props {
  type: HistoryActivityType;
  detail: unknown;
}

const LINKED_KIND_TO_TYPE: Record<string, HistoryActivityType> = {
  interview: "interview",
  pressure: "pressure_training",
  communication: "communication",
};

function InterviewBody({ session }: { session: InterviewSessionView }) {
  const navigate = useNavigate();
  // The finished-interview result already includes the question review.
  if (session.final_evaluation) {
    return (
      <FinalInterviewResult
        session={session}
        onPracticeAgain={() => navigate(TYPE_META.interview.modulePath)}
        onBack={() => navigate("/history")}
      />
    );
  }
  const answered = session.questions.filter((q) => q.answer !== null && q.answer !== undefined);
  return answered.length > 0 ? (
    <QuestionReview questions={answered} />
  ) : (
    <p className="text-sm text-text-muted">No answers were recorded for this interview.</p>
  );
}

function PressureBody({ session }: { session: PressureSessionView }) {
  const navigate = useNavigate();
  if (session.final_evaluation) {
    return (
      <PressureResult
        session={session}
        onPracticeAgain={() => navigate(TYPE_META.pressure_training.modulePath)}
        onBack={() => navigate("/history")}
      />
    );
  }
  const answered = session.questions.filter((q) => q.answer);
  if (answered.length === 0) {
    return <p className="text-sm text-text-muted">No answers were recorded for this session.</p>;
  }
  return (
    <Card>
      <CardHeader>
        <CardTitle>Your answers</CardTitle>
      </CardHeader>
      <CardContent>
        <ol className="space-y-3 text-sm">
          {answered.map((q) => (
            <li key={q.question_number}>
              <p className="font-medium text-text-primary">{q.question}</p>
              <p className="whitespace-pre-wrap break-words text-text-secondary">{q.answer}</p>
            </li>
          ))}
        </ol>
      </CardContent>
    </Card>
  );
}

function CommunicationBody({ session }: { session: SessionDetail }) {
  return (
    <div className="space-y-4">
      {session.objective && (
        <Card>
          <CardContent className="space-y-1 py-4 text-sm text-text-secondary">
            <p>
              <span className="text-text-muted">Objective: </span>
              {session.objective}
            </p>
            {session.ai_role && (
              <p>
                <span className="text-text-muted">AI played: </span>
                {session.ai_role}
              </p>
            )}
          </CardContent>
        </Card>
      )}
      <Card>
        <CardHeader>
          <CardTitle>Conversation</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {session.messages.length === 0 ? (
            <p className="text-sm text-text-muted">No messages were recorded.</p>
          ) : (
            session.messages.map((m, i) => (
              <MessageBubble key={`${i}-${m.timestamp}`} message={m} aiLabel={session.ai_role || "AI"} />
            ))
          )}
        </CardContent>
      </Card>
      {session.evaluation && <EvaluationPanel evaluation={session.evaluation} />}
    </div>
  );
}

function CtfBody({ session }: { session: CtfSessionDetail }) {
  return (
    <div className="space-y-4">
      <Card>
        <CardContent className="space-y-2 py-4 text-sm text-text-secondary">
          <p className="whitespace-pre-wrap break-words">{session.description}</p>
          {session.user_notes && (
            <p className="whitespace-pre-wrap break-words">
              <span className="text-text-muted">Your notes: </span>
              {session.user_notes}
            </p>
          )}
          <p className="text-xs text-text-muted">Hints used: {session.hints_used}</p>
        </CardContent>
      </Card>

      {session.hints.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Hints you requested</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-3 text-sm">
              {session.hints.map((h) => (
                <li key={`${h.level}-${h.requested_at}`}>
                  <p className="text-[11px] font-medium uppercase tracking-wide text-text-muted">
                    {h.level.replace("_", " ")} · {formatDateTime(h.requested_at)}
                  </p>
                  <p className="whitespace-pre-wrap break-words text-text-secondary">{h.content}</p>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Conversation</CardTitle>
        </CardHeader>
        <CardContent>
          {session.messages.length === 0 ? (
            <p className="text-sm text-text-muted">No messages were recorded.</p>
          ) : (
            <ol className="space-y-3">
              {session.messages.map((m, i) => (
                <li key={`${i}-${m.created_at}`} className="text-sm">
                  <p className="text-[11px] font-medium uppercase tracking-wide text-text-muted">
                    {m.role === "user" ? "You" : "AI mentor"} · {formatDateTime(m.created_at)}
                  </p>
                  <p className="whitespace-pre-wrap break-words text-text-primary">{m.content}</p>
                </li>
              ))}
            </ol>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function VoiceBody({ session }: { session: VoiceConversationSession }) {
  const navigate = useNavigate();
  const linkedType = session.linked_session ? LINKED_KIND_TO_TYPE[session.linked_session.kind] : undefined;
  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>Transcript</CardTitle>
        </CardHeader>
        <CardContent>
          <ConversationTranscript messages={session.messages} />
        </CardContent>
      </Card>
      {session.summary && (
        <ConversationSummary summary={session.summary} onNew={() => navigate(TYPE_META.voice_conversation.modulePath)} />
      )}
      {session.linked_session && linkedType && (
        <p className="text-sm text-text-secondary">
          This conversation also created a{" "}
          <Link
            className="text-link underline-offset-2 hover:underline"
            to={`/history/${linkedType}/${session.linked_session.session_id}`}
          >
            {session.linked_session.label ?? "linked session"}
          </Link>{" "}
          with its full evaluation.
        </p>
      )}
    </div>
  );
}

export function ActivityDetailBody({ type, detail }: Props) {
  switch (type) {
    case "interview":
      return <InterviewBody session={detail as InterviewSessionView} />;
    case "pressure_training":
      return <PressureBody session={detail as PressureSessionView} />;
    case "communication":
      return <CommunicationBody session={detail as SessionDetail} />;
    case "ctf":
      return <CtfBody session={detail as CtfSessionDetail} />;
    case "voice_conversation":
      return <VoiceBody session={detail as VoiceConversationSession} />;
    case "cybersecurity_practice":
      return <PracticeDetail data={detail as PracticeDetailData} />;
  }
}
