import { Card, CardContent } from "@/components/ui/card";
import { EXPERIENCE_LEVELS, type UserProfile } from "@/types/profile";

function initialsOf(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  const first = parts[0][0];
  const last = parts.length > 1 ? parts[parts.length - 1][0] : "";
  return (first + last).toUpperCase();
}

export function ProfileHeader({ user }: { user: UserProfile }) {
  const level = EXPERIENCE_LEVELS.find((l) => l.value === user.profile.experience_level)?.label;
  const pct = user.completion.percentage;

  return (
    <Card>
      <CardContent className="flex flex-col items-center gap-5 py-6 text-center sm:flex-row sm:text-left">
        <div
          aria-hidden="true"
          className="flex h-20 w-20 shrink-0 items-center justify-center rounded-full bg-signal/15 font-display text-2xl font-semibold text-signal"
        >
          {initialsOf(user.full_name)}
        </div>

        <div className="min-w-0 flex-1">
          <h2 className="truncate font-display text-xl font-semibold text-text-primary">{user.full_name}</h2>
          <p className="truncate text-sm text-text-secondary">{user.email}</p>
          <p className="mt-1 text-sm text-text-muted">
            {user.profile.career_goal || "Add your career goal"}
            {level ? ` · ${level}` : ""}
          </p>
        </div>

        <div className="w-full sm:w-56">
          <div className="mb-1.5 flex justify-between text-xs text-text-secondary">
            <span>Profile completion</span>
            <span className="font-medium text-text-primary">{pct}%</span>
          </div>
          <div
            role="progressbar"
            aria-valuenow={pct}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label="Profile completion"
            className="h-2 overflow-hidden rounded-full bg-surface-raised"
          >
            <div className="h-full rounded-full bg-signal transition-all" style={{ width: `${pct}%` }} />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
