import type { Weakness } from "@/types/progress";

const SEVERITY_COLOR: Record<Weakness["severity"], string> = {
  high: "text-danger",
  medium: "text-warn",
  low: "text-text-secondary",
};

const SOURCE_LABEL: Record<Weakness["source"], string> = {
  cybersecurity_practice: "Practice",
  interview: "Interview",
  communication: "Communication",
  pressure: "Pressure training",
};

export function WeaknessesCard({ weaknesses }: { weaknesses: Weakness[] }) {
  if (weaknesses.length === 0) {
    return (
      <p className="text-sm text-text-muted">
        Not enough data yet. Complete a few more sessions in each area to see where you need more practice.
      </p>
    );
  }
  return (
    <ul className="space-y-2.5">
      {weaknesses.map((weakness) => (
        <li key={weakness._id}>
          <div className="flex items-center justify-between text-sm">
            <span className="text-text-primary">{weakness.area}</span>
            <span className={`text-xs font-medium ${SEVERITY_COLOR[weakness.severity]}`}>
              avg {weakness.evidence.average_score}
            </span>
          </div>
          <p className="text-[11px] text-text-muted">
            {SOURCE_LABEL[weakness.source]} · {weakness.evidence.attempts} attempts
          </p>
        </li>
      ))}
    </ul>
  );
}
