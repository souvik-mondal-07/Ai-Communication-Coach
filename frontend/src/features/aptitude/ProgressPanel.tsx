import { Link } from "react-router-dom";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { ProgressBar } from "@/components/ui/progress";
import { accuracyTone, DIFFICULTY_LABELS, formatDuration, MODE_LABELS } from "@/features/aptitude/aptitudeMeta";
import { formatDateTime } from "@/utils/formatters";
import type { AptitudeProgress, Recommendations } from "@/types/aptitude";
import { BarChart3 } from "lucide-react";

const TONE_COLOR = { success: "var(--color-success)", warn: "var(--color-warn)", danger: "var(--color-danger)" } as const;

export function ProgressPanel({ progress, recommendations }: { progress: AptitudeProgress; recommendations: Recommendations | null }) {
  if (progress.sessions_completed === 0) {
    return (
      <EmptyState icon={BarChart3} title="No aptitude practice recorded yet"
        description="Finish a practice session or mock test and your accuracy, speed and weak topics will appear here. Nothing is estimated in advance." />
    );
  }
  const trend = progress.trend.map((t, i) => ({ n: i + 1, accuracy: t.accuracy }));
  return (
    <div className="space-y-6">
      <dl className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {[
          ["Sessions completed", String(progress.sessions_completed)],
          ["Questions answered", String(progress.questions_answered)],
          ["Overall accuracy", `${progress.accuracy}%`],
          ["Avg. time per question", progress.average_seconds_per_question === null ? "-" : `${progress.average_seconds_per_question}s`],
        ].map(([k, v]) => (
          <div key={k} className="rounded-[var(--radius-panel)] border border-border bg-surface px-4 py-3">
            <dt className="text-xs text-text-muted">{k}</dt><dd className="mt-0.5 text-xl font-semibold tabular-nums text-text-primary">{v}</dd>
          </div>
        ))}
      </dl>

      {recommendations && (
        <Card>
          <CardHeader><CardTitle>Revision recommendations</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            <p className="text-sm text-text-secondary">{recommendations.message}</p>
            {recommendations.weak_topics.map((w) => (
              <div key={w.topic_id} className="rounded-[var(--radius-panel)] border border-border px-3 py-2.5">
                <p className="text-sm font-medium text-text-primary">{w.topic_title} <Badge tone="danger">{w.accuracy}%</Badge></p>
                <p className="mt-0.5 text-xs text-text-muted">{w.reason}</p>
                {w.weak_subtopics.length > 0 && <p className="mt-1 text-xs text-text-secondary">Weakest: {w.weak_subtopics.map((s) => `${s.title} (${s.accuracy}%)`).join(", ")}</p>}
              </div>
            ))}
            {recommendations.incorrect_question_count > 0 && <p className="text-xs text-text-muted">{recommendations.incorrect_question_count} question(s) are still marked incorrect from your last attempt - use Weak topic practice to retry them.</p>}
          </CardContent>
        </Card>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader><CardTitle>Accuracy by topic</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            {progress.topic_accuracy.map((t) => (
              <div key={t.topic_id} className="space-y-1">
                <div className="flex justify-between gap-2 text-sm"><span className="text-text-primary">{t.topic_title}</span><span className="text-xs text-text-muted tabular-nums">{t.correct}/{t.answered} · {t.accuracy}%</span></div>
                <ProgressBar value={t.accuracy} label={`${t.topic_title} accuracy`} color={TONE_COLOR[accuracyTone(t.accuracy)]} />
              </div>
            ))}
          </CardContent>
        </Card>
        <div className="space-y-6">
          <Card>
            <CardHeader><CardTitle>Accuracy by difficulty</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              {progress.difficulty_accuracy.map((d) => (
                <div key={d.difficulty} className="space-y-1">
                  <div className="flex justify-between text-sm"><span className="text-text-primary">{DIFFICULTY_LABELS[d.difficulty]}</span><span className="text-xs text-text-muted tabular-nums">{d.correct}/{d.answered} · {d.accuracy}%</span></div>
                  <ProgressBar value={d.accuracy} label={`${DIFFICULTY_LABELS[d.difficulty]} accuracy`} color={TONE_COLOR[accuracyTone(d.accuracy)]} />
                </div>
              ))}
            </CardContent>
          </Card>
          <Card>
            <CardHeader><CardTitle>Improvement over time</CardTitle></CardHeader>
            <CardContent>
              {trend.length < 2 ? <p className="text-sm text-text-muted">Complete at least two sessions to see a trend.</p> : (
                <>
                  <div className="h-44" aria-hidden="true">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={trend} margin={{ top: 8, right: 8, bottom: 0, left: -16 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                        <XAxis dataKey="n" stroke="var(--color-text-muted)" fontSize={11} />
                        <YAxis domain={[0, 100]} stroke="var(--color-text-muted)" fontSize={11} />
                        <Tooltip />
                        <Line type="monotone" dataKey="accuracy" stroke="var(--color-signal)" strokeWidth={2} isAnimationActive={false} />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                  <p className="mt-2 text-xs text-text-muted">
                    {progress.improvement_points === null ? "A change figure appears after four sessions." : `Recent sessions are ${progress.improvement_points >= 0 ? "up" : "down"} ${Math.abs(progress.improvement_points)} points on your earlier ones.`}
                  </p>
                </>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      <Card>
        <CardHeader><CardTitle>Recent sessions</CardTitle></CardHeader>
        <CardContent>
          <ul className="divide-y divide-border">
            {progress.recent_sessions.map((s) => (
              <li key={s.session_id} className="flex flex-wrap items-center gap-x-4 gap-y-1 py-2.5 text-sm">
                <Link to={`/aptitude/result/${s.session_id}`} className="font-medium text-link underline-offset-2 hover:underline">{MODE_LABELS[s.mode]}</Link>
                <span className="tabular-nums text-text-primary">{s.score}/{s.total} ({s.accuracy}%)</span>
                <span className="text-xs text-text-muted">{formatDuration(s.time_taken_seconds)}</span>
                <span className="ml-auto text-xs text-text-muted">{formatDateTime(s.finished_at)}</span>
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}
