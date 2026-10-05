import { CheckCircle2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  MODE_LABELS,
  type PracticeCompleteResult,
  type PracticeMode,
} from "@/features/cybersecurity/cybersecurityTypes";
import { formatClock, recommendationRoute } from "@/features/cybersecurity/practice/practiceUtils";

interface PracticeSummaryProps {
  summary: PracticeCompleteResult;
  onPracticeAgain: () => void;
  onBack: () => void;
  onOpenRecommendation: (route: string) => void;
}

function Tile({ label, value }: { label: string; value: string | number }) {
  return (
    <div>
      <p className="text-xs text-text-muted">{label}</p>
      <p className="mt-1 font-display text-2xl font-semibold text-text-primary">{value}</p>
    </div>
  );
}

function Areas({ title, items, tone }: { title: string; items: string[]; tone: string }) {
  if (items.length === 0) return null;
  return (
    <div>
      <p className="text-xs font-medium text-text-muted">{title}</p>
      <ul className="mt-1 space-y-1">
        {items.map((item) => (
          <li key={item} className={`text-sm ${tone}`}>
            • {item}
          </li>
        ))}
      </ul>
    </div>
  );
}

export function PracticeSummary({ summary, onPracticeAgain, onBack, onOpenRecommendation }: PracticeSummaryProps) {
  const total = summary.questions_total ?? summary.questions_answered;
  const next = summary.recommended_next;
  const scored = summary.scored !== false;

  return (
    <div className="mx-auto max-w-xl space-y-5 py-6">
      <div className="text-center">
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-[var(--radius-panel)] bg-signal/15 text-signal">
          <CheckCircle2 size={24} />
        </div>
        <h1 className="mt-3 font-display text-xl font-semibold text-text-primary">Practice Complete</h1>
        <p className="mt-1 text-xs text-text-muted">
          {summary.topic_title}
          {summary.mode ? ` · ${MODE_LABELS[summary.mode as PracticeMode] ?? summary.mode}` : ""}
          {summary.timed_out ? " · time ran out" : ""}
        </p>
      </div>

      <Card>
        <CardContent className="space-y-5 py-6">
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <Tile label="Score" value={scored ? `${summary.score}%` : "—"} />
            <Tile label="Questions" value={total} />
            <Tile label="Correct / strong" value={summary.correct_answers} />
            <Tile label="Needs improvement" value={summary.needs_improvement ?? Math.max(0, summary.questions_answered - summary.correct_answers)} />
          </div>

          {!scored && (
            <p className="text-sm text-text-secondary">
              No questions were answered, so this session isn't scored and won't affect your progress.
            </p>
          )}

          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
            {summary.hints_used !== null && summary.hints_used !== undefined && (
              <Tile label="Hints used" value={summary.hints_used} />
            )}
            {summary.duration_seconds != null && <Tile label="Time" value={formatClock(summary.duration_seconds)} />}
            {summary.difficulty && summary.difficulty_mode && (
              <Tile
                label="Difficulty"
                value={`${summary.difficulty_mode === "adaptive" ? "Adaptive · " : ""}${summary.difficulty}`}
              />
            )}
          </div>

          <Areas title="Strong areas" items={summary.strong_areas ?? []} tone="text-signal" />
          <Areas title="Needs work" items={summary.needs_work ?? []} tone="text-warn" />
          {(summary.unanswered ?? 0) > 0 && (
            <p className="text-xs text-text-muted">{summary.unanswered} question(s) were not answered.</p>
          )}
        </CardContent>
      </Card>

      {next && (
        <Card>
          <CardContent className="space-y-2 py-4">
            <p className="text-xs font-medium text-text-muted">Recommended next</p>
            <p className="text-sm font-semibold text-text-primary">{next.title}</p>
            {next.reasons.map((reason) => (
              <p key={reason} className="text-xs text-text-secondary">
                {reason}
              </p>
            ))}
            <Button size="sm" onClick={() => onOpenRecommendation(recommendationRoute(next))}>
              Open
            </Button>
          </CardContent>
        </Card>
      )}

      <div className="flex flex-col justify-center gap-2 sm:flex-row">
        <Button variant="secondary" onClick={onBack}>
          Back to Practice
        </Button>
        <Button onClick={onPracticeAgain}>Practice Again</Button>
      </div>
    </div>
  );
}
