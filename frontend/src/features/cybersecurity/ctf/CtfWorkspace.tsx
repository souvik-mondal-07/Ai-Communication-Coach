import { useState } from "react";
import { CheckCircle2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ChallengeInfo } from "@/features/cybersecurity/ctf/ChallengeInfo";
import { CtfChat } from "@/features/cybersecurity/ctf/CtfChat";
import { CtfProgress } from "@/features/cybersecurity/ctf/CtfProgress";
import { HintPanel } from "@/features/cybersecurity/ctf/HintPanel";
import type { CtfSessionDetail, HintLevel } from "@/features/cybersecurity/ctf/ctfTypes";

interface CtfWorkspaceProps {
  session: CtfSessionDetail;
  onSendMessage: (message: string) => Promise<void>;
  onRequestHint: (level: HintLevel) => void;
  onComplete: (flag?: string) => Promise<void>;
  isSendingMessage: boolean;
  isRequestingHint: boolean;
  isCompleting: boolean;
  error: string | null;
  onDismissError: () => void;
}

export function CtfWorkspace({
  session,
  onSendMessage,
  onRequestHint,
  onComplete,
  isSendingMessage,
  isRequestingHint,
  isCompleting,
  error,
  onDismissError,
}: CtfWorkspaceProps) {
  const [flag, setFlag] = useState("");
  const isCompleted = session.status === "completed";

  return (
    <div className="mx-auto max-w-3xl space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="font-display text-lg font-semibold text-text-primary">
          CTF &amp; Lab Mentor
        </h1>
        <CtfProgress session={session} />
      </div>

      <ChallengeInfo session={session} />

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
          <h2 className="mb-3 text-sm font-semibold text-text-primary">Mentor Conversation</h2>
          <div className="h-80">
            <CtfChat
              messages={session.messages}
              onSend={onSendMessage}
              isSending={isSendingMessage}
            />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="py-4">
          <h2 className="mb-3 text-sm font-semibold text-text-primary">Hints</h2>
          <HintPanel
            hints={session.hints}
            onRequestHint={onRequestHint}
            isRequesting={isRequestingHint}
          />
        </CardContent>
      </Card>

      {isCompleted ? (
        <div className="flex items-center gap-2 rounded-[var(--radius-panel)] border border-signal/30 bg-signal/10 px-4 py-3 text-sm text-signal">
          <CheckCircle2 size={16} />
          Challenge marked complete.
        </div>
      ) : (
        <Card>
          <CardContent className="flex flex-col gap-3 py-4 sm:flex-row sm:items-center">
            <input
              type="text"
              value={flag}
              onChange={(e) => setFlag(e.target.value)}
              placeholder="Flag (optional, for your own tracking)"
              className="flex-1 rounded-[var(--radius-panel)] border border-border bg-surface-raised px-3 py-2 text-sm text-text-primary placeholder:text-text-muted"
            />
            <Button
              onClick={() => void onComplete(flag.trim() || undefined)}
              disabled={isCompleting}
              className="shrink-0"
            >
              {isCompleting ? "Completing…" : "Mark Challenge Complete"}
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
