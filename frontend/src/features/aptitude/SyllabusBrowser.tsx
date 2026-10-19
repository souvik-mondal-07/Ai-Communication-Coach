import { ChevronDown } from "lucide-react";
import { Link } from "react-router-dom";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { ProgressBar } from "@/components/ui/progress";
import { completionPercent, COVERAGE_LABELS } from "@/features/aptitude/aptitudeMeta";
import type { CoverageStatus, Syllabus } from "@/types/aptitude";

const TONE: Record<CoverageStatus, "success" | "warn" | "danger"> = { implemented: "success", partial: "warn", missing: "danger" };

/**
 * Topic and subtopic browser. Every number and status comes from the questions that exist right now - a
 * subtopic is only "Ready" with enough real questions, and an empty one says so.
 */
export function SyllabusBrowser({ syllabus }: { syllabus: Syllabus }) {
  const { totals } = syllabus;
  const sections = [...new Set(syllabus.topics.map((t) => t.section))];
  return (
    <div className="space-y-6">
      <Card variant="raised">
        <CardContent className="space-y-3 py-4">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <p className="text-sm font-medium text-text-primary">Syllabus coverage</p>
            <p className="text-xs text-text-muted">{totals.subtopics_implemented} of {totals.subtopics} subtopics ready · {totals.questions} questions in the bank</p>
          </div>
          <ProgressBar value={completionPercent(syllabus)} label="Subtopics with enough questions" tone="success" />
          <p className="text-xs text-text-muted">A subtopic counts as ready with at least {totals.min_questions_per_subtopic} reviewed questions. Small subtopics repeat quickly in long sessions.</p>
        </CardContent>
      </Card>

      {sections.map((section) => (
        <section key={section} aria-labelledby={`sec-${section.replace(/\W+/g, "-")}`} className="space-y-2">
          <h2 id={`sec-${section.replace(/\W+/g, "-")}`} className="text-sm font-semibold text-text-primary">{section}</h2>
          {syllabus.topics.filter((t) => t.section === section).map((t) => (
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
              <ul className="divide-y divide-border border-t border-border">
                {t.subtopics.map((s) => (
                  <li key={s.id} className="flex flex-wrap items-center gap-x-3 gap-y-1 px-4 py-2.5 text-sm">
                    <span className="min-w-0 flex-1 text-text-primary">{s.title}</span>
                    <span className="text-xs text-text-muted tabular-nums">{s.by_difficulty.easy}E · {s.by_difficulty.medium}M · {s.by_difficulty.hard}H</span>
                    <Badge tone={TONE[s.status]}>{COVERAGE_LABELS[s.status]}</Badge>
                    {s.question_count > 0
                      ? <Link to={`/aptitude?mode=topic&subtopic=${encodeURIComponent(s.id)}`} className="text-xs font-medium text-link underline-offset-2 hover:underline">Practice<span className="sr-only"> {s.title}</span></Link>
                      : <span className="text-xs text-text-muted">Not available</span>}
                  </li>
                ))}
              </ul>
            </details>
          ))}
        </section>
      ))}
    </div>
  );
}
