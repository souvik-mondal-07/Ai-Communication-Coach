import { useState } from "react";
import { Link } from "react-router-dom";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ProgressBar } from "@/components/ui/progress";
import { CodeBlock } from "@/features/dsa/CodeBlock";
import { accuracyTone, DIFFICULTY_LABELS, formatDuration, MODE_LABELS } from "@/features/python-practice/pythonPracticeMeta";
import { cn } from "@/lib/utils";
import type { PyResult, Outcome, ResultQuestion } from "@/types/pythonPractice";

const TONE_COLOR = { success: "var(--color-success)", warn: "var(--color-warn)", danger: "var(--color-danger)" } as const;
const OUTCOME: Record<Outcome, { label: string; tone: "success" | "danger" | "neutral" }> = {
  correct: { label: "Correct", tone: "success" }, incorrect: { label: "Incorrect", tone: "danger" }, unanswered: { label: "Not answered", tone: "neutral" },
};
const LETTERS = ["A", "B", "C", "D"];

function ReviewItem({ q, index }: { q: ResultQuestion; index: number }) {
  return (
    <li className="space-y-3 rounded-[var(--radius-card)] border border-border bg-surface p-4">
      <div className="flex flex-wrap items-center gap-2 text-xs">
        <span className="font-medium text-text-primary">Question {index + 1}</span>
        <Badge tone={OUTCOME[q.outcome].tone}>{OUTCOME[q.outcome].label}</Badge>
        <Badge tone="neutral">{DIFFICULTY_LABELS[q.difficulty]}</Badge>
        {q.python_version && <Badge tone="violet">Python {q.python_version}</Badge>}
        {q.hints_used > 0 && <span className="text-text-muted">{q.hints_used} hint{q.hints_used === 1 ? "" : "s"} used</span>}
        {q.code_checks > 0 && <span className="text-text-muted">{q.code_checks} submission{q.code_checks === 1 ? "" : "s"}</span>}
      </div>
      <p className="whitespace-pre-line text-sm text-text-primary">{q.statement}</p>
      {q.code && <CodeBlock code={q.code} label="Code for this question" />}

      {q.interaction === "mcq" && (
        <ol className="grid gap-1.5" aria-label="Options">
          {q.options.map((o, i) => (
            <li key={i} className={cn("flex gap-2 rounded-[var(--radius-panel)] border px-3 py-2 text-sm", i === q.correct_index ? "border-success bg-success/10" : i === q.selected_index ? "border-danger bg-danger/10" : "border-border")}>
              <span className="font-semibold text-text-secondary" aria-hidden="true">{LETTERS[i]}</span>
              <span className="min-w-0 flex-1 break-words text-text-primary">{o}</span>
              {i === q.correct_index && <span className="text-xs font-medium text-success">Correct answer</span>}
              {i === q.selected_index && i !== q.correct_index && <span className="text-xs font-medium text-danger">Your answer</span>}
            </li>
          ))}
        </ol>
      )}
      {q.interaction === "short" && (
        <dl className="space-y-1 text-sm">
          <div className="flex gap-2"><dt className="text-text-muted">Your answer:</dt><dd className="font-mono text-text-primary">{q.text_answer || "(none)"}</dd></div>
          <div className="flex gap-2"><dt className="text-text-muted">Correct answer:</dt><dd className="font-mono text-success">{q.correct_answer}</dd></div>
        </dl>
      )}
      {q.interaction === "code" && (
        <div className="space-y-3">
          {q.title && <p className="text-sm font-medium text-text-primary">{q.title}</p>}
          <div className="space-y-1"><h4 className="text-xs font-semibold uppercase tracking-wide text-text-muted">Your code</h4>{q.code_answer ? <CodeBlock code={q.code_answer} label="Your code" /> : <p className="text-sm text-text-muted">(no code submitted)</p>}</div>
          {q.note && <p className="text-xs text-warn">{q.note}</p>}
          {q.tests_total > 0 && <p className="text-sm text-text-secondary">Tests passed: <span className="font-semibold tabular-nums text-text-primary">{q.tests_passed} of {q.tests_total}</span>{q.verdict ? ` (${q.verdict.message})` : ""}</p>}
          <div className="space-y-1"><h4 className="text-xs font-semibold uppercase tracking-wide text-text-muted">Reference solution</h4><CodeBlock code={q.reference_source ?? ""} label="Reference solution" /></div>
          <p className="text-sm text-text-secondary"><span className="font-medium text-text-primary">Complexity: </span>time {q.time_complexity}, space {q.space_complexity}</p>
        </div>
      )}
      <p className="text-sm text-text-secondary"><span className="font-medium text-text-primary">Explanation: </span>{q.explanation}</p>
    </li>
  );
}

