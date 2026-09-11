import { Link } from "react-router-dom";
import { Card, CardContent } from "@/components/ui/card";
import {
  CATEGORY_LABELS,
  DIFFICULTY_LABELS,
  type CtfSessionSummary,
} from "@/features/cybersecurity/ctf/ctfTypes";

interface CtfSessionListProps {
  sessions: CtfSessionSummary[];
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

export function CtfSessionList({ sessions }: CtfSessionListProps) {
  if (sessions.length === 0) {
    return (
      <p className="py-10 text-center text-sm text-text-muted">
        No challenge sessions yet — start one above.
      </p>
    );
  }

  return (
    <div className="space-y-2">
      {sessions.map((session) => (
        <Link key={session.session_id} to={`/ctf/${session.session_id}`}>
          <Card className="transition-colors hover:border-border-strong">
            <CardContent className="flex items-center justify-between gap-3 py-3.5">
              <div className="min-w-0">
                <p className="truncate text-sm font-medium text-text-primary">{session.title}</p>
                <p className="mt-0.5 text-xs text-text-muted">
                  {CATEGORY_LABELS[session.category]} · {DIFFICULTY_LABELS[session.difficulty]} ·{" "}
                  {session.platform}
                </p>
              </div>
              <span
                className={`shrink-0 rounded-full border px-2.5 py-1 text-[11px] font-medium ${
                  STATUS_STYLES[session.status] ?? STATUS_STYLES.in_progress
                }`}
              >
                {STATUS_LABELS[session.status] ?? session.status}
              </span>
            </CardContent>
          </Card>
        </Link>
      ))}
    </div>
  );
}
