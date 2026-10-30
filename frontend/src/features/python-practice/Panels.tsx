import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ShieldAlert, ShieldCheck } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { EmptyState, ErrorState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { formatDuration, MODE_LABELS } from "@/features/python-practice/pythonPracticeMeta";
import * as svc from "@/services/pythonPracticeService";
import { usePythonPracticeStore } from "@/store/pythonPracticeStore";
import { getApiErrorMessage } from "@/utils/apiError";
import type { Coverage, RunnerStatus } from "@/types/pythonPractice";

/** Says plainly whether submitted code can run on this server, and why not when it cannot. Never claims more isolation than was verified. */
export function RunnerBanner({ runner }: { runner: RunnerStatus }) {
  return (
    <Card>
      <CardContent className="space-y-2 py-4 text-sm">
        <div className="flex flex-wrap items-center gap-2">
          {runner.available ? <ShieldCheck size={18} className="text-success" aria-hidden="true" /> : <ShieldAlert size={18} className="text-warn" aria-hidden="true" />}
          <h2 className="font-semibold text-text-primary">{runner.available ? "Code runner available" : "Code runner unavailable"}</h2>
          <Badge tone={runner.available ? "success" : "warn"}>{runner.available ? `Python ${runner.python_version}, isolated` : "Coding exercises are turned off"}</Badge>
        </div>
        {runner.available ? (
          <p className="text-text-secondary">Your code runs in an isolated process with no network, no file access to the application, and strict time ({runner.limits.cpu_seconds}s CPU), memory ({runner.limits.memory_mb} MB) and process limits. Isolation was verified on this server at startup.</p>
        ) : (
          <p className="text-text-secondary">{runner.reason} Theory, output-prediction, tracing and complexity questions still work; coding, debugging and completion exercises are hidden because they could not be graded.</p>
        )}
        {runner.available && (
          <details className="text-xs text-text-muted">
            <summary className="cursor-pointer text-text-secondary">How isolation works</summary>
            <ul className="mt-1 list-disc space-y-0.5 pl-5">{runner.layers.map((l) => <li key={l}>{l}</li>)}</ul>
          </details>
        )}
      </CardContent>
    </Card>
  );
}

/** The syllabus coverage matrix from the server: per-topic counts, exercise types, verification and honest gaps. */
export function CoveragePanel() {
  const [data, setData] = useState<Coverage | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const ctl = new AbortController();
    svc.getCoverage(ctl.signal).then(setData).catch((e) => { if (!ctl.signal.aborted) setError(getApiErrorMessage(e, "Unable to load the coverage report.")); });
    return () => ctl.abort();
  }, [attempt]);
  if (error) return <ErrorState message={error} onRetry={() => { setError(null); setAttempt((n) => n + 1); }} />;
  if (!data) return <div role="status" aria-label="Loading coverage" className="space-y-2"><Skeleton className="h-16 w-full" /><Skeleton className="h-40 w-full" /></div>;
  return (
    <div className="space-y-3">
      <p className="text-sm text-text-secondary">
        {data.topics_implemented} of {data.topics_total} topics meet the minimum · {data.total_questions} questions: {data.machine_verified} machine-verified (executed or cross-checked), {data.manual_review} manual-review only.
      </p>
      {data.gaps.length > 0 ? <ul role="status" className="list-disc space-y-0.5 pl-5 text-sm text-warn">{data.gaps.map((g) => <li key={g}>{g}</li>)}</ul> : <p className="text-sm text-success">No topic is below the minimum question count.</p>}
      <div className="overflow-x-auto rounded-[var(--radius-panel)] border border-border">
        <table className="w-full min-w-[44rem] text-left text-xs">
          <caption className="sr-only">Syllabus coverage by topic</caption>
          <thead className="bg-surface-raised text-text-muted"><tr>{["Unit", "Topic", "Questions", "E / M / H", "Exercise types", "Verified"].map((h) => <th key={h} scope="col" className="px-3 py-1.5">{h}</th>)}</tr></thead>
          <tbody>{data.rows.map((r) => (
            <tr key={r.topic_id} className="border-t border-border align-top">
              <td className="px-3 py-1.5">{r.unit}</td><th scope="row" className="px-3 py-1.5 font-medium text-text-primary">{r.topic}</th><td className="px-3 py-1.5">{r.count}</td>
              <td className="px-3 py-1.5">{r.easy} / {r.medium} / {r.hard}</td><td className="px-3 py-1.5">{Object.entries(r.formats).map(([k, v]) => `${k} ${v}`).join(", ")}</td><td className="px-3 py-1.5">{r.machine_verified} of {r.count}</td>
            </tr>))}</tbody>
        </table>
      </div>
    </div>
  );
}

/** Earlier sessions from the server's own records. Nothing here is computed on the device. */
export function HistoryPanel() {
  const { history, historyStatus, historyError, loadHistory } = usePythonPracticeStore();
  useEffect(() => { void loadHistory(); }, [loadHistory]);
  if (historyStatus === "error") return <ErrorState message={historyError ?? "Unable to load history."} onRetry={() => void loadHistory()} />;
  if (historyStatus !== "ready" || !history) return <div role="status" aria-label="Loading history" className="space-y-2"><Skeleton className="h-14 w-full" /><Skeleton className="h-14 w-full" /></div>;
  if (history.items.length === 0) return <EmptyState title="No sessions yet" description="Sessions you start appear here with their score and time." />;
  return (
    <ul className="space-y-2" aria-label="Previous sessions">
      {history.items.map((h) => {
        const done = h.status === "completed";
        return (
          <li key={h.session_id} className="flex flex-wrap items-center justify-between gap-2 rounded-[var(--radius-panel)] border border-border bg-surface px-4 py-3 text-sm">
            <div>
              <p className="font-medium text-text-primary">{MODE_LABELS[h.mode]}</p>
              <p className="text-xs text-text-muted">{new Date(h.started_at).toLocaleString()} · {h.question_count} questions{h.time_taken_seconds !== null ? ` · ${formatDuration(h.time_taken_seconds)}` : ""}</p>
            </div>
            <div className="flex items-center gap-3">
              {done ? <span className="font-semibold text-text-primary">{h.score}/{h.question_count} · {h.accuracy}%</span> : <Badge tone="warn">In progress</Badge>}
              <Link className="text-link underline-offset-2 hover:underline" to={done ? `/python-practice/result/${h.session_id}` : `/python-practice/session/${h.session_id}`}>{done ? "View result" : "Resume"}</Link>
            </div>
          </li>
        );
      })}
    </ul>
  );
}
