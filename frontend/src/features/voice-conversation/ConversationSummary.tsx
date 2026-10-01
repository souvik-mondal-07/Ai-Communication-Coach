import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardTitle } from "@/components/ui/card";
import { formatDuration } from "@/features/voice/formatDuration";
import type { VoiceConversationSummary } from "@/types/voiceConversation";

const SCORE_LABELS: Record<string, string> = {
  overall_score: "Overall",
  technical_score: "Technical",
  communication_score: "Communication",
  pressure_handling_score: "Pressure handling",
  response_control_score: "Response control",
  clarity_score: "Clarity",
  grammar_score: "Grammar",
  vocabulary_score: "Vocabulary",
  professionalism_score: "Professionalism",
  confidence_score: "Confidence",
  relevance_score: "Relevance",
  conversation_flow_score: "Conversation flow",
};

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[var(--radius-panel)] border border-border px-3 py-2">
      <dt className="text-[11px] text-text-muted">{label}</dt>
      <dd className="text-sm font-medium text-text-primary">{value}</dd>
    </div>
  );
}

function List({ title, items }: { title: string; items: string[] }) {
  if (items.length === 0) return null;
  return (
    <div>
      <h3 className="mb-1 text-sm font-medium text-text-primary">{title}</h3>
      <ul className="list-disc space-y-1 pl-5 text-sm text-text-secondary">
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </div>
  );
}

interface ConversationSummaryProps {
  summary: VoiceConversationSummary | null;
  onNew: () => void;
}

/** Shows only values the server actually measured or took from an existing evaluation. */
export function ConversationSummary({ summary, onNew }: ConversationSummaryProps) {
  const evaluation = summary?.evaluation ?? null;
  const scores = evaluation
    ? Object.entries(SCORE_LABELS).filter(([key]) => typeof evaluation[key] === "number")
    : [];
  const speaking = summary?.speaking_metrics ?? null;
  const pace = typeof speaking?.average_speaking_rate_wpm === "number" ? speaking.average_speaking_rate_wpm : null;
  const fillers = typeof speaking?.total_filler_words === "number" ? speaking.total_filler_words : null;
  const evaluationSummary = typeof evaluation?.summary === "string" ? evaluation.summary : null;

  return (
    <Card>
      <CardContent className="space-y-5 py-5">
        <CardTitle>Session completed</CardTitle>
        {!summary ? (
          <p className="text-sm text-text-secondary">This conversation has ended.</p>
        ) : (
          <>
            <dl className="grid grid-cols-2 gap-2 sm:grid-cols-4">
              <Stat label="Mode" value={summary.mode_label} />
              <Stat label="Answers" value={String(summary.turns)} />
              <Stat label="Duration" value={formatDuration(summary.duration_seconds)} />
              {summary.average_response_duration_seconds != null && (
                <Stat label="Avg. answer length" value={`${Math.round(summary.average_response_duration_seconds)}s`} />
              )}
              {summary.average_response_words != null && (
                <Stat label="Avg. words / answer" value={String(Math.round(summary.average_response_words))} />
              )}
              {pace != null && <Stat label="Speaking pace" value={`${Math.round(pace)} wpm`} />}
              {fillers != null && <Stat label="Filler words" value={String(fillers)} />}
            </dl>

            {scores.length > 0 && (
              <dl className="grid grid-cols-2 gap-2 sm:grid-cols-4" aria-label="Scores">
                {scores.map(([key, label]) => (
                  <Stat key={key} label={label} value={`${Math.round(evaluation?.[key] as number)} / 100`} />
                ))}
              </dl>
            )}

            {evaluationSummary && <p className="text-sm text-text-secondary">{evaluationSummary}</p>}
            {summary.evaluation_error && (
              <p role="status" className="text-sm text-text-muted">
                The evaluation couldn't be generated this time. Your conversation was still saved.
              </p>
            )}
            {!summary.evaluation_available && !summary.evaluation_error && summary.turns > 0 && (
              <p className="text-sm text-text-muted">This conversation type doesn't produce a scored evaluation.</p>
            )}
            <List title="Strengths" items={summary.strengths} />
            <List title="Areas to improve" items={summary.areas_to_improve} />
          </>
        )}
        <div className="flex flex-wrap gap-2">
          <Button onClick={onNew}>New conversation</Button>
          <Link
            to="/progress"
            className="inline-flex h-9 items-center rounded-[var(--radius-panel)] border border-border bg-surface-raised px-4 text-sm font-medium text-text-primary hover:border-border-strong focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-signal"
          >
            View progress
          </Link>
        </div>
      </CardContent>
    </Card>
  );
}
