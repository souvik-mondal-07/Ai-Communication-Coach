import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { Card, CardContent } from "@/components/ui/card";
import { InterviewSetup } from "@/features/interview/InterviewSetup";
import * as interviewService from "@/services/interviewService";
import { parseServerDate } from "@/hooks/useInterview";
import { getApiErrorMessage } from "@/utils/apiError";
import {
  INTERVIEW_DIFFICULTY_LABELS,
  INTERVIEW_TYPE_LABELS,
  type InterviewConfig,
  type InterviewSummary,
} from "@/types/interview";

const STATUS_LABELS: Record<InterviewSummary["status"], string> = {
  in_progress: "In progress",
  completed: "Completed",
  abandoned: "Ended early",
};

function HistoryRow({ item }: { item: InterviewSummary }) {
  const date = new Date(parseServerDate(item.started_at)).toLocaleDateString();
  return (
    <li>
      <Link
        to={`/interview/${item.session_id}`}
        className="flex items-center justify-between gap-3 rounded-[var(--radius-panel)] border border-border px-3 py-2.5 text-sm transition-colors hover:border-border-strong"
      >
        <span className="text-text-primary">
          {INTERVIEW_TYPE_LABELS[item.interview_type]} · {INTERVIEW_DIFFICULTY_LABELS[item.difficulty]}
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

export default function Interview() {
  const navigate = useNavigate();
  const location = useLocation();
  // "Practice Again" passes the previous configuration along.
  const preset = (location.state as { preset?: Partial<InterviewConfig> } | null)?.preset;

  const [isStarting, setIsStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [history, setHistory] = useState<InterviewSummary[]>([]);
  const [historyLoaded, setHistoryLoaded] = useState(false);

  useEffect(() => {
    let cancelled = false;
    interviewService
      .listInterviews(1, 10)
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

  async function handleStart(config: InterviewConfig) {
    setIsStarting(true);
    setError(null);
    try {
      const result = await interviewService.startInterview(config);
      navigate(`/interview/${result.session_id}`);
    } catch (err) {
      setError(getApiErrorMessage(err, "Couldn't start the interview. Please try again."));
      setIsStarting(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <h1 className="font-display text-xl font-semibold text-text-primary">Interview</h1>
        <p className="mt-1 text-sm text-text-secondary">
          Practise a realistic cybersecurity job interview. The interviewer asks the questions, follows up on
          your answers, and you get detailed technical and communication feedback at the end.
        </p>
      </div>

      <InterviewSetup onStart={handleStart} isStarting={isStarting} error={error} initial={preset} />

      <section aria-label="Your interviews" className="space-y-2">
        <h2 className="text-sm font-semibold text-text-primary">Your interviews</h2>
        {!historyLoaded ? (
          <p className="text-sm text-text-muted">Loading…</p>
        ) : history.length === 0 ? (
          <Card>
            <CardContent className="py-4 text-sm text-text-muted">
              No interviews yet. Start one above.
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
