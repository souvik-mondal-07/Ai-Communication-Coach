import { useRef } from "react";
import { Eye, Play, RotateCcw, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { CodeBlock } from "@/features/dsa/CodeBlock";
import { Hints, QuestionMeta } from "@/features/dbms-sql/QuestionCard";
import { ResultTable } from "@/features/dbms-sql/ResultTable";
import { MAX_SQL_CHARS } from "@/features/dbms-sql/dbmsSqlMeta";
import { cn } from "@/lib/utils";
import type { CheckOutcome, RunResult, SessionQuestion } from "@/types/dbmsSql";

interface EditorProps {
  value: string;
  onChange: (value: string) => void;
  onRun: () => void;
  disabled?: boolean;
  label?: string;
  id: string;
}

/**
 * Plain accessible SQL editor. The project has no code-editor library, so this is a monospaced textarea (no syntax highlighting).
 * Tab keeps its normal meaning so keyboard users are never trapped; Ctrl/Cmd+Enter runs the query.
 */
export function SqlEditor({ value, onChange, onRun, disabled, label = "SQL query", id }: EditorProps) {
  return (
    <div className="space-y-1">
      <label htmlFor={id} className="block text-sm font-medium text-text-primary">{label}</label>
      <textarea id={id} value={value} disabled={disabled} rows={7} spellCheck={false} autoCapitalize="off" autoCorrect="off" maxLength={MAX_SQL_CHARS}
        aria-describedby={`${id}-hint`} onChange={(e) => onChange(e.target.value)}
        onKeyDown={(e) => { if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) { e.preventDefault(); onRun(); } }}
        className="w-full resize-y rounded-[var(--radius-panel)] border border-border-input bg-surface p-3 font-mono text-sm leading-relaxed text-text-primary placeholder:text-text-muted disabled:opacity-70"
        placeholder="SELECT ... FROM ... WHERE ..." />
      <p id={`${id}-hint`} className="flex flex-wrap justify-between gap-2 text-[11px] text-text-muted">
        <span>Ctrl/Cmd + Enter runs the query. Read-only SQL only; the sandbox allows one SELECT or WITH statement.</span>
        <span className="tabular-nums">{value.length}/{MAX_SQL_CHARS}</span>
      </p>
    </div>
  );
}

/** What the last run produced: rows, or a plain-language reason it was refused or failed. */
export function RunOutput({ run }: { run: RunResult }) {
  if (!run.ok) {
    return (
      <div role="alert" className="rounded-[var(--radius-panel)] border border-danger/40 bg-danger/10 px-3 py-2 text-sm text-danger">
        <p className="font-medium">{run.error?.kind === "not_allowed" ? "Not allowed in the practice sandbox" : run.error?.kind === "timeout" ? "Stopped: too much work" : "The query did not run"}</p>
        <p className="mt-0.5 text-text-primary">{run.error?.message ?? "The query could not be executed."}</p>
      </div>
    );
  }
  return <ResultTable caption="Your query result" columns={run.columns} rows={run.rows} rowCount={run.row_count} truncated={run.truncated} />;
}

interface Props {
  question: SessionQuestion;
  index: number;
  total: number;
  draft: string;
  run?: RunResult;
  check?: CheckOutcome;
  busy?: "run" | "check" | "reveal" | "hint";
  canCheck: boolean;
  onDraft: (sql: string) => void;
  onRun: () => void;
  onCheck: () => void;
  onReveal: () => void;
  onHint: () => void;
}

/**
 * The SQL exercise runner: statement, editor, Run (preview only), Check (graded by the server, practice sessions), hints, and a
 * reference solution after solving or giving up. Expected rows and the reference query are only ever shown once the server sends them.
 */
