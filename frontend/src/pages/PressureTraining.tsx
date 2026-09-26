import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Card, CardContent } from "@/components/ui/card";
import { PressureSetup } from "@/features/pressure/PressureSetup";
import { parseServerDate } from "@/hooks/useInterview";
import * as pressureService from "@/services/pressureService";
import { getApiErrorMessage } from "@/utils/apiError";
import { INTERVIEW_DIFFICULTY_LABELS } from "@/types/interview";
import type { PressureConfig, PressureSummary } from "@/types/pressure";

const STATUS_LABELS: Record<PressureSummary["status"], string> = {
  in_progress: "In progress",
  completed: "Completed",
  abandoned: "Ended early",
};

const MODE_LABELS = { interview: "Interview", communication: "Communication" } as const;

function HistoryRow({ item }: { item: PressureSummary }) {
  const date = new Date(parseServerDate(item.started_at)).toLocaleDateString();
  return (
    <li>
      <Link
        to={`/pressure-training/${item.session_id}`}
        className="flex items-center justify-between gap-3 rounded-[var(--radius-panel)] border border-border px-3 py-2.5 text-sm transition-colors hover:border-border-strong"
      >
        <span className="text-text-primary">
          Level {item.pressure_level} · {MODE_LABELS[item.mode]} · {INTERVIEW_DIFFICULTY_LABELS[item.difficulty]}
          <span className="block text-xs text-text-muted">
            {date} · {item.answered_count} of {item.question_count} answered · {STATUS_LABELS[item.status]}
          </span>
        </span>
        <span className="shrink-0 text-xs text-text-secondary">
          {item.status === "completed" && item.overall_score !== null
            ? `${item.overall_score} / 100`
            : item.status === "in_progress"
              ? "Resume →"
              : "—"}
        </span>
      </Link>
    </li>
  );
}

export default function PressureTraining() {
  const navigate = useNavigate();

  const [isStarting, setIsStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [history, setHistory] = useState<PressureSummary[]>([]);
  const [historyLoaded, setHistoryLoaded] = useState(false);

  useEffect(() => {
    let cancelled = false;
    pressureService
      .listPressureSessions(1, 10)
      .then((page) => {
        if (!cancelled) setHistory(page.sessions);
      })
      .catch(() => {
        /* history is a convenience; the setup form still works */
      })
      .finally(() => {
        if (!cancelled) setHistoryLoaded(true);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  async function handleStart(config: PressureConfig) {
    setIsStarting(true);
    setError(null);
    try {
      const result = await pressureService.startPressureSession(config);
      navigate(`/pressure-training/${result.session_id}`);
    } catch (err) {
      setError(getApiErrorMessage(err, "Couldn't start pressure training. Please try again."));
      setIsStarting(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <h1 className="font-display text-xl font-semibold text-text-primary">Pressure Training</h1>
        <p className="mt-1 text-sm text-text-secondary">
          Practice interview and communication situations under increasing pressure — time limits, unexpected
          follow-ups, topic switches, and occasional interruptions. This is a training tool, not a diagnostic
          one: it never assesses anxiety or any mental-health condition.
        </p>
      </div>

      <PressureSetup onStart={handleStart} isStarting={isStarting} error={error} />

      <section aria-label="Your pressure training sessions" className="space-y-2">
        <h2 className="text-sm font-semibold text-text-primary">Your Sessions</h2>
        {!historyLoaded ? (
          <p className="text-sm text-text-muted">Loading…</p>
        ) : history.length === 0 ? (
          <Card>
            <CardContent className="py-4 text-sm text-text-muted">
              No pressure training sessions yet. Start one above.
            </CardContent>
          </Card>
        ) : (
          <ul className="space-y-2">
            {history.map((item) => (
              <HistoryRow key={item.session_id} item={item} />
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
