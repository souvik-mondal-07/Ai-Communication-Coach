import { useRef } from "react";
import { AlertTriangle, CheckCircle2, Eye, Play, RotateCcw, Send, XCircle } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { CodeBlock } from "@/features/dsa/CodeBlock";
import { Hints, QuestionMeta } from "@/features/python-practice/QuestionCard";
import { MAX_CODE_CHARS } from "@/features/python-practice/pythonPracticeMeta";
import { cn } from "@/lib/utils";
import type { CheckOutcome, GradeResult, SessionQuestion, TestOutcome } from "@/types/pythonPractice";

interface Props {
  question: SessionQuestion;
  index: number;
  total: number;
  draft: string;
  run?: GradeResult;
  check?: CheckOutcome;
  busy?: "run" | "check" | "reveal" | "hint";
  /** True in practice sessions: submission checks, hints and the reference solution are allowed. False in a timed mock. */
  canCheck: boolean;
  onDraft: (code: string) => void;
  onRun: () => void;
  onCheck: () => void;
  onReveal: () => void;
  onHint: () => void;
}

const VERDICT_TONE: Record<string, "success" | "danger" | "warn"> = {
  accepted: "success", wrong_answer: "danger", runtime_error: "danger", timeout: "warn", compile_error: "danger", output_limit: "warn", runner_error: "warn",
};
const VERDICT_TITLE: Record<string, string> = {
  accepted: "Accepted", wrong_answer: "Wrong answer", runtime_error: "Runtime error", timeout: "Time limit exceeded", compile_error: "Could not compile or load", output_limit: "Too much output", runner_error: "Runner problem",
};
const STATUS_LABEL: Record<TestOutcome["status"], string> = { passed: "Passed", failed: "Failed", error: "Error", timeout: "Timed out", not_run: "Not run" };

function TestRow({ test }: { test: TestOutcome }) {
  return (
    <li className="rounded-[var(--radius-panel)] border border-border bg-surface px-3 py-2 text-sm">
      <div className="flex flex-wrap items-center gap-2">
        {test.passed ? <CheckCircle2 size={15} className="text-success" aria-hidden="true" /> : <XCircle size={15} className="text-danger" aria-hidden="true" />}
        <span className="font-medium text-text-primary">{test.label}</span>
        <Badge tone={test.passed ? "success" : "danger"}>{STATUS_LABEL[test.status]}</Badge>
        {!test.visible && <span className="text-xs text-text-muted">Hidden: details are not shown</span>}
        {test.ms !== null && test.visible && <span className="ml-auto text-xs text-text-muted">{test.ms} ms</span>}
      </div>
      {test.message && <pre className="mt-2 whitespace-pre-wrap break-words rounded bg-surface-raised p-2 font-mono text-xs text-text-secondary">{test.message}</pre>}
      {test.stdout && <pre aria-label="Printed output" className="mt-2 whitespace-pre-wrap break-words rounded bg-surface-raised p-2 font-mono text-xs text-text-secondary">{test.stdout}</pre>}
    </li>
  );
}

function Results({ result, label }: { result: GradeResult; label: string }) {
  const tone = VERDICT_TONE[result.verdict] ?? "warn";
  return (
    <div role="status" aria-label={label} className="space-y-2">
      <div className={cn("flex flex-wrap items-center gap-2 rounded-[var(--radius-panel)] border px-3 py-2 text-sm", tone === "success" ? "border-success/40 bg-success/10" : tone === "danger" ? "border-danger/40 bg-danger/10" : "border-warn/40 bg-warn/10")}>
        <span className="font-semibold text-text-primary">{VERDICT_TITLE[result.verdict] ?? result.verdict}</span>
        {result.verdict !== "runner_error" && <span className="text-text-secondary">{result.passed} of {result.total} tests passed</span>}
        <span className="text-text-secondary">{result.message}</span>
      </div>
      {result.setup_error && (
        <pre className="whitespace-pre-wrap break-words rounded-[var(--radius-panel)] border border-border bg-surface-raised p-3 font-mono text-xs text-text-secondary">
          {result.setup_error.type}: {result.setup_error.message}{result.setup_error.line ? ` (line ${result.setup_error.line})` : ""}
        </pre>
      )}
      {result.tests.length > 0 && <ul className="space-y-1.5" aria-label="Test results">{result.tests.map((t) => <TestRow key={t.id} test={t} />)}</ul>}
    </div>
  );
}

