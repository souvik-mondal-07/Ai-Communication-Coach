import { useRef } from "react";
import { Save } from "lucide-react";
import { Button } from "@/components/ui/button";
import { CodeBlock } from "@/features/dsa/CodeBlock";
import { ComplexityPanel } from "@/features/dsa/ComplexityPanel";
import { Hints, QuestionMeta } from "@/features/dsa/QuestionCard";
import { TestTable } from "@/features/dsa/TestTable";
import { MAX_CODE_CHARS } from "@/features/dsa/dsaMeta";
import type { SessionQuestion } from "@/types/dsa";

interface Props {
  question: SessionQuestion;
  index: number;
  total: number;
  draft: string;
  saving: boolean;
  canReveal: boolean;
  onChange: (code: string) => void;
  onSave: (opts?: { reveal?: boolean }) => void;
}

/**
 * Code-entry interface for write-the-function questions (no editor dependency: an accessible textarea).
 * Tab inserts four spaces; press Escape and then Tab to move focus away instead. The code is saved to the server,
 * NEVER run: the panel says so, and the reference solution and test cases are for you to compare against by hand.
 */
export function CodingPanel({ question, index, total, draft, saving, canReveal, onChange, onSave }: Props) {
  const ref = useRef<HTMLTextAreaElement>(null);
  const escaped = useRef(false);
  const coding = question.coding;
  const fb = question.feedback && question.feedback.kind === "code" ? question.feedback : null;
  const locked = question.locked;
  const dirty = draft !== (question.code_answer ?? "");
  if (!coding) return null;

  return (
    <section aria-labelledby="question-heading" className="space-y-4">
      <QuestionMeta question={question} index={index} total={total} />
      <p className="whitespace-pre-line text-base leading-relaxed text-text-primary">{question.statement}</p>
      {question.constraints && <p className="text-xs text-text-secondary"><span className="font-medium text-text-primary">Constraints:</span> {question.constraints}</p>}
      {coding.sample_io && <p className="font-mono text-xs text-text-secondary"><span className="font-sans font-medium text-text-primary">Example:</span> {coding.sample_io}</p>}

      <div className="space-y-1.5">
        <label htmlFor="code-editor" className="text-sm font-medium text-text-primary">Your solution — <code className="font-mono text-xs">{coding.function_name}()</code></label>
        <textarea
          id="code-editor"
          ref={ref}
          value={draft}
          spellCheck={false}
          autoCapitalize="off"
          autoCorrect="off"
          readOnly={locked}
          rows={Math.min(22, Math.max(10, draft.split("\n").length + 2))}
          maxLength={MAX_CODE_CHARS}
          aria-describedby="code-help"
          onChange={(e) => onChange(e.target.value)}
          onBlur={() => { if (dirty && !locked) onSave(); }}
          onKeyDown={(e) => {
            if (e.key === "Escape") { escaped.current = true; return; }
            if (e.key === "Tab" && !e.shiftKey && !escaped.current) {
              e.preventDefault();
              const el = e.currentTarget;
              const { selectionStart: s, selectionEnd: en } = el;
              onChange(`${draft.slice(0, s)}    ${draft.slice(en)}`);
              requestAnimationFrame(() => el.setSelectionRange(s + 4, s + 4));
              return;
            }
            escaped.current = false;
          }}
          className="block w-full resize-y rounded-[var(--radius-panel)] border border-border-input bg-surface p-3 font-mono text-sm leading-relaxed text-text-primary"
        />
        <p id="code-help" className="text-xs text-text-muted">
          <span className="font-medium text-text-secondary">This code is not run.</span> It is saved so you can review it against the reference solution and test cases. Tab inserts spaces; press Esc then Tab to leave the editor. {draft.length}/{MAX_CODE_CHARS} characters.
        </p>
        <div className="flex flex-wrap items-center gap-2">
          <Button type="button" size="sm" variant="secondary" onClick={() => onSave()} disabled={locked || saving || !dirty} loading={saving}><Save size={14} aria-hidden="true" /> {dirty ? "Save code" : "Saved"}</Button>
          <Button type="button" size="sm" variant="ghost" onClick={() => onChange(coding.template)} disabled={locked}>Reset to template</Button>
          {canReveal && !locked && <Button type="button" size="sm" variant="secondary" onClick={() => onSave({ reveal: true })} disabled={saving || !draft.trim()}>Submit &amp; show reference</Button>}
        </div>
      </div>

      <div className="space-y-1.5">
        <h3 className="text-sm font-medium text-text-primary">Sample test cases</h3>
        <TestTable tests={coding.visible_tests} caption="Visible test cases" hiddenCount={coding.hidden_test_count} />
      </div>

      {!fb && <Hints key={question.question_id} hints={question.hints} />}

      {fb && (
        <div className="space-y-3" role="status">
          <p className="rounded-[var(--radius-panel)] border border-warn/40 bg-warn/10 px-3 py-2 text-sm text-text-primary">{fb.execution_note}</p>
          <div className="space-y-1.5"><h3 className="text-sm font-medium text-text-primary">Reference solution</h3><CodeBlock code={fb.reference_solution} label="Reference solution" /></div>
          <div className="space-y-1.5"><h3 className="text-sm font-medium text-text-primary">All test cases</h3><TestTable tests={fb.test_cases} caption="All test cases including previously hidden ones" /></div>
          <p className="text-sm text-text-secondary">{fb.explanation}</p>
          <ComplexityPanel complexity={fb.complexity} />
        </div>
      )}
    </section>
  );
}
