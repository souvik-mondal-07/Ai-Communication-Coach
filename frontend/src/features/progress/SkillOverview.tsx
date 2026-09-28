import type { CtfBreakdownRow, SkillBreakdownRow } from "@/types/progress";

function barColor(status: SkillBreakdownRow["status"]): string {
  if (status === "strong") return "bg-signal";
  if (status === "weak") return "bg-danger";
  return "bg-warn";
}

function scoreTextColor(status: SkillBreakdownRow["status"]): string {
  if (status === "strong") return "text-signal";
  if (status === "weak") return "text-danger";
  return "text-warn";
}

export function SkillOverview({ skills }: { skills: SkillBreakdownRow[] }) {
  if (skills.length === 0) {
    return (
      <p className="text-sm text-text-muted">
        Start practicing to build your personal progress profile. Skill breakdowns will appear here once you've
        completed a few practice sessions.
      </p>
    );
  }

  const sorted = [...skills].sort((a, b) => b.average_score - a.average_score);

  return (
    <ul className="space-y-3">
      {sorted.map((skill) => (
        <li key={skill.skill}>
          <div className="mb-1 flex items-center justify-between text-sm">
            <span className="text-text-primary">{skill.category}</span>
            <span className={`font-medium ${scoreTextColor(skill.status)}`}>{skill.average_score}</span>
          </div>
          <div className="h-1.5 w-full overflow-hidden rounded-full bg-surface-raised">
            <div
              className={`h-full rounded-full ${barColor(skill.status)}`}
              style={{ width: `${Math.max(4, skill.average_score)}%` }}
            />
          </div>
          <p className="mt-1 text-[11px] text-text-muted">
            {skill.attempts} attempt{skill.attempts === 1 ? "" : "s"} · {skill.level}
          </p>
        </li>
      ))}
    </ul>
  );
}

export function CtfActivityOverview({ activity }: { activity: CtfBreakdownRow[] }) {
  if (activity.length === 0) {
    return <p className="text-sm text-text-muted">No CTF sessions yet.</p>;
  }
  return (
    <ul className="space-y-2">
      {activity.map((row) => (
        <li
          key={row.category}
          className="flex items-center justify-between rounded-[var(--radius-panel)] border border-border px-3 py-2 text-sm"
        >
          <span className="text-text-primary">{row.category.replace(/_/g, " ")}</span>
          <span className="text-xs text-text-secondary">
            {row.completed}/{row.attempts} completed ({row.completion_rate}%)
          </span>
        </li>
      ))}
    </ul>
  );
}