/**
 * The coding workspace. Plain textarea editor (no new dependency): Tab inserts four spaces, and Escape then Tab moves focus on, so keyboard users are
 * never trapped. "Run examples" only runs the visible examples; "Submit solution" runs every hidden test too. Pass/fail is always decided by the server.
 */
export function CodeWorkbench({ question, index, total, draft, run, check, busy, canCheck, onDraft, onRun, onCheck, onReveal, onHint }: Props) {
  const spec = question.code_spec;
  const escaped = useRef(false);
  if (!spec) return null;
  const locked = question.locked;
  const fb = question.feedback && question.feedback.kind === "code" ? question.feedback : null;
  const shown = check?.result ?? run ?? null;
  const tooLong = draft.length > MAX_CODE_CHARS;
  const canSubmit = canCheck && !locked && draft.trim().length > 0 && !tooLong;

  const onKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Escape") { escaped.current = true; return; }
    if (e.key === "Tab" && !e.shiftKey && !escaped.current) {
      e.preventDefault();
      const el = e.currentTarget;
      const { selectionStart: a, selectionEnd: b } = el;
      onDraft(`${draft.slice(0, a)}    ${draft.slice(b)}`);
      requestAnimationFrame(() => { el.selectionStart = el.selectionEnd = a + 4; });
      return;
    }
    escaped.current = false;
  };

  return (
    <section aria-labelledby="question-heading" className="space-y-4">
      <QuestionMeta question={question} index={index} total={total} />
      {question.title && <h2 className="font-display text-lg font-semibold text-text-primary">{question.title}</h2>}
      <p className="whitespace-pre-line text-base leading-relaxed text-text-primary">{question.statement}</p>

      <div className="space-y-2 rounded-[var(--radius-panel)] border border-border bg-surface px-3 py-3 text-sm">
        <p className="text-xs font-medium uppercase tracking-wide text-text-muted">Function to write</p>
        <code className="block break-words font-mono text-text-primary">{spec.signature}</code>
        {spec.constraints.length > 0 && <ul className="list-disc space-y-0.5 pl-5 text-text-secondary" aria-label="Constraints">{spec.constraints.map((c) => <li key={c}>{c}</li>)}</ul>}
      </div>

      {spec.examples.length > 0 && (
        <div className="space-y-1.5">
          <p className="text-sm font-medium text-text-primary">Examples</p>
          <div className="overflow-x-auto rounded-[var(--radius-panel)] border border-border">
            <table className="w-full min-w-[28rem] text-left text-xs">
              <caption className="sr-only">Example inputs and expected outputs</caption>
              <thead className="bg-surface-raised text-text-muted"><tr><th scope="col" className="px-3 py-1.5">Example</th><th scope="col" className="px-3 py-1.5">Input</th><th scope="col" className="px-3 py-1.5">Expected output</th></tr></thead>
              <tbody>{spec.examples.map((ex) => (
                <tr key={ex.id} className="border-t border-border align-top"><th scope="row" className="px-3 py-1.5 font-medium text-text-primary">{ex.label}</th><td className="px-3 py-1.5 font-mono break-all text-text-secondary">{ex.input}</td><td className="px-3 py-1.5 font-mono break-all text-text-secondary">{ex.expected}</td></tr>
              ))}</tbody>
            </table>
          </div>
          <p className="text-xs text-text-muted">Your submission is also checked against {spec.hidden_count} hidden tests (edge cases and larger inputs). Their details are never shown.</p>
        </div>
      )}

      <div className="space-y-1.5">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <label htmlFor={`code-${question.question_id}`} className="text-sm font-medium text-text-primary">Your Python code</label>
          <div className="flex items-center gap-2 text-xs text-text-muted">
            <span className={cn(tooLong && "text-danger")}>{draft.length}/{MAX_CODE_CHARS}</span>
            <Button type="button" variant="ghost" size="sm" disabled={locked || draft === spec.starter} onClick={() => onDraft(spec.starter)}><RotateCcw size={13} aria-hidden="true" /> Reset to starter</Button>
          </div>
        </div>
        <textarea id={`code-${question.question_id}`} value={draft} disabled={locked} spellCheck={false} autoCapitalize="off" autoCorrect="off" rows={Math.min(22, Math.max(10, draft.split("\n").length + 2))}
          aria-describedby={`code-help-${question.question_id}`} onChange={(e) => onDraft(e.target.value)} onKeyDown={onKeyDown}
          className="w-full resize-y rounded-[var(--radius-panel)] border border-border-input bg-surface p-3 font-mono text-sm leading-relaxed text-text-primary disabled:opacity-70" />
        <p id={`code-help-${question.question_id}`} className="text-xs text-text-muted">Tab inserts four spaces; press Escape then Tab to move focus out. Your code runs in an isolated runner with no network or file access and strict time and memory limits.</p>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <Button type="button" variant="secondary" onClick={onRun} loading={busy === "run"} disabled={locked || !draft.trim() || tooLong || Boolean(busy)}><Play size={14} aria-hidden="true" /> Run examples</Button>
        {canCheck && <Button type="button" onClick={onCheck} loading={busy === "check"} disabled={!canSubmit || Boolean(busy)}><Send size={14} aria-hidden="true" /> Submit solution</Button>}
        {canCheck && !locked && question.can_reveal && <Button type="button" variant="ghost" onClick={onReveal} loading={busy === "reveal"} disabled={Boolean(busy)}><Eye size={14} aria-hidden="true" /> Show reference solution (scores 0)</Button>}
      </div>
      {!canCheck && <p className="text-xs text-text-muted">Timed test: you can run the examples any time. Your last saved code is graded against every test when you submit the test.</p>}
      {canCheck && !locked && !question.can_reveal && question.checks === 0 && <p className="text-xs text-text-muted">The reference solution unlocks after your first submission (or after every hint).</p>}

      {!locked && <Hints key={question.question_id} question={question} busy={busy === "hint"} onRequest={onHint} />}

      {shown && <Results result={shown} label={check?.result ? "Submission results" : "Example run results"} />}
      {!shown && question.last_check && (
        <p role="status" className="text-sm text-text-secondary">Last submission: {question.last_check.passed} of {question.last_check.total} tests passed ({VERDICT_TITLE[question.last_check.verdict] ?? question.last_check.verdict}).</p>
      )}

      {fb && (
        <div role="status" className="space-y-3 rounded-[var(--radius-panel)] border border-border bg-surface-raised px-4 py-3 text-sm">
          <p className={cn("flex items-center gap-1.5 font-medium", fb.is_correct ? "text-success" : "text-warn")}>
            {fb.is_correct ? <CheckCircle2 size={15} aria-hidden="true" /> : <AlertTriangle size={15} aria-hidden="true" />}
            {fb.is_correct ? "Solved: every test passed" : "Reference solution revealed: this question scores 0"}
          </p>
          <CodeBlock code={fb.reference_source} label="Reference solution" />
          <p className="text-text-secondary"><span className="font-medium text-text-primary">Complexity:</span> time {fb.time_complexity}, space {fb.space_complexity}</p>
          <p className="text-text-secondary">{fb.explanation}</p>
        </div>
      )}
    </section>
  );
}
