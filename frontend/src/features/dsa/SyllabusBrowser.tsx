import { ChevronDown } from "lucide-react";
import { Link } from "react-router-dom";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { ProgressBar } from "@/components/ui/progress";
import { completionPercent, COVERAGE_LABELS, FORMAT_LABELS } from "@/features/dsa/dsaMeta";
import type { CoverageStatus, DsaFormat, Syllabus } from "@/types/dsa";

const TONE: Record<CoverageStatus, "success" | "warn" | "danger"> = { implemented: "success", partial: "warn", missing: "danger" };
const FORMATS: DsaFormat[] = ["conceptual", "scenario", "output", "trace", "complexity", "coding"];

/**
 * Topic and subtopic browser. Every number and status comes from the questions that exist right now: a subtopic is only
 * "Ready" with enough real questions, and an empty one says so. Each syllabus line is listed with its question count.
 */
export function SyllabusBrowser({ syllabus }: { syllabus: Syllabus }) {
  const { totals } = syllabus;
  return (
    <div className="space-y-6">
      <Card variant="raised">
        <CardContent className="space-y-3 py-4">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <p className="text-sm font-medium text-text-primary">Syllabus coverage</p>
            <p className="text-xs text-text-muted">{totals.subtopics_implemented} of {totals.subtopics} subtopics ready · {totals.questions} questions in the bank</p>
          </div>
          <ProgressBar value={completionPercent(syllabus)} label="Subtopics with enough questions" tone="success" />
          <p className="text-xs text-text-muted">A subtopic counts as ready with at least {totals.min_questions_per_subtopic} reviewed questions. That is a minimum, not depth: small subtopics repeat quickly in long sessions.</p>
          <ul className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-text-secondary" aria-label="Questions by format">
            {FORMATS.map((f) => <li key={f}>{FORMAT_LABELS[f]}: <span className="font-medium tabular-nums text-text-primary">{totals.by_format[f] ?? 0}</span></li>)}
          </ul>
          <p className="text-xs text-text-muted"><span className="font-medium text-text-secondary">Code execution:</span> {syllabus.execution.message}</p>
        </CardContent>
      </Card>

      {syllabus.topics.map((t) => (
        <details key={t.id} className="group rounded-[var(--radius-card)] border border-border bg-surface">
          <summary className="flex cursor-pointer list-none items-center gap-3 px-4 py-3">
            <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-[var(--radius-panel)] bg-signal/10 text-xs font-semibold text-signal" aria-hidden="true">{t.code}</span>
            <span className="min-w-0 flex-1">
              <span className="block text-sm font-medium text-text-primary">{t.title}</span>
              <span className="block text-xs text-text-muted">{t.summary}</span>
            </span>
            <Badge tone={TONE[t.status]}>{t.subtopics_implemented}/{t.subtopics_total} ready</Badge>
            <span className="hidden text-xs text-text-muted sm:inline">{t.question_count} questions</span>
            <ChevronDown size={16} className="shrink-0 text-text-muted transition-transform group-open:rotate-180" aria-hidden="true" />
          </summary>
          <div className="space-y-3 border-t border-border px-4 py-3">
            <div>
              <h3 className="text-xs font-semibold text-text-primary">Syllabus items</h3>
              <ul className="mt-1 space-y-0.5 text-xs text-text-secondary">
                {t.items.map((i) => <li key={i.text}>{i.text} <span className="text-text-muted">({i.question_count} questions)</span></li>)}
              </ul>
            </div>
            <ul className="divide-y divide-border rounded-[var(--radius-panel)] border border-border">
              {t.subtopics.map((s) => (
                <li key={s.id} className="flex flex-wrap items-center gap-x-3 gap-y-1 px-3 py-2.5 text-sm">
                  <span className="min-w-0 flex-1 text-text-primary">{s.title}</span>
                  <span className="text-xs text-text-muted tabular-nums">{s.by_difficulty.easy}E · {s.by_difficulty.medium}M · {s.by_difficulty.hard}H</span>
                  <Badge tone={TONE[s.status]}>{COVERAGE_LABELS[s.status]}</Badge>
                  {s.question_count > 0
                    ? <Link to={`/dsa?mode=topic&subtopic=${encodeURIComponent(s.id)}`} className="text-xs font-medium text-link underline-offset-2 hover:underline">Practice<span className="sr-only"> {s.title}</span></Link>
                    : <span className="text-xs text-text-muted">Not available</span>}
                </li>
              ))}
            </ul>
          </div>
        </details>
      ))}
    </div>
  );
}
