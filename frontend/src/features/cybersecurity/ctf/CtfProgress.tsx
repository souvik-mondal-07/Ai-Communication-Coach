import type { CtfSessionDetail } from "@/features/cybersecurity/ctf/ctfTypes";

interface CtfProgressProps {
  session: CtfSessionDetail;
}

const STATUS_STYLES: Record<string, string> = {
  in_progress: "text-warn border-warn/30 bg-warn/10",
  completed: "text-signal border-signal/30 bg-signal/10",
  abandoned: "text-text-muted border-border bg-surface-raised",
};

const STATUS_LABELS: Record<string, string> = {
  in_progress: "In Progress",
  completed: "Completed",
  abandoned: "Abandoned",
};

export function CtfProgress({ session }: CtfProgressProps) {
  return (
    <div className="flex items-center gap-2 text-xs text-text-muted">
      <span
        className={`rounded-full border px-2.5 py-1 font-medium ${
          STATUS_STYLES[session.status] ?? STATUS_STYLES.in_progress
        }`}
      >
        {STATUS_LABELS[session.status] ?? session.status}
      </span>
      <span>{session.hints_used} hint{session.hints_used === 1 ? "" : "s"} used</span>
    </div>
  );
}
