import { Flame } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { streakHeadline, streakHint } from "@/components/dashboard/dailyPracticeUtils";
import type { Streak } from "@/types/dailyPractice";

/** Inline flame + streak, used inside other cards. */
export function StreakBadge({ streak }: { streak: Streak }) {
  return (
    <span className="inline-flex items-center gap-1 text-sm font-medium text-text-primary" aria-label={streakHeadline(streak)}>
      <Flame size={16} className={streak.current_streak > 0 ? "text-warn" : "text-text-muted"} aria-hidden="true" />
      {streakHeadline(streak)}
    </span>
  );
}

/** Full streak card: current, longest, total active days and the counting rule. */
export function StreakCard({ streak }: { streak: Streak }) {
  return (
    <Card>
      <CardContent className="space-y-3 py-5">
        <StreakBadge streak={streak} />
        <p className="text-xs text-text-secondary">{streakHint(streak)}</p>
        <dl className="grid grid-cols-3 gap-2 text-center">
          {[
            ["Current", streak.current_streak],
            ["Longest", streak.longest_streak],
            ["Active days", streak.total_active_days],
          ].map(([label, value]) => (
            <div key={label} className="rounded-[var(--radius-panel)] border border-border bg-surface-raised px-2 py-2">
              <dt className="text-[11px] text-text-muted">{label}</dt>
              <dd className="font-display text-lg font-semibold text-text-primary">{value}</dd>
            </div>
          ))}
        </dl>
        <p className="text-[11px] text-text-muted">
          A day counts once you finish at least one practice activity. Opening the app does not count. Days follow your
          timezone ({streak.timezone}).
        </p>
      </CardContent>
    </Card>
  );
}
