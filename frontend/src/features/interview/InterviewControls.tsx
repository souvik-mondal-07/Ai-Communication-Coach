import { useState } from "react";
import { Button } from "@/components/ui/button";

interface InterviewControlsProps {
  answeredCount: number;
  onEnd: () => void | Promise<void>;
  isEnding: boolean;
}

/** End-interview control with a confirmation step (ending early is allowed but irreversible). */
export function InterviewControls({ answeredCount, onEnd, isEnding }: InterviewControlsProps) {
  const [confirming, setConfirming] = useState(false);

  if (!confirming) {
    return (
      <div className="flex justify-end">
        <Button variant="secondary" size="sm" onClick={() => setConfirming(true)} disabled={isEnding}>
          End Interview
        </Button>
      </div>
    );
  }

  return (
    <div
      role="alertdialog"
      aria-label="End interview?"
      className="flex flex-col gap-3 rounded-[var(--radius-panel)] border border-warn/40 bg-warn/10 px-3 py-3 sm:flex-row sm:items-center sm:justify-between"
    >
      <p className="text-sm text-text-secondary">
        {answeredCount === 0
          ? "You haven't answered anything yet, so this interview won't be scored."
          : `End now? Your ${answeredCount} answered question${answeredCount === 1 ? "" : "s"} will be evaluated.`}
      </p>
      <div className="flex gap-2">
        <Button variant="danger" size="sm" onClick={() => void onEnd()} disabled={isEnding}>
          {isEnding ? "Ending…" : "Yes, end interview"}
        </Button>
        <Button variant="ghost" size="sm" onClick={() => setConfirming(false)} disabled={isEnding}>
          Keep going
        </Button>
      </div>
    </div>
  );
}
