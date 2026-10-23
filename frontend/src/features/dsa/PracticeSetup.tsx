import { useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  availableQuestions, buildSessionRequest, defaultForm, DIFFICULTY_LABELS, MAX_QUESTIONS, MAX_TIMER_MINUTES, MODE_BY_ID, MODES, type SetupForm,
} from "@/features/dsa/dsaMeta";
import { cn } from "@/lib/utils";
import type { DsaDifficulty, DsaMode, SessionRequest, Syllabus } from "@/types/dsa";

interface Props {
  syllabus: Syllabus | null;
  initial?: Partial<SetupForm>;
  starting: boolean;
  error: string | null;
  hasWeakTopics: boolean;
  onStart: (request: SessionRequest) => void;
}

const COUNT_PRESETS = [5, 10, 20, 30];

export function PracticeSetup({ syllabus, initial, starting, error, hasWeakTopics, onStart }: Props) {
  const [form, setForm] = useState<SetupForm>(() => ({ ...defaultForm(initial?.mode ?? "topic"), ...initial }));
  const [formError, setFormError] = useState<string | null>(null);
  const meta = MODE_BY_ID[form.mode];
  const available = useMemo(() => availableQuestions(syllabus, form), [syllabus, form]);
  const patch = (p: Partial<SetupForm>) => { setForm((f) => ({ ...f, ...p })); setFormError(null); };
  const pickMode = (mode: DsaMode) => setForm((f) => ({ ...defaultForm(mode), topicIds: MODE_BY_ID[mode].canPickTopics ? f.topicIds : [], subtopicIds: MODE_BY_ID[mode].canPickTopics ? f.subtopicIds : [], difficulty: f.difficulty }));
  const toggle = (list: string[], id: string) => (list.includes(id) ? list.filter((x) => x !== id) : [...list, id]);
  const timed = meta.timer === "required" || (meta.timer === "optional" && form.useTimer);
  const shortfall = available !== null && meta.canPickTopics && form.questionCount > available;

  function submit(e: React.FormEvent) {
    e.preventDefault();
    const built = buildSessionRequest(form);
    if (!built.ok) return setFormError(built.error);
    onStart(built.request);
  }

  return (
    <form onSubmit={submit} className="space-y-6" aria-label="Start a practice session">
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

      {meta.canPickTopics && syllabus && (
        <fieldset>
          <legend className="mb-1 text-sm font-medium text-text-primary">Topics {meta.needsTopic ? <span className="text-danger" aria-hidden="true">*</span> : <span className="font-normal text-text-muted">(leave empty for the whole syllabus)</span>}</legend>
          <div className="max-h-72 space-y-2 overflow-y-auto rounded-[var(--radius-card)] border border-border p-3">
            {syllabus.topics.map((t) => {
              const topicOn = form.topicIds.includes(t.id);
              return (
                <details key={t.id} open={form.subtopicIds.some((s) => t.subtopics.some((x) => x.id === s))}>
                  <summary className="flex cursor-pointer items-center gap-2 text-sm text-text-primary">
                    <input type="checkbox" checked={topicOn} aria-label={`${t.title} (all subtopics)`} className="h-4 w-4 accent-[var(--color-signal)]"
                      onClick={(e) => e.stopPropagation()}
                      onChange={() => patch({ topicIds: toggle(form.topicIds, t.id), subtopicIds: form.subtopicIds.filter((s) => !t.subtopics.some((x) => x.id === s)) })} />
                    <span><span className="text-text-muted">{t.code}.</span> {t.title}</span>
                    <span className="ml-auto text-xs text-text-muted">{t.question_count} questions</span>
                  </summary>
                  {!topicOn && (
                    <ul className="mt-1.5 grid gap-1 pl-6 sm:grid-cols-2">
                      {t.subtopics.map((s) => (
                        <li key={s.id}>
                          <label className="flex items-center gap-2 text-xs text-text-secondary">
                            <input type="checkbox" className="h-3.5 w-3.5 accent-[var(--color-signal)]" disabled={s.question_count === 0}
                              checked={form.subtopicIds.includes(s.id)} onChange={() => patch({ subtopicIds: toggle(form.subtopicIds, s.id) })} />
                            {s.title} <span className="text-text-muted">({s.question_count})</span>
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
              <button key={d} type="button" role="radio" aria-checked={form.difficulty === d} onClick={() => patch({ difficulty: d as DsaDifficulty | "any" })}
                className={cn("rounded-full border px-3.5 py-1.5 text-sm", form.difficulty === d ? "border-signal bg-signal/10 text-text-primary" : "border-border text-text-secondary hover:border-border-input")}>
                {d === "any" ? "Any" : DIFFICULTY_LABELS[d]}
              </button>
            ))}
          </div>
        </fieldset>

        <div>
          <label htmlFor="dsa-count" className="mb-2 block text-sm font-medium text-text-primary">Number of questions</label>
          <div className="flex flex-wrap items-center gap-2">
            <input id="dsa-count" type="number" inputMode="numeric" min={1} max={MAX_QUESTIONS} value={Number.isNaN(form.questionCount) ? "" : form.questionCount}
              onChange={(e) => patch({ questionCount: e.target.value === "" ? NaN : Number(e.target.value) })}
              className="h-9 w-24 rounded-[var(--radius-panel)] border border-border-input bg-surface px-3 text-sm text-text-primary" />
            {COUNT_PRESETS.map((n) => (
              <button key={n} type="button" onClick={() => patch({ questionCount: n })} className="rounded-full border border-border px-2.5 py-1 text-xs text-text-secondary hover:border-border-input">{n}</button>
            ))}
          </div>
          {available !== null && meta.canPickTopics && (
            <p className={cn("mt-1.5 text-xs", shortfall ? "text-warn" : "text-text-muted")} aria-live="polite">
              {available === 0 ? "No questions match this scope yet."
                : shortfall ? `Only ${available} question${available === 1 ? "" : "s"} are available for this mode and scope - the session will be that long.`
                : `Up to ${available} questions available for this mode and scope${form.difficulty !== "any" ? " (the difficulty filter narrows this further)" : ""}.`}
            </p>
          )}
        </div>
      </div>

      <div className="space-y-3">
        {meta.timer === "optional" && (
          <label className="flex items-center gap-2 text-sm text-text-primary">
            <input type="checkbox" checked={form.useTimer} onChange={(e) => patch({ useTimer: e.target.checked })} className="h-4 w-4 accent-[var(--color-signal)]" /> Use a timer
          </label>
        )}
        {timed && (
          <div>
            <label htmlFor="dsa-timer" className="mb-1.5 block text-sm font-medium text-text-primary">Time limit (minutes)</label>
            <input id="dsa-timer" type="number" inputMode="numeric" min={1} max={MAX_TIMER_MINUTES} value={Number.isNaN(form.timerMinutes) ? "" : form.timerMinutes}
              onChange={(e) => patch({ timerMinutes: e.target.value === "" ? NaN : Number(e.target.value) })}
              className="h-9 w-24 rounded-[var(--radius-panel)] border border-border-input bg-surface px-3 text-sm text-text-primary" />
            <span className="ml-2 text-xs text-text-muted">The session is submitted automatically when time runs out.</span>
          </div>
        )}
        {meta.allowsFeedback && (
          <label className="flex items-start gap-2 text-sm text-text-primary">
            <input type="checkbox" checked={form.immediateFeedback} onChange={(e) => patch({ immediateFeedback: e.target.checked })} className="mt-0.5 h-4 w-4 accent-[var(--color-signal)]" />
            <span>Show the answer and explanation after each question<span className="block text-xs text-text-muted">Answers lock once revealed. Turn off to review everything at the end.</span></span>
          </label>
        )}
      </div>

      <Card variant="raised"><CardContent className="space-y-1 py-3 text-xs leading-relaxed text-text-secondary">
        <p><span className="font-medium text-text-primary">Scoring:</span> 1 mark per correct multiple-choice answer, 0 for incorrect or unanswered, no negative marking. Time is measured by the server.</p>
        {form.mode === "coding" && <p><span className="font-medium text-text-primary">Coding exercises are not run automatically.</span> Write-the-function answers are saved and compared with the reference solution and test cases by you; they are not part of your score. Fill-the-line and fix-the-bug questions are multiple choice and are scored.</p>}
      </CardContent></Card>

      {(formError || error) && <p role="alert" className="text-sm text-danger">{formError ?? error}</p>}
      <Button type="submit" size="lg" loading={starting}>{starting ? "Starting…" : form.mode === "timed_mock" ? "Start mock test" : "Start practice"}</Button>
    </form>
  );
}
