import { useState } from "react";
import { AccountSecurity } from "@/features/profile/AccountSecurity";
import { ProfileLoadState } from "@/features/profile/ProfileLoadState";
import {
  AiPreferences,
  AppearanceSettings,
  InterviewPreferences,
  LearningPreferences,
} from "@/features/profile/SettingsSections";
import { cn } from "@/lib/utils";
import { useProfileStore } from "@/store/profileStore";

const TABS = [
  { id: "appearance", label: "Appearance" },
  { id: "ai", label: "AI Preferences" },
  { id: "learning", label: "Learning" },
  { id: "interview", label: "Interview" },
  { id: "security", label: "Account Security" },
] as const;

type TabId = (typeof TABS)[number]["id"];

export default function Settings() {
  const profile = useProfileStore((s) => s.profile);
  const [tab, setTab] = useState<TabId>("appearance");

  if (!profile) return <ProfileLoadState />;
  const prefs = profile.preferences;

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      {/* Scrolls inside its own box on narrow screens so the page never overflows. */}
      <div role="tablist" aria-label="Settings sections" className="flex gap-1 overflow-x-auto border-b border-border">
        {TABS.map((t) => (
          <button
            key={t.id}
            id={`tab-${t.id}`}
            role="tab"
            type="button"
            aria-selected={tab === t.id}
            aria-controls={`panel-${t.id}`}
            onClick={() => setTab(t.id)}
            className={cn(
              "-mb-px shrink-0 border-b-2 px-3 py-2.5 text-sm transition-colors",
              tab === t.id
                ? "border-signal text-signal"
                : "border-transparent text-text-secondary hover:text-text-primary"
            )}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div role="tabpanel" id={`panel-${tab}`} aria-labelledby={`tab-${tab}`}>
        {tab === "appearance" && <AppearanceSettings prefs={prefs} />}
        {tab === "ai" && <AiPreferences prefs={prefs} />}
        {tab === "learning" && <LearningPreferences prefs={prefs} />}
        {tab === "interview" && <InterviewPreferences prefs={prefs} />}
        {tab === "security" && <AccountSecurity email={profile.email} />}
      </div>
    </div>
  );
}
