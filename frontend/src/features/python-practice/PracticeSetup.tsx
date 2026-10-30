import { useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  availableQuestions, buildSessionRequest, defaultForm, DIFFICULTY_LABELS, MAX_QUESTIONS, MAX_TIMER_MINUTES, MODE_BY_ID, MODES, type SetupForm,
} from "@/features/python-practice/pythonPracticeMeta";
import { cn } from "@/lib/utils";
import type { PyDifficulty, PyMode, SessionRequest, Syllabus } from "@/types/pythonPractice";

interface Props {
  syllabus: Syllabus;
  initial?: Partial<SetupForm>;
  starting: boolean;
  error: string | null;
  hasWeakTopics: boolean;
  onStart: (request: SessionRequest) => void;
}

const COUNT_PRESETS = [5, 10, 20, 30];
const toggle = (list: string[], id: string) => (list.includes(id) ? list.filter((x) => x !== id) : [...list, id]);

export function PracticeSetup({ syllabus, initial, starting, error, hasWeakTopics, onStart }: Props) {
  const [form, setForm] = useState<SetupForm>(() => ({ ...defaultForm(initial?.mode ?? "topic"), ...initial }));
  const [formError, setFormError] = useState<string | null>(null);
  const meta = MODE_BY_ID[form.mode];
  const available = useMemo(() => availableQuestions(syllabus, form), [syllabus, form]);
  const patch = (p: Partial<SetupForm>) => { setForm((f) => ({ ...f, ...p })); setFormError(null); };
  const pickMode = (mode: PyMode) => setForm((f) => ({ ...defaultForm(mode), unitIds: MODE_BY_ID[mode].canPickScope ? f.unitIds : [], topicIds: MODE_BY_ID[mode].canPickScope ? f.topicIds : [], difficulty: f.difficulty }));
  const timed = meta.timer === "required" || (meta.timer === "optional" && form.useTimer);
  const shortfall = available !== null && form.questionCount > available;

  function submit(e: React.FormEvent) {
    e.preventDefault();
    const built = buildSessionRequest(form);
    if (!built.ok) return setFormError(built.error);
    onStart(built.request);
  }

  return (
    <form onSubmit={submit} noValidate className="space-y-6" aria-label="Start a practice session">
      <fieldset>
        <legend className="mb-2 text-sm font-medium text-text-primary">Practice mode</legend>
        <div role="radiogroup" aria-label="Practice mode" className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {MODES.map((m) => {
            const Icon = m.icon;
            const selected = form.mode === m.id;
            return (
              <button key={m.id} type="button" role="radio" aria-checked={selected} onClick={() => pickMode(m.id)}
                className={cn("rounded-[var(--radius-card)] border p-4 text-left transition-colors", selected ? "border-signal bg-signal/10" : "border-border bg-surface hover:border-border-input")}>
                <span className="flex items-center gap-2 text-sm font-semibold text-text-primary"><Icon size={16} className="text-signal" aria-hidden="true" />{m.title}</span>
                <span className="mt-1.5 block text-xs leading-relaxed text-text-secondary">{m.blurb}</span>
                {m.id === "weak" && !hasWeakTopics && <span className="mt-2 block text-xs text-text-muted">Becomes useful once you have answered questions.</span>}
              </button>
            );
          })}
        </div>
      </fieldset>

      {meta.canPickScope && (
        <fieldset>
          <legend className="mb-1 text-sm font-medium text-text-primary">
            {meta.needsTopic ? <>Topics <span className="text-danger" aria-hidden="true">*</span></> : <>Scope <span className="font-normal text-text-muted">(leave empty for the whole syllabus)</span></>}
          </legend>
          <div className="max-h-72 space-y-2 overflow-y-auto rounded-[var(--radius-card)] border border-border p-3">
            {syllabus.units.map((u) => {
              const unitOn = form.unitIds.includes(u.id);
              return (
                <details key={u.id} open={form.topicIds.some((t) => u.topics.some((x) => x.id === t))}>
                  <summary className="flex cursor-pointer items-center gap-2 text-sm text-text-primary">
                    {!meta.needsTopic && (
                      <input type="checkbox" checked={unitOn} aria-label={`${u.title} (whole unit)`} className="h-4 w-4 accent-[var(--color-signal)]" onClick={(e) => e.stopPropagation()}
                        onChange={() => patch({ unitIds: toggle(form.unitIds, u.id), topicIds: form.topicIds.filter((t) => !u.topics.some((x) => x.id === t)) })} />
                    )}
                    <span><span className="text-text-muted">Unit {u.code}.</span> {u.title}</span>
                    <span className="ml-auto text-xs text-text-muted">{u.question_count} questions</span>
                  </summary>
                  {!unitOn && (
                    <ul className="mt-1.5 grid gap-1 pl-6 sm:grid-cols-2">
                      {u.topics.map((t) => (
                        <li key={t.id}>
                          <label className="flex items-center gap-2 text-xs text-text-secondary">
                            <input type="checkbox" className="h-3.5 w-3.5 accent-[var(--color-signal)]" disabled={t.question_count === 0} checked={form.topicIds.includes(t.id)} onChange={() => patch({ topicIds: toggle(form.topicIds, t.id) })} />
                            {t.title} <span className="text-text-muted">({t.question_count})</span>
                          </label>
                        </li>
                      ))}
                    </ul>
                  )}
                </details>
              );
            })}
          </div>
        </fieldset>
      )}

      <div className="grid gap-6 md:grid-cols-2">
        <fieldset>
          <legend className="mb-2 text-sm font-medium text-text-primary">Difficulty</legend>
          <div role="radiogroup" aria-label="Difficulty" className="flex flex-wrap gap-2">
            {(["any", "easy", "medium", "hard"] as const).map((d) => (
              <button key={d} type="button" role="radio" aria-checked={form.difficulty === d} onClick={() => patch({ difficulty: d as PyDifficulty | "any" })}
                className={cn("rounded-full border px-3.5 py-1.5 text-sm", form.difficulty === d ? "border-signal bg-signal/10 text-text-primary" : "border-border text-text-secondary hover:border-border-input")}>
                {d === "any" ? "Any" : DIFFICULTY_LABELS[d]}
              </button>
            ))}
          </div>
        </fieldset>
        <div>
          <label htmlFor="py-count" className="mb-2 block text-sm font-medium text-text-primary">Number of questions</label>
          <div className="flex flex-wrap items-center gap-2">
            <input id="py-count" type="number" inputMode="numeric" min={1} max={MAX_QUESTIONS} value={Number.isNaN(form.questionCount) ? "" : form.questionCount}
              onChange={(e) => patch({ questionCount: e.target.value === "" ? NaN : Number(e.target.value) })}
              className="h-9 w-24 rounded-[var(--radius-panel)] border border-border-input bg-surface px-3 text-sm text-text-primary" />
            {COUNT_PRESETS.map((n) => <button key={n} type="button" onClick={() => patch({ questionCount: n })} className="rounded-full border border-border px-2.5 py-1 text-xs text-text-secondary hover:border-border-input">{n}</button>)}
          </div>
          {available !== null && form.mode !== "weak" && (
            <p className={cn("mt-1.5 text-xs", shortfall || available === 0 ? "text-warn" : "text-text-muted")} aria-live="polite">
              {available === 0 ? "No questions match this scope yet."
                : shortfall ? `Only about ${available} question${available === 1 ? " is" : "s are"} in this scope, so the session may be shorter.`
                : `Up to ${available} questions in this scope; the mode and difficulty filters narrow this further.`}
            </p>
          )}
        </div>
      </div>

      <div className="space-y-3">
        {meta.timer === "optional" && (
          <label className="flex items-center gap-2 text-sm text-text-primary"><input type="checkbox" checked={form.useTimer} onChange={(e) => patch({ useTimer: e.target.checked })} className="h-4 w-4 accent-[var(--color-signal)]" /> Use a timer</label>
        )}
        {timed && (
          <div>
            <label htmlFor="py-timer" className="mb-1.5 block text-sm font-medium text-text-primary">Time limit (minutes)</label>
            <input id="py-timer" type="number" inputMode="numeric" min={1} max={MAX_TIMER_MINUTES} value={Number.isNaN(form.timerMinutes) ? "" : form.timerMinutes}
              onChange={(e) => patch({ timerMinutes: e.target.value === "" ? NaN : Number(e.target.value) })}
              className="h-9 w-24 rounded-[var(--radius-panel)] border border-border-input bg-surface px-3 text-sm text-text-primary" />
            <span className="ml-2 text-xs text-text-muted">{form.mode === "timed_mock" ? "Leave it as is to let the server size the test from its questions. " : ""}The session is submitted automatically when time runs out.</span>
          </div>
        )}
        {meta.allowsFeedback && (
          <label className="flex items-start gap-2 text-sm text-text-primary">
            <input type="checkbox" checked={form.immediateFeedback} onChange={(e) => patch({ immediateFeedback: e.target.checked })} className="mt-0.5 h-4 w-4 accent-[var(--color-signal)]" />
            <span>Check answers as I go (feedback, hints and code checking)<span className="block text-xs text-text-muted">Answers lock once revealed. Turn off to practise without feedback and review everything at the end.</span></span>
          </label>
        )}
      </div>

      <Card variant="raised"><CardContent className="space-y-1 py-3 text-xs leading-relaxed text-text-secondary">
        <p><span className="font-medium text-text-primary">Scoring:</span> 1 mark per correct answer, 0 for incorrect or unanswered, no negative marking. The server grades everything: code is run against hidden tests, so any correct implementation is accepted.</p>
        <p><span className="font-medium text-text-primary">Code runner:</span> your code runs in an isolated process with no network or file access and strict time and memory limits. Revealing a reference solution before solving it scores that question 0.</p>
      </CardContent></Card>

      {(formError || error) && <p role="alert" className="text-sm text-danger">{formError ?? error}</p>}
      <Button type="submit" size="lg" loading={starting}>{starting ? "Starting…" : form.mode === "timed_mock" ? "Start mock interview" : "Start practice"}</Button>
    </form>
  );
}
