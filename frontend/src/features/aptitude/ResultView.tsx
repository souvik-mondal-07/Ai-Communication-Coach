import { useState } from "react";
import { Link } from "react-router-dom";
import { Check, Flag, MinusCircle, X } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ProgressBar } from "@/components/ui/progress";
import { accuracyTone, DIFFICULTY_LABELS, formatDuration, MODE_LABELS } from "@/features/aptitude/aptitudeMeta";
import { DataView } from "@/features/aptitude/DataView";
import { cn } from "@/lib/utils";
import type { AptitudeResult, ResultQuestion } from "@/types/aptitude";

const LETTERS = ["A", "B", "C", "D"];
type Filter = "all" | "incorrect" | "unanswered" | "marked";
const TONE_COLOR = { success: "var(--color-success)", warn: "var(--color-warn)", danger: "var(--color-danger)" } as const;

function Tile({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="rounded-[var(--radius-panel)] border border-border bg-surface px-4 py-3">
      <dt className="text-xs text-text-muted">{label}</dt>
      <dd className="mt-0.5 text-xl font-semibold tabular-nums text-text-primary">{value}</dd>
      {hint && <dd className="text-xs text-text-muted">{hint}</dd>}
    </div>
  );
}

function ReviewItem({ q, number }: { q: ResultQuestion; number: number }) {
  const Icon = q.outcome === "correct" ? Check : q.outcome === "incorrect" ? X : MinusCircle;
  const tone = q.outcome === "correct" ? "text-success" : q.outcome === "incorrect" ? "text-danger" : "text-text-muted";
  const word = q.outcome === "correct" ? "Correct" : q.outcome === "incorrect" ? "Incorrect" : "Not answered";
  return (
    <li className="space-y-3 rounded-[var(--radius-card)] border border-border bg-surface p-4">
      <div className="flex flex-wrap items-center gap-2 text-xs">
        <span className="font-medium text-text-primary">Question {number}</span>
        <span className={cn("inline-flex items-center gap-1 font-medium", tone)}><Icon size={14} aria-hidden="true" />{word}</span>
        <Badge tone="neutral">{DIFFICULTY_LABELS[q.difficulty]}</Badge>
        {q.marked_for_review && <Badge tone="warn"><Flag size={11} aria-hidden="true" /> Marked</Badge>}
      </div>
      <p className="whitespace-pre-line text-sm leading-relaxed text-text-primary">{q.statement}</p>
      {q.data && <DataView data={q.data} />}
      <ul className="grid gap-1.5">
        {q.options.map((o, i) => {
          const correct = i === q.correct_index;
          const picked = i === q.selected_index;
          return (
            <li key={i} className={cn("flex items-start gap-2 rounded-[var(--radius-panel)] border px-3 py-2 text-sm", correct ? "border-success bg-success/10" : picked ? "border-danger bg-danger/10" : "border-border")}>
              <span className="font-semibold text-text-secondary" aria-hidden="true">{LETTERS[i]}.</span>
              <span className="min-w-0 flex-1 text-text-primary">{o}</span>
              {correct && <span className="text-xs font-medium text-success">Correct answer</span>}
              {picked && !correct && <span className="text-xs font-medium text-danger">Your answer</span>}
              {picked && correct && <span className="text-xs font-medium text-success">· You chose this</span>}
            </li>
          );
        })}
      </ul>
      <div className="rounded-[var(--radius-panel)] bg-surface-raised px-3 py-2.5 text-sm">
        <p className="text-text-secondary">{q.explanation}</p>
        {q.formula && <p className="mt-1.5 text-xs text-text-muted"><span className="font-medium text-text-secondary">Formula / shortcut:</span> {q.formula}</p>}
      </div>
    </li>
  );
}

