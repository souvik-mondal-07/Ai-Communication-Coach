import { useState } from "react";
import { X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ChipSelect } from "@/features/profile/ChipSelect";
import { SectionCard } from "@/features/profile/SectionCard";
import { hintClass, inputClass, labelClass } from "@/features/profile/formStyles";
import { useSave } from "@/features/profile/useSave";
import { useProfileStore } from "@/store/profileStore";
import {
  CYBERSECURITY_INTERESTS,
  FIELD_LIMITS,
  LEARNING_GOALS,
  MAX_CUSTOM_GOALS,
  type CybersecurityInterest,
  type LearningGoal,
  type UserProfile,
} from "@/types/profile";

const same = (a: readonly unknown[], b: readonly unknown[]) => JSON.stringify(a) === JSON.stringify(b);

export function CybersecurityProfileForm({ user }: { user: UserProfile }) {
  const saveProfile = useProfileStore((s) => s.saveProfile);
  const [interests, setInterests] = useState<CybersecurityInterest[]>(user.profile.cybersecurity_interests);
  const [goals, setGoals] = useState<LearningGoal[]>(user.profile.learning_goals);
  const [custom, setCustom] = useState<string[]>(user.profile.custom_learning_goals);
  const [draft, setDraft] = useState("");
  const { isSaving, flash, run, dismiss } = useSave("Profile updated successfully.", "Unable to update profile. Please try again.");

  const dirty =
    !same(interests, user.profile.cybersecurity_interests) ||
    !same(goals, user.profile.learning_goals) ||
    !same(custom, user.profile.custom_learning_goals);

  function addCustom() {
    const text = draft.trim();
    if (!text || custom.length >= MAX_CUSTOM_GOALS) return;
    if (!custom.some((c) => c.toLowerCase() === text.toLowerCase())) setCustom([...custom, text]);
    setDraft("");
  }

  return (
    <SectionCard
      title="Cybersecurity profile"
      description="Pick what you care about. Your mentor will use this to tailor practice in later updates."
      onSave={() =>
        void run(() =>
          saveProfile({
            cybersecurity_interests: interests,
            learning_goals: goals,
            custom_learning_goals: custom,
          })
        )
      }
      isSaving={isSaving}
      isDirty={dirty}
      flash={flash}
      onDismissFlash={dismiss}
    >
      <div>
        <p className={labelClass}>Cybersecurity interests</p>
        <ChipSelect label="Cybersecurity interests" options={CYBERSECURITY_INTERESTS} value={interests} onChange={setInterests} />
      </div>

      <div>
        <p className={labelClass}>Learning goals</p>
        <ChipSelect label="Learning goals" options={LEARNING_GOALS} value={goals} onChange={setGoals} />
      </div>

      <div>
        <label htmlFor="pf-custom-goal" className={labelClass}>Custom goals (optional)</label>
        <div className="flex gap-2">
          <input
            id="pf-custom-goal"
            className={inputClass}
            value={draft}
            maxLength={FIELD_LIMITS.customGoal}
            disabled={custom.length >= MAX_CUSTOM_GOALS}
            placeholder="e.g. Pass the OSCP exam"
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                addCustom();
              }
            }}
          />
          <Button type="button" variant="secondary" onClick={addCustom} disabled={!draft.trim() || custom.length >= MAX_CUSTOM_GOALS}>
            Add
          </Button>
        </div>
        <p className={hintClass}>Up to {MAX_CUSTOM_GOALS} custom goals.</p>
        {custom.length > 0 && (
          <ul className="mt-3 flex flex-wrap gap-2">
            {custom.map((goal) => (
              <li key={goal} className="flex max-w-full items-center gap-1.5 rounded-full border border-signal bg-signal/10 py-1 pl-3 pr-1.5 text-sm text-signal">
                <span className="truncate">{goal}</span>
                <button
                  type="button"
                  aria-label={`Remove goal ${goal}`}
                  onClick={() => setCustom(custom.filter((c) => c !== goal))}
                  className="rounded-full p-0.5 hover:bg-signal/20"
                >
                  <X size={14} />
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </SectionCard>
  );
}