/** The scored review: summary, per-topic accuracy, revision suggestions and every question with its explanation (and, for coding questions, your code, test results and the reference solution). */
export function ResultView({ result }: { result: PyResult }) {
  const [filter, setFilter] = useState<"all" | "incorrect" | "unanswered">("all");
  const shown = result.questions.map((q, i) => ({ q, i })).filter(({ q }) => filter === "all" || q.outcome === filter);
  return (
    <div className="space-y-6">
      <Card><CardContent className="space-y-4 py-5">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="text-xs text-text-muted">{MODE_LABELS[result.mode]}{result.auto_submitted ? " · submitted automatically when time ran out" : ""}</p>
            <p className="font-display text-3xl font-semibold tabular-nums text-text-primary" aria-label={`Score ${result.score} out of ${result.total_questions}`}>{result.score} / {result.total_questions}</p>
          </div>
          <Badge tone={accuracyTone(result.accuracy)}>{result.accuracy}% accuracy</Badge>
        </div>
        <ProgressBar value={result.accuracy} label="Accuracy" color={TONE_COLOR[accuracyTone(result.accuracy)]} />
        <dl className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
          {[["Correct", result.correct], ["Incorrect", result.incorrect], ["Not answered", result.unanswered], ["Time taken", formatDuration(result.time_taken_seconds)]].map(([k, v]) => (
            <div key={String(k)} className="rounded-[var(--radius-panel)] bg-surface-raised px-3 py-2"><dt className="text-xs text-text-muted">{k}</dt><dd className="font-semibold tabular-nums text-text-primary">{v}</dd></div>
          ))}
        </dl>
        <p className="text-xs text-text-muted">{result.scoring_policy}</p>
      </CardContent></Card>

      {result.revision_topics.length > 0 && (
        <Card><CardHeader><CardTitle>Topics to revise</CardTitle></CardHeader><CardContent>
          <ul className="space-y-1.5 text-sm">
            {result.revision_topics.map((t) => (
              <li key={t.topic_id} className="flex items-center justify-between gap-2"><span className="text-text-primary">{t.topic_title} <span className="text-text-muted">({t.accuracy}%)</span></span>
                <Link to={`/python-practice?mode=topic&topic=${encodeURIComponent(t.topic_id)}`} className="text-xs text-link underline-offset-2 hover:underline" aria-label={`Practise ${t.topic_title}`}>Practise</Link></li>
            ))}
          </ul>
        </CardContent></Card>
      )}

      <Card><CardHeader><CardTitle>Performance by topic</CardTitle></CardHeader><CardContent className="space-y-3">
        {result.topic_performance.map((t) => (
          <div key={t.topic_id} className="space-y-1">
            <div className="flex justify-between gap-2 text-sm"><span className="text-text-primary">{t.topic_title}</span><span className="text-xs tabular-nums text-text-muted">{t.correct}/{t.total} · {t.accuracy}%</span></div>
            <ProgressBar value={t.accuracy} label={`${t.topic_title} accuracy`} color={TONE_COLOR[accuracyTone(t.accuracy)]} />
          </div>
        ))}
      </CardContent></Card>

      <section aria-labelledby="review-title" className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 id="review-title" className="font-display text-base font-semibold text-text-primary">Question review</h2>
          <div role="radiogroup" aria-label="Filter questions" className="flex gap-1.5">
            {(["all", "incorrect", "unanswered"] as const).map((f) => (
              <button key={f} type="button" role="radio" aria-checked={filter === f} onClick={() => setFilter(f)}
                className={cn("rounded-full border px-3 py-1 text-xs", filter === f ? "border-signal bg-signal/10 text-text-primary" : "border-border text-text-secondary hover:border-border-input")}>
                {f === "all" ? `All (${result.questions.length})` : f === "incorrect" ? `Incorrect (${result.incorrect})` : `Not answered (${result.unanswered})`}
              </button>
            ))}
          </div>
        </div>
        {shown.length === 0 ? <p className="text-sm text-text-muted">No questions in this view.</p> : <ol className="space-y-3">{shown.map(({ q, i }) => <ReviewItem key={q.question_id} q={q} index={i} />)}</ol>}
      </section>
    </div>
  );
}
