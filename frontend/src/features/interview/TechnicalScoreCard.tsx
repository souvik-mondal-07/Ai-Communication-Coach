import { Card, CardContent } from "@/components/ui/card";
import { ScoreCard } from "@/features/communication/ScoreCard";
import { averageOf } from "@/features/interview/scoreUtils";
import type { AnswerRecord, InterviewType } from "@/types/interview";

interface TechnicalScoreCardProps {
  score: number;
  interviewType: InterviewType;
  records: AnswerRecord[];
}

/** Technical knowledge score with its rubric breakdown. For HR interviews it scores answer content. */
export function TechnicalScoreCard({ score, interviewType, records }: TechnicalScoreCardProps) {
  const label = interviewType === "hr" ? "Answer Content" : "Technical Knowledge";
  const breakdown: [string, number | null][] = [
    ["Accuracy", averageOf(records, "technical_evaluation", "accuracy")],
    ["Completeness", averageOf(records, "technical_evaluation", "completeness")],
    ["Relevance", averageOf(records, "technical_evaluation", "relevance")],
    ["Depth", averageOf(records, "technical_evaluation", "depth")],
  ];
  const practical = averageOf(records, "technical_evaluation", "practical_reasoning");
  if (practical !== null) breakdown.push(["Practical Reasoning", practical]);

  return (
    <Card>
      <CardContent className="space-y-3 py-4">
        <div className="text-center">
          <p className="text-xs text-text-muted">{label}</p>
          <p className="mt-1 font-display text-3xl font-semibold text-text-primary" data-testid="technical-score">
            {score}
          </p>
        </div>
        <div className="grid grid-cols-2 gap-2">
          {breakdown.map(([name, value]) => (
            <ScoreCard key={name} label={name} score={value} />
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
