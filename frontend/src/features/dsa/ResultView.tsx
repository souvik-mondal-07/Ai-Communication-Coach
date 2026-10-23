import { useState } from "react";
import { Link } from "react-router-dom";
import { Check, Flag, MinusCircle, X } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ProgressBar } from "@/components/ui/progress";
import { accuracyTone, answeredCount, CODING_TYPE_LABELS, DIFFICULTY_LABELS, FORMAT_LABELS, formatDuration, MODE_LABELS } from "@/features/dsa/dsaMeta";
import { CodeBlock } from "@/features/dsa/CodeBlock";
import { ComplexityPanel } from "@/features/dsa/ComplexityPanel";
import { TestTable } from "@/features/dsa/TestTable";
import { TraceViewer } from "@/features/dsa/TraceViewer";
import { cn } from "@/lib/utils";
import type { DsaResult, ResultQuestion, SelfVerdict } from "@/types/dsa";

const LETTERS = ["A", "B", "C", "D"];
type Filter = "all" | "incorrect" | "unanswered" | "marked" | "coding";
const TONE_COLOR = { success: "var(--color-success)", warn: "var(--color-warn)", danger: "var(--color-danger)" } as const;
const VERDICTS: { id: SelfVerdict; label: string }[] = [{ id: "passed", label: "I think it passes" }, { id: "partial", label: "Partly" }, { id: "failed", label: "It fails" }];

function Tile({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="rounded-[var(--radius-panel)] border border-border bg-surface px-4 py-3">
      <dt className="text-xs text-text-muted">{label}</dt>
      <dd className="mt-0.5 text-xl font-semibold tabular-nums text-text-primary">{value}</dd>
      {hint && <dd className="text-xs text-text-muted">{hint}</dd>}
    </div>
  );
}

function McqReview({ q }: { q: ResultQuestion }) {
  return (
    <ul className="grid gap-1.5">
      {q.options.map((o, i) => {
        const correct = i === q.correct_index;
        const picked = i === q.selected_index;
        return (
          <li key={i} className={cn("flex items-start gap-2 rounded-[var(--radius-panel)] border px-3 py-2 text-sm", correct ? "border-success bg-success/10" : picked ? "border-danger bg-danger/10" : "border-border")}>
            <span className="font-semibold text-text-secondary" aria-hidden="true">{LETTERS[i]}.</span>
            <span className="min-w-0 flex-1 break-words text-text-primary">{o}</span>
            {correct && <span className="text-xs font-medium text-success">Correct answer</span>}
            {picked && !correct && <span className="text-xs font-medium text-danger">Your answer</span>}
            {picked && correct && <span className="text-xs font-medium text-success">· You chose this</span>}
          </li>
        );
      })}
    </ul>
  );
}

function CodeReview({ q, onAssess }: { q: ResultQuestion; onAssess?: (verdict: SelfVerdict) => void }) {
  return (
    <div className="space-y-3">
      {q.execution_note && <p className="rounded-[var(--radius-panel)] border border-warn/40 bg-warn/10 px-3 py-2 text-sm text-text-primary">{q.execution_note}</p>}
      <div className="space-y-1">
        <h4 className="text-xs font-semibold text-text-primary">Your submitted code</h4>
        {q.code_answer ? <CodeBlock code={q.code_answer} label="Your submitted code" /> : <p className="text-sm text-text-muted">You did not submit code for this question.</p>}
      </div>
      {q.reference_solution && <div className="space-y-1"><h4 className="text-xs font-semibold text-text-primary">Reference solution</h4><CodeBlock code={q.reference_solution} label="Reference solution" /></div>}
      {q.test_cases && <div className="space-y-1"><h4 className="text-xs font-semibold text-text-primary">Test cases (including those that were hidden)</h4><TestTable tests={q.test_cases} caption="All test cases" /></div>}
      {q.code_answer && (
        <div role="group" aria-label="Your own assessment" className="space-y-1.5">
          <p className="text-xs text-text-secondary">After tracing your code through the test cases by hand, record how you think it did. This is your own verdict: it is saved for your reference and does not change your score.</p>
          <div className="flex flex-wrap gap-1.5">
            {VERDICTS.map((v) => (
              <Button key={v.id} type="button" size="sm" variant={q.self_assessment === v.id ? "primary" : "secondary"} aria-pressed={q.self_assessment === v.id} onClick={() => onAssess?.(v.id)} disabled={!onAssess}>{v.label}</Button>
            ))}
          </div>
          {q.self_assessment && <p className="text-xs text-text-muted" role="status">Self-assessed: {VERDICTS.find((v) => v.id === q.self_assessment)?.label}.</p>}
        </div>
      )}
    </div>
  );
}

