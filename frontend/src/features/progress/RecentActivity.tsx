import type { ActivityItem } from "@/types/progress";

export function RecentActivity({ activity }: { activity: ActivityItem[] }) {
  if (activity.length === 0) {
    return <p className="text-sm text-text-muted">No activity yet. Complete a session to see it here.</p>;
  }
  return (
    <ul className="space-y-2">
      {activity.map((item, index) => (
        <li
          key={`${item.type}-${item.completed_at}-${index}`}
          className="flex items-center justify-between gap-3 border-b border-border pb-2 text-sm last:border-b-0 last:pb-0"
        >
          <span className="text-text-primary">{item.label}</span>
          <span className="shrink-0 text-xs text-text-muted">
            {item.score !== null ? `${item.score}/100 · ` : ""}
            {new Date(item.completed_at).toLocaleDateString()}
          </span>
        </li>
      ))}
    </ul>
  );
}
