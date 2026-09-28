import { Sparkles } from "lucide-react";
import type { PersonalProfile } from "@/types/progress";

function Chips({ items, emptyText }: { items: string[]; emptyText: string }) {
  if (items.length === 0) {
    return <p className="text-xs text-text-muted">{emptyText}</p>;
  }
  return (
    <div className="flex flex-wrap gap-1.5">
      {items.map((item) => (
        <span
          key={item}
          className="rounded-full border border-border bg-surface-raised px-2.5 py-0.5 text-[11px] text-text-secondary"
        >
          {item}
        </span>
      ))}
    </div>
  );
}

export function PersonalProfileCard({ profile }: { profile: PersonalProfile }) {
  const hasAnyData =
    profile.technical_profile.strong_areas.length > 0 ||
    profile.technical_profile.weak_areas.length > 0 ||
    profile.recent_focus.length > 0 ||
    profile.recommended_focus.length > 0;

  if (!hasAnyData) {
    return (
      <p className="text-sm text-text-muted">
        Start practicing to build your personal AI profile. It will summarize your strengths, areas to improve,
        and recommended focus as your progress data grows.
      </p>
    );
  }

  return (
    <div className="space-y-4">
      {profile.ai_summary?.summary && (
        <div className="rounded-[var(--radius-panel)] border border-signal/30 bg-signal/5 p-3">
          <div className="mb-1.5 flex items-center gap-1.5 text-[11px] font-medium text-signal">
            <Sparkles size={12} />
            AI SUMMARY (generated from the stats below)
          </div>
          <p className="text-sm text-text-primary">{profile.ai_summary.summary}</p>
        </div>
      )}

      <div>
        <p className="mb-1.5 text-xs font-medium text-text-secondary">Current focus</p>
        <Chips items={profile.recent_focus} emptyText="No recent focus yet." />
      </div>

      <div>
        <p className="mb-1.5 text-xs font-medium text-text-secondary">Strong areas</p>
        <Chips items={profile.technical_profile.strong_areas} emptyText="Nothing consistently strong yet." />
      </div>

      <div>
        <p className="mb-1.5 text-xs font-medium text-text-secondary">Areas to improve</p>
        <Chips
          items={[
            ...profile.technical_profile.weak_areas,
            ...profile.communication_profile.improvement_areas,
            ...profile.interview_profile.improvement_areas,
            ...profile.pressure_profile.improvement_areas,
          ]}
          emptyText="No repeated weak areas detected."
        />
      </div>

      <div>
        <p className="mb-1.5 text-xs font-medium text-text-secondary">Recommended next focus</p>
        <Chips items={profile.recommended_focus} emptyText="No active recommendations." />
      </div>
    </div>
  );
}