function ReviewItem({ q, number, onAssess }: { q: ResultQuestion; number: number; onAssess?: (qid: string, verdict: SelfVerdict) => void }) {
  const Icon = q.outcome === "correct" ? Check : q.outcome === "incorrect" ? X : MinusCircle;
  const tone = q.outcome === "correct" ? "text-success" : q.outcome === "incorrect" ? "text-danger" : "text-text-muted";
  const word = { correct: "Correct", incorrect: "Incorrect", unanswered: "Not answered", ungraded: "Not auto-graded" }[q.outcome];
  return (
    <li className="space-y-3 rounded-[var(--radius-card)] border border-border bg-surface p-4">
      <div className="flex flex-wrap items-center gap-2 text-xs">
        <span className="font-medium text-text-primary">Question {number}</span>
        <span className={cn("inline-flex items-center gap-1 font-medium", tone)}><Icon size={14} aria-hidden="true" />{word}</span>
        <Badge tone="neutral">{DIFFICULTY_LABELS[q.difficulty]}</Badge>
        <Badge tone="neutral">{q.coding_type ? CODING_TYPE_LABELS[q.coding_type] : FORMAT_LABELS[q.format]}</Badge>
        {q.marked_for_review && <Badge tone="warn"><Flag size={11} aria-hidden="true" /> Marked</Badge>}
      </div>
      <p className="whitespace-pre-line text-sm leading-relaxed text-text-primary">{q.statement}</p>
      {q.code && q.interaction === "mcq" && <CodeBlock code={q.code} label="Code for this question" />}
      {q.interaction === "mcq" ? <McqReview q={q} /> : <CodeReview q={q} onAssess={onAssess ? (v) => onAssess(q.question_id, v) : undefined} />}
      <div className="rounded-[var(--radius-panel)] bg-surface-raised px-3 py-2.5 text-sm"><p className="text-text-secondary">{q.explanation}</p></div>
      {q.trace && <TraceViewer steps={q.trace} />}
      <ComplexityPanel complexity={q.complexity} />
    </li>
  );
}

interface Props {
  result: DsaResult;
  practiceHref?: string;
  onAssess?: (questionId: string, verdict: SelfVerdict) => void;
}

