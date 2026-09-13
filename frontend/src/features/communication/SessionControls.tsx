import { Button } from "@/components/ui/button";
import { DIFFICULTY_LABELS, type SessionDetail } from "@/features/communication/communicationTypes";

interface SessionControlsProps {
  session: SessionDetail;
  onEndSession: () => void;
  isCompleting: boolean;
  isCompleted: boolean;
}

export function SessionControls({
  session,
  onEndSession,
  isCompleting,
  isCompleted,
}: SessionControlsProps) {
  return (
    <div className="flex flex-col gap-3 border-b border-border pb-3 sm:flex-row sm:items-center sm:justify-between">
      <div>
        <h1 className="text-sm font-semibold text-text-primary">{session.scenario_title}</h1>
        <p className="mt-0.5 text-xs text-text-muted">
          Your role: {session.user_role} · AI role: {session.ai_role} ·{" "}
          {DIFFICULTY_LABELS[session.difficulty]}
        </p>
        <p className="mt-0.5 text-xs text-text-muted">Objective: {session.objective}</p>
      </div>
      {!isCompleted && (
        <Button variant="secondary" size="sm" onClick={onEndSession} disabled={isCompleting}>
          {isCompleting ? "Evaluating…" : "End Session"}
        </Button>
      )}
    </div>
  );
}
