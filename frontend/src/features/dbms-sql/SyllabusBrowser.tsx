import { Link } from "react-router-dom";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ProgressBar } from "@/components/ui/progress";
import { completionPercent, COVERAGE_LABELS, FORMAT_LABELS } from "@/features/dbms-sql/dbmsSqlMeta";
import type { CoverageStatus, Syllabus } from "@/types/dbmsSql";

const TONE: Record<CoverageStatus, "success" | "warn" | "danger"> = { implemented: "success", partial: "warn", missing: "danger" };

/** The seven units and seventy topics with REAL question counts from the server. A topic is "Ready" only when it has enough questions. */
export function SyllabusBrowser({ syllabus }: { syllabus: Syllabus }) {
  const pct = completionPercent(syllabus);
  return (
    <div className="space-y-5">
      <Card variant="raised"><CardContent className="space-y-2 py-4">
        <p className="text-sm text-text-primary"><span className="font-semibold tabular-nums">{syllabus.topics_implemented}</span> of <span className="font-semibold tabular-nums">{syllabus.topics_total}</span> topics have at least {syllabus.min_questions_per_topic} questions · {syllabus.question_total} questions in total.</p>
        <ProgressBar value={pct} label="Topics with enough questions" tone="success" />
        <p className="text-xs text-text-muted">SQL engine: {syllabus.sql_engine.engine} {syllabus.sql_engine.version} (read-only; window functions {syllabus.sql_engine.window_functions ? "supported" : "not supported"}; RIGHT/FULL JOIN {syllabus.sql_engine.right_full_join ? "supported" : "not supported"}). Questions about other products are labelled with their dialect.</p>
      </CardContent></Card>
      {syllabus.units.map((u) => (
        <Card key={u.id}>
          <CardHeader>
            <CardTitle className="flex flex-wrap items-center gap-2"><span>Unit {u.code}: {u.title}</span><Badge tone="neutral">{u.question_count} questions</Badge><Badge tone={u.topics_implemented === u.topics_total ? "success" : "warn"}>{u.topics_implemented}/{u.topics_total} topics ready</Badge></CardTitle>
            <p className="text-xs text-text-muted">{u.summary}</p>
          </CardHeader>
          <CardContent>
            <ul className="divide-y divide-border">
              {u.topics.map((t) => (
                <li key={t.id} className="flex flex-wrap items-center justify-between gap-2 py-2">
                  <div className="min-w-0">
                    <p className="text-sm text-text-primary">{t.title}</p>
                    <p className="text-[11px] text-text-muted">
                      {t.question_count} question{t.question_count === 1 ? "" : "s"} · E/M/H {t.by_difficulty.easy}/{t.by_difficulty.medium}/{t.by_difficulty.hard}
                      {Object.keys(t.by_format).length > 0 && ` · ${Object.entries(t.by_format).map(([f, n]) => `${FORMAT_LABELS[f as keyof typeof FORMAT_LABELS] ?? f} ${n}`).join(", ")}`}
                      {(t.by_interaction.sql ?? 0) > 0 && " · hands-on SQL"}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge tone={TONE[t.status]}>{COVERAGE_LABELS[t.status]}</Badge>
                    {t.question_count > 0 && <Link className="text-xs text-link underline-offset-2 hover:underline" to={`/dbms-sql?mode=topic&topic=${encodeURIComponent(t.id)}`} aria-label={`Practise ${t.title}`}>Practise</Link>}
                  </div>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
