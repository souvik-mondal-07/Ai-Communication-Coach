import { Card, CardContent } from "@/components/ui/card";
import { ScoreCard } from "@/features/communication/ScoreCard";
import { averageOf } from "@/features/interview/scoreUtils";
import type { AnswerRecord } from "@/types/interview";

interface CommunicationScoreCardProps {
  score: number;
  records: AnswerRecord[];
}

const DIMENSIONS: [string, string][] = [
  ["Clarity", "clarity"],
  ["Grammar", "grammar"],
  ["Vocabulary", "vocabulary"],
  ["Structure", "structure"],
  ["Conciseness", "conciseness"],
  ["Professionalism", "professionalism"],
];

/** Communication score (kept separate from technical) with its rubric breakdown. */
export function CommunicationScoreCard({ score, records }: CommunicationScoreCardProps) {
  return (
    <Card>
      <CardContent className="space-y-3 py-4">
        <div className="text-center">
          <p className="text-xs text-text-muted">Communication</p>
          <p className="mt-1 font-display text-3xl font-semibold text-text-primary" data-testid="communication-score">
            {score}
          </p>
        </div>
        <div className="grid grid-cols-2 gap-2">
          {DIMENSIONS.map(([label, key]) => (
            <ScoreCard key={key} label={label} score={averageOf(records, "communication_evaluation", key)} />
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
