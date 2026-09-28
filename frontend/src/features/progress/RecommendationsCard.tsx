import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import type { Recommendation, RecommendationType } from "@/types/progress";

const TYPE_ROUTE: Record<RecommendationType, string> = {
  practice: "/cybersecurity",
  ctf: "/ctf",
  communication: "/communication",
  interview: "/interview",
  pressure: "/pressure-training",
};

const TYPE_ACTION_LABEL: Record<RecommendationType, string> = {
  practice: "Start Practice",
  ctf: "Start CTF",
  communication: "Start Communication",
  interview: "Start Interview",
  pressure: "Start Pressure Training",
};

const PRIORITY_COLOR: Record<Recommendation["priority"], string> = {
  high: "text-danger",
  medium: "text-warn",
  low: "text-text-secondary",
};

interface RecommendationsCardProps {
  recommendations: Recommendation[];
  onComplete: (id: string) => void;
  completingId?: string | null;
}

export function RecommendationsCard({ recommendations, onComplete, completingId }: RecommendationsCardProps) {
  if (recommendations.length === 0) {
    return (
      <p className="text-sm text-text-muted">
        Complete a few sessions and we'll suggest what to focus on next, based on your actual performance.
      </p>
    );
  }

  return (
    <ul className="space-y-4">
      {recommendations.map((rec) => (
        <li key={rec._id} className="rounded-[var(--radius-panel)] border border-border p-3">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-sm font-medium text-text-primary">{rec.area}</p>
              <p className="mt-0.5 text-xs text-text-secondary">{rec.reason}</p>
            </div>
            <span className={`shrink-0 text-[11px] font-medium uppercase ${PRIORITY_COLOR[rec.priority]}`}>
              {rec.priority}
            </span>
          </div>
          <div className="mt-3 flex items-center gap-2">
            <Link to={TYPE_ROUTE[rec.type]}>
              <Button variant="secondary" size="sm">
                {TYPE_ACTION_LABEL[rec.type]}
              </Button>
            </Link>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onComplete(rec._id)}
              disabled={completingId === rec._id}
            >
              {completingId === rec._id ? "Marking done…" : "Mark done"}
            </Button>
          </div>
        </li>
      ))}
    </ul>
  );
}
