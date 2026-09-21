import { ImprovementList } from "@/features/communication/ImprovementList";
import type { FinalEvaluation } from "@/types/interview";

interface WeaknessListProps {
  evaluation: Pick<
    FinalEvaluation,
    "weaknesses" | "technical_weaknesses" | "communication_weaknesses" | "weak_topics"
  >;
}

/** "Areas to Improve": overall weaknesses plus technical / communication detail and weak topics from this interview. */
export function WeaknessList({ evaluation }: WeaknessListProps) {
  const { weaknesses, technical_weaknesses, communication_weaknesses, weak_topics } = evaluation;
  const nothing =
    weaknesses.length + technical_weaknesses.length + communication_weaknesses.length + weak_topics.length === 0;

  return (
    <div className="space-y-4">
      <p className="text-sm font-semibold text-text-primary">Areas to Improve</p>
      {nothing && <p className="text-sm text-text-secondary">No significant weaknesses were identified. Nice work.</p>}
      <ImprovementList title="Overall" items={weaknesses} variant="negative" />
      <ImprovementList title="Technical" items={technical_weaknesses} variant="negative" />
      <ImprovementList title="Communication" items={communication_weaknesses} variant="negative" />
      {weak_topics.length > 0 && (
        <div>
          <p className="mb-1.5 text-xs font-medium text-text-muted">Weaker topic areas in this interview</p>
          <ul className="flex flex-wrap gap-2">
            {weak_topics.map((t) => (
              <li
                key={t.topic}
                className="rounded-full border border-warn/40 bg-warn/10 px-2.5 py-1 text-xs text-warn"
              >
                {t.label} · {t.average_score}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
