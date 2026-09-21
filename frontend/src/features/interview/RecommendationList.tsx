import { Link } from "react-router-dom";
import { ImprovementList } from "@/features/communication/ImprovementList";
import type { FinalEvaluation } from "@/types/interview";

interface RecommendationListProps {
  evaluation: Pick<FinalEvaluation, "recommended_practice" | "recommendations">;
}

/** "Recommended Practice": topics to study (linked to Cybersecurity Learning when one exists) plus next steps. */
export function RecommendationList({ evaluation }: RecommendationListProps) {
  const { recommended_practice, recommendations } = evaluation;
  if (recommended_practice.length === 0 && recommendations.length === 0) return null;

  return (
    <div className="space-y-4">
      <p className="text-sm font-semibold text-text-primary">Recommended Practice</p>
      {recommended_practice.length > 0 && (
        <ol className="space-y-1.5">
          {recommended_practice.map((item, index) => (
            <li key={`${item.slug ?? item.title}`} className="flex items-baseline gap-2 text-sm text-text-secondary">
              <span className="text-text-muted">{index + 1}.</span>
              {item.slug ? (
                <Link to={`/cybersecurity/${item.slug}`} className="text-link hover:underline">
                  {item.title}
                </Link>
              ) : (
                <span>{item.title}</span>
              )}
            </li>
          ))}
        </ol>
      )}
      <ImprovementList title="Next steps" items={recommendations} variant="neutral" />
    </div>
  );
}
