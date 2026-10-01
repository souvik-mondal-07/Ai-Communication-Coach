import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import * as voiceConversationService from "@/services/voiceConversationService";
import { VOICE_MODE_LABELS, type VoiceConversationSessionRow } from "@/types/voiceConversation";

const STATUS_LABELS: Record<VoiceConversationSessionRow["status"], string> = {
  created: "Not started",
  active: "In progress",
  completed: "Completed",
  abandoned: "Ended early",
};

/** Recent conversations, with Resume for unfinished ones. (A full history page is a later step.) */
export function ConversationHistory() {
  const [rows, setRows] = useState<VoiceConversationSessionRow[] | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    voiceConversationService
      .listSessions(1, 6)
      .then((result) => !cancelled && setRows(result.sessions))
      .catch(() => !cancelled && setFailed(true));
    return () => {
      cancelled = true;
    };
  }, []);

  if (failed) return <p className="text-sm text-text-muted">Recent conversations couldn't be loaded.</p>;
  if (rows === null) return <p className="text-sm text-text-muted">Loading recent conversations…</p>;
  if (rows.length === 0) return <p className="text-sm text-text-muted">No conversations yet.</p>;

  return (
    <ul className="space-y-2">
      {rows.map((row) => {
        const unfinished = row.status === "created" || row.status === "active";
        return (
          <li key={row.session_id}>
            <Link
              to={`/voice-conversation/${row.session_id}`}
              className="flex items-center justify-between gap-3 rounded-[var(--radius-panel)] border border-border px-3 py-2.5 text-sm transition-colors hover:border-border-strong focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-signal"
            >
              <span className="min-w-0 text-text-primary">
                {VOICE_MODE_LABELS[row.mode]}
                <span className="block truncate text-xs text-text-muted">
                  {row.started_at ? new Date(row.started_at).toLocaleDateString() : ""} · {row.user_turn_count} answers ·{" "}
                  {STATUS_LABELS[row.status]}
                </span>
              </span>
              <span className="shrink-0 text-xs text-text-secondary">{unfinished ? "Resume →" : "View"}</span>
            </Link>
          </li>
        );
      })}
    </ul>
  );
}