export function SqlWorkbench({ question, index, total, draft, run, check, busy, canCheck, onDraft, onRun, onCheck, onReveal, onHint }: Props) {
  const spec = question.sql!;
  const fb = question.feedback && question.feedback.kind === "sql" ? question.feedback : null;
  const locked = question.locked;
  const resetRef = useRef(question.sql?.starter ?? "");
  const verdict = check?.verdict ?? question.last_check;
  return (
    <section aria-labelledby="question-heading" className="space-y-4">
      <QuestionMeta question={question} index={index} total={total} />
      <p className="whitespace-pre-line text-base leading-relaxed text-text-primary">{question.statement}</p>
      <p className="text-xs text-text-secondary">
        Return column{spec.expected_columns.length === 1 ? "" : "s"}: <span className="font-mono text-text-primary">{spec.expected_columns.join(", ")}</span>
        {" · "}{spec.ordered ? "row order matters" : "row order does not matter"}
        {spec.check_column_names ? " · column names must match (use AS)" : ""}
      </p>

      <SqlEditor id={`sql-${question.question_id}`} value={draft} onChange={onDraft} onRun={onRun} disabled={locked} />

      <div className="flex flex-wrap items-center gap-2">
        <Button type="button" size="sm" variant="secondary" onClick={onRun} loading={busy === "run"} disabled={locked && !draft.trim()}><Play size={14} aria-hidden="true" /> Run query</Button>
        {canCheck && !locked && <Button type="button" size="sm" onClick={onCheck} loading={busy === "check"} disabled={!draft.trim()}><ShieldCheck size={14} aria-hidden="true" /> Check answer</Button>}
        {spec.starter && !locked && <Button type="button" size="sm" variant="ghost" onClick={() => onDraft(resetRef.current)}><RotateCcw size={14} aria-hidden="true" /> Reset to starter</Button>}
        {canCheck && !locked && <Button type="button" size="sm" variant="ghost" onClick={onReveal} loading={busy === "reveal"}><Eye size={14} aria-hidden="true" /> Show solution</Button>}
        {question.checks > 0 && <span className="text-xs text-text-muted" aria-live="polite">{question.checks} check{question.checks === 1 ? "" : "s"}</span>}
      </div>
      {canCheck && !locked && <p className="text-xs text-text-muted">Showing the solution before you solve it scores this question 0.</p>}
      {!canCheck && <p className="text-xs text-text-muted">Your query is saved and graded when you submit. Use Run query to test it on the sample data.</p>}

      {run && <div className="space-y-1.5"><h3 className="text-xs font-semibold uppercase tracking-wide text-text-muted">Your output</h3><RunOutput run={run} /></div>}

      {verdict && !fb && (
        <div role="status" className="space-y-1.5 rounded-[var(--radius-panel)] border border-warn/40 bg-warn/10 px-4 py-3 text-sm">
          <p className="font-medium text-text-primary">Not matching yet</p>
          <ul className="list-disc space-y-0.5 pl-5 text-text-secondary">{verdict.messages.map((m, i) => <li key={i}>{m}</li>)}</ul>
          {check?.comparison && (
            <div className="grid gap-3 pt-1 md:grid-cols-2">
              <div><h4 className="mb-1 text-xs font-semibold text-text-muted">Expected</h4><ResultTable caption="Expected result" columns={check.comparison.expected.columns} rows={check.comparison.expected.rows} rowCount={check.comparison.expected.row_count} truncated={check.comparison.expected.truncated} /></div>
              <div><h4 className="mb-1 text-xs font-semibold text-text-muted">Yours</h4><ResultTable caption="Your result" columns={check.comparison.actual.columns} rows={check.comparison.actual.rows} rowCount={check.comparison.actual.row_count} truncated={check.comparison.actual.truncated} /></div>
            </div>
          )}
        </div>
      )}

      {!locked && <Hints key={question.question_id} question={question} busy={busy === "hint"} onRequest={onHint} />}

      {fb && (
        <div role="status" className="space-y-3 rounded-[var(--radius-panel)] border border-border bg-surface-raised px-4 py-3 text-sm">
          <p className={cn("font-medium", fb.is_correct ? "text-success" : "text-danger")}>{fb.is_correct ? "Correct: your result matches" : fb.revealed ? "Solution revealed (this question scores 0)" : "Not correct"}</p>
          <div className="space-y-1"><h3 className="text-xs font-semibold uppercase tracking-wide text-text-muted">Reference solution</h3><CodeBlock code={fb.reference_sql} label="Reference solution" /></div>
          <div className="space-y-1"><h3 className="text-xs font-semibold uppercase tracking-wide text-text-muted">Expected result</h3><ResultTable caption="Expected result" columns={fb.expected.columns} rows={fb.expected.rows} rowCount={fb.expected.row_count} truncated={fb.expected.truncated} /></div>
          <p className="text-text-secondary"><span className="font-medium text-text-primary">Why it works: </span>{fb.explanation}</p>
        </div>
      )}
    </section>
  );
}