export function ResultView({ result, practiceHref = "/aptitude" }: { result: AptitudeResult; practiceHref?: string }) {
  const [filter, setFilter] = useState<Filter>("all");
  const shown = result.questions.map((q, i) => ({ q, n: i + 1 })).filter(({ q }) =>
    filter === "all" ? true : filter === "marked" ? q.marked_for_review : q.outcome === filter);
  const tone = accuracyTone(result.accuracy);
  const filters: { id: Filter; label: string; count: number }[] = [
    { id: "all", label: "All", count: result.questions.length },
    { id: "incorrect", label: "Incorrect", count: result.incorrect },
    { id: "unanswered", label: "Unanswered", count: result.unanswered },
    { id: "marked", label: "Marked", count: result.questions.filter((q) => q.marked_for_review).length },
  ];

  return (
    <div className="space-y-6">
      {result.auto_submitted && (
        <p role="status" className="rounded-[var(--radius-panel)] border border-warn/40 bg-warn/10 px-4 py-2.5 text-sm text-text-primary">
          Time ran out, so this test was submitted automatically with the answers you had saved.
        </p>
      )}
      <section aria-labelledby="score-heading" className="space-y-3">
        <h2 id="score-heading" className="text-sm font-semibold text-text-primary">{MODE_LABELS[result.mode]} · Result</h2>
        <dl className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <Tile label="Score" value={`${result.score} / ${result.total_questions}`} hint={`${result.accuracy}% accuracy`} />
          <Tile label="Correct" value={String(result.correct)} />
          <Tile label="Incorrect" value={String(result.incorrect)} />
          <Tile label="Unanswered" value={String(result.unanswered)} />
          <Tile label="Time taken" value={formatDuration(result.time_taken_seconds)} hint="Measured by the server" />
          <Tile label="Average per question" value={`${result.average_seconds_per_question}s`} />
        </dl>
        <ProgressBar value={result.accuracy} label={`Accuracy ${result.accuracy}%`} color={TONE_COLOR[tone]} />
        <p className="text-xs text-text-muted">{result.scoring_policy}</p>
      </section>

      <Card>
        <CardHeader><CardTitle>Topic-wise performance</CardTitle></CardHeader>
        <CardContent className="space-y-3">
          {result.topic_performance.map((t) => (
            <div key={t.topic_id} className="space-y-1">
              <div className="flex flex-wrap justify-between gap-2 text-sm">
                <span className="text-text-primary">{t.topic_title}</span>
                <span className="text-xs text-text-muted tabular-nums">{t.correct}/{t.total} correct · {t.accuracy}%</span>
              </div>
              <ProgressBar value={t.accuracy} label={`${t.topic_title} accuracy`} color={TONE_COLOR[accuracyTone(t.accuracy)]} />
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Recommended for revision</CardTitle></CardHeader>
        <CardContent>
          {result.revision_topics.length === 0 ? (
            <p className="text-sm text-text-secondary">Nothing to flag: every topic in this session was at or above 70%.</p>
          ) : (
            <ul className="space-y-3">
              {result.revision_topics.map((t) => (
                <li key={t.topic_id} className="text-sm">
                  <p className="text-text-primary"><span className="font-medium">{t.topic_title}</span> <span className="text-text-muted">({t.accuracy}% in this session)</span></p>
                  <p className="mt-0.5 text-xs text-text-secondary">
                    Revisit: {t.subtopics.map((s, i) => (
                      <span key={s.subtopic_id}>{i > 0 && ", "}<Link className="text-link underline-offset-2 hover:underline" to={`${practiceHref}?mode=topic&subtopic=${encodeURIComponent(s.subtopic_id)}`}>{s.title}</Link></span>
                    ))}
                  </p>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      <section aria-labelledby="review-heading" className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 id="review-heading" className="text-sm font-semibold text-text-primary">Answers and explanations</h2>
          <div role="group" aria-label="Filter questions" className="flex flex-wrap gap-1.5">
            {filters.map((f) => (
              <button key={f.id} type="button" aria-pressed={filter === f.id} onClick={() => setFilter(f.id)}
                className={cn("rounded-full border px-3 py-1 text-xs", filter === f.id ? "border-signal bg-signal/10 text-text-primary" : "border-border text-text-secondary hover:border-border-input")}>
                {f.label} ({f.count})
              </button>
            ))}
          </div>
        </div>
        {shown.length === 0 ? <p className="text-sm text-text-muted">No questions in this view.</p> : <ol className="space-y-3">{shown.map(({ q, n }) => <ReviewItem key={q.question_id} q={q} number={n} />)}</ol>}
      </section>
    </div>
  );
}
