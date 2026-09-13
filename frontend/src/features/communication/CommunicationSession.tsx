import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { CommunicationChat } from "@/features/communication/CommunicationChat";
import { EvaluationPanel } from "@/features/communication/EvaluationPanel";
import { SessionControls } from "@/features/communication/SessionControls";
import type { SessionDetail } from "@/features/communication/communicationTypes";

interface CommunicationSessionProps {
  session: SessionDetail;
  onSendMessage: (message: string) => Promise<void>;
  onComplete: () => Promise<void>;
  isSendingMessage: boolean;
  isCompleting: boolean;
  error: string | null;
  onDismissError: () => void;
}

export function CommunicationSession({
  session,
  onSendMessage,
  onComplete,
  isSendingMessage,
  isCompleting,
  error,
  onDismissError,
}: CommunicationSessionProps) {
  const navigate = useNavigate();
  const isCompleted = session.status === "completed";

  return (
    <div className="mx-auto max-w-3xl space-y-4">
      <SessionControls
        session={session}
        onEndSession={() => void onComplete()}
        isCompleting={isCompleting}
        isCompleted={isCompleted}
      />

      {error && (
        <div className="flex items-center justify-between gap-3 rounded-[var(--radius-panel)] border border-danger/40 bg-danger/10 px-3 py-2 text-sm text-danger">
          <span>{error}</span>
          <button type="button" onClick={onDismissError} className="shrink-0 text-xs underline hover:no-underline">
            Dismiss
          </button>
        </div>
      )}

      <Card>
        <CardContent className="py-4">
          <div className="h-96">
            <CommunicationChat
              messages={session.messages}
              aiLabel={session.ai_role || "AI"}
              onSend={onSendMessage}
              isSending={isSendingMessage}
              disabled={isCompleted}
            />
          </div>
        </CardContent>
      </Card>

      {isCompleted && session.evaluation && (
        <>
          <EvaluationPanel evaluation={session.evaluation} />
          <div className="flex justify-center gap-2">
            <Button variant="secondary" onClick={() => navigate("/communication")}>
              Back to Scenarios
            </Button>
          </div>
        </>
      )}
    </div>
  );
}