export function ResultView({ result, practiceHref = "/dsa", onAssess }: Props) {
  const [filter, setFilter] = useState<Filter>("all");
  const shown = result.questions.map((q, i) => ({ q, n: i + 1 })).filter(({ q }) =>
    filter === "all" ? true : filter === "marked" ? q.marked_for_review : filter === "coding" ? q.interaction === "code" : q.outcome === filter);
  const scored = result.graded_questions > 0;
  const tone = accuracyTone(result.accuracy);
  const filters: { id: Filter; label: string; count: number }[] = [
    { id: "all", label: "All", count: result.questions.length },
    { id: "incorrect", label: "Incorrect", count: result.incorrect },
    { id: "unanswered", label: "Unanswered", count: result.unanswered },
    { id: "marked", label: "Marked", count: result.questions.filter((q) => q.marked_for_review).length },
    ...(result.ungraded_questions > 0 ? [{ id: "coding" as Filter, label: "Coding", count: result.ungraded_questions }] : []),
  ];

  return (
    <div className="space-y-6">
      {result.auto_submitted && (
        <p role="status" className="rounded-[var(--radius-panel)] border border-warn/40 bg-warn/10 px-4 py-2.5 text-sm text-text-primary">
          Time ran out, so this session was submitted automatically with the answers you had saved.
        </p>
      )}
      <section aria-labelledby="score-heading" className="space-y-3">
        <h2 id="score-heading" className="text-sm font-semibold text-text-primary">{MODE_LABELS[result.mode]} · Result</h2>
        <dl className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <Tile label="Questions" value={`${result.total_questions} total`} hint={`${result.graded_questions} auto-graded${result.ungraded_questions ? ` · ${result.ungraded_questions} coding` : ""}`} />
          <Tile label="Score" value={scored ? `${result.score} / ${result.graded_questions}` : "—"} hint={scored ? `${result.accuracy}% accuracy` : "No auto-graded questions"} />
          <Tile label="Correct" value={String(result.correct)} />
          <Tile label="Incorrect" value={String(result.incorrect)} />
          <Tile label="Unanswered" value={String(result.unanswered)} />
          <Tile label="With an answer" value={String(answeredCount(result))} hint="saved option or code" />
          <Tile label="Time taken" value={formatDuration(result.time_taken_seconds)} hint="Measured by the server" />
          <Tile label="Average per question" value={`${result.average_seconds_per_question}s`} />
        </dl>
        {scored && <ProgressBar value={result.accuracy} label={`Accuracy ${result.accuracy}%`} color={TONE_COLOR[tone]} />}
        <p className="text-xs text-text-muted">{result.scoring_policy}</p>
      </section>

      {result.topic_performance.length > 0 && (
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
      )}

      <Card>
        <CardHeader><CardTitle>Recommended for revision</CardTitle></CardHeader>
        <CardContent>
          {result.revision_topics.length === 0 ? (
            <p className="text-sm text-text-secondary">{scored ? "Nothing to flag: every scored topic in this session was at or above 70%." : "Coding-only sessions are not scored, so no revision topics are flagged. Compare each answer with its reference solution below."}</p>
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

      {result.complexity_summary.length > 0 && (
        <Card>
          <CardHeader><CardTitle>Complexity summary</CardTitle></CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[30rem] text-left text-xs">
                <caption className="sr-only">Complexity of the algorithms and snippets in this session</caption>
                <thead className="text-text-muted"><tr><th scope="col" className="py-1.5 pr-3 font-medium">Subtopic</th><th scope="col" className="py-1.5 pr-3 font-medium">Time</th><th scope="col" className="py-1.5 font-medium">Space</th></tr></thead>
                <tbody className="divide-y divide-border">
                  {result.complexity_summary.map((c) => (
                    <tr key={c.question_id}><td className="py-1.5 pr-3 text-text-primary">{c.subtopic_title}</td><td className="py-1.5 pr-3 font-mono text-text-primary">{c.complexity.time ?? "—"}</td><td className="py-1.5 font-mono text-text-primary">{c.complexity.space ?? "—"}</td></tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}

      <section aria-labelledby="review-heading" className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 id="review-heading" className="text-sm font-semibold text-text-primary">Answers, traces and explanations</h2>
          <div role="group" aria-label="Filter questions" className="flex flex-wrap gap-1.5">
            {filters.map((f) => (
              <button key={f.id} type="button" aria-pressed={filter === f.id} onClick={() => setFilter(f.id)}
                className={cn("rounded-full border px-3 py-1 text-xs", filter === f.id ? "border-signal bg-signal/10 text-text-primary" : "border-border text-text-secondary hover:border-border-input")}>
                {f.label} ({f.count})
              </button>
            ))}
          </div>
        </div>
        {shown.length === 0 ? <p className="text-sm text-text-muted">No questions in this view.</p> : <ol className="space-y-3">{shown.map(({ q, n }) => <ReviewItem key={q.question_id} q={q} number={n} onAssess={onAssess} />)}</ol>}
      </section>
    </div>
  );
}
