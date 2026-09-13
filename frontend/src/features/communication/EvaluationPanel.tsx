import { Card, CardContent } from "@/components/ui/card";
import { BetterResponseCard } from "@/features/communication/BetterResponseCard";
import { ImprovementList } from "@/features/communication/ImprovementList";
import { ScoreCard } from "@/features/communication/ScoreCard";
import { SCORE_FIELDS, type Evaluation } from "@/features/communication/communicationTypes";

interface EvaluationPanelProps {
  evaluation: Evaluation;
}

export function EvaluationPanel({ evaluation }: EvaluationPanelProps) {
  return (
    <div className="space-y-4">
      <Card>
        <CardContent className="py-5 text-center">
          <p className="text-xs text-text-muted">Overall Score</p>
          <p className="mt-1 font-display text-4xl font-semibold text-text-primary">
            {evaluation.overall_score}
            <span className="text-lg text-text-muted">/100</span>
          </p>
        </CardContent>
      </Card>

      <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-4">
        {SCORE_FIELDS.map(({ key, label }) => (
          <ScoreCard key={key} label={label} score={evaluation[key] as number} />
        ))}
      </div>

      <Card>
        <CardContent className="space-y-4 py-5">
          <ImprovementList title="Strengths" items={evaluation.strengths} variant="positive" />
          <ImprovementList title="Weaknesses" items={evaluation.weaknesses} variant="negative" />
          <ImprovementList title="Improvements" items={evaluation.improvements} variant="neutral" />
        </CardContent>
      </Card>

      {evaluation.better_responses.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-sm font-semibold text-text-primary">Better Responses</h3>
          {evaluation.better_responses.map((response, idx) => (
            <BetterResponseCard key={idx} response={response} />
          ))}
        </div>
      )}

      <Card>
        <CardContent className="py-4">
          <p className="mb-1 text-xs font-medium text-text-muted">Summary</p>
          <p className="text-sm leading-relaxed text-text-secondary">{evaluation.summary}</p>
        </CardContent>
      </Card>
    </div>
  );
}
