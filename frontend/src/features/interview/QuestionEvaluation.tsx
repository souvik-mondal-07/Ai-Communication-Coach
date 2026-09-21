import { ScoreCard } from "@/features/communication/ScoreCard";
import type { AnswerRecord } from "@/types/interview";

interface QuestionEvaluationProps {
  record: Pick<
    AnswerRecord,
    "technical_evaluation" | "communication_evaluation" | "improved_answer"
  >;
}

/** Scores, feedback and an improved answer for one answered prompt. Renders nothing while evaluations are hidden. */
export function QuestionEvaluation({ record }: QuestionEvaluationProps) {
  const tech = record.technical_evaluation;
  const comm = record.communication_evaluation;
  if (!tech || !comm) return null;

  return (
    <div className="space-y-3 rounded-[var(--radius-panel)] border border-border bg-surface-raised p-3">
      <div className="grid grid-cols-2 gap-2.5">
        <ScoreCard label="Technical Score" score={tech.technical_score} />
        <ScoreCard label="Communication Score" score={comm.communication_score} />
      </div>
      <div className="space-y-2 text-sm">
        <p className="text-text-secondary">
          <span className="font-medium text-text-primary">Technical feedback: </span>
          {tech.feedback}
        </p>
        <p className="text-text-secondary">
          <span className="font-medium text-text-primary">Communication feedback: </span>
          {comm.feedback}
        </p>
        {record.improved_answer && (
          <div className="rounded-[var(--radius-panel)] border border-signal/30 bg-signal/5 px-3 py-2">
            <p className="text-xs font-medium text-signal">Improved Answer</p>
            <p className="mt-1 text-text-secondary">{record.improved_answer}</p>
          </div>
        )}
      </div>
    </div>
  );
}
