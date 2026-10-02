import { useState } from "react";
import { ChipSelect } from "@/features/profile/ChipSelect";
import { OptionGroup } from "@/features/profile/OptionGroup";
import { SectionCard } from "@/features/profile/SectionCard";
import { labelClass } from "@/features/profile/formStyles";
import { useSave } from "@/features/profile/useSave";
import { useProfileStore } from "@/store/profileStore";
import {
  INTERVIEW_FOCUS_AREAS,
  LEARNING_DIFFICULTIES,
  LEARNING_STYLES,
  RESPONSE_STYLES,
  THEMES,
  type InterviewFocus,
  type LearningDifficulty,
  type LearningStyle,
  type ResponseStyle,
  type ThemePreference,
  type UserPreferences,
} from "@/types/profile";
import { applyTheme } from "@/utils/theme";

const SAVED = "Settings saved successfully.";
const FAILED = "Unable to save settings. Please try again.";

export function AppearanceSettings({ prefs }: { prefs: UserPreferences }) {
  const savePreferences = useProfileStore((s) => s.savePreferences);
  const { isSaving, flash, run, dismiss } = useSave(SAVED, FAILED);

  // Applies instantly, saves in the background, and rolls back if the save fails.
  function choose(theme: ThemePreference) {
    if (theme === prefs.theme || isSaving) return;
    const previous = prefs.theme;
    applyTheme(theme);
    void run(async () => {
      try {
        await savePreferences({ theme });
      } catch (err) {
        applyTheme(previous);
        throw err;
      }
    });
  }

  return (
    <SectionCard title="Appearance" description="Choose how the app looks. Saved to your account." flash={flash} onDismissFlash={dismiss}>
      <div>
        <p className={labelClass}>Theme</p>
        <OptionGroup label="Theme" options={THEMES} value={prefs.theme} onChange={choose} />
      </div>
      {flash && (
        <p className="text-xs text-text-muted" aria-live="polite">
          {flash.text}
        </p>
      )}
    </SectionCard>
  );
}

export function AiPreferences({ prefs }: { prefs: UserPreferences }) {
  const savePreferences = useProfileStore((s) => s.savePreferences);
  const [style, setStyle] = useState<ResponseStyle>(prefs.response_style);
  const { isSaving, flash, run, dismiss } = useSave(SAVED, FAILED);
  return (
    <SectionCard
      title="AI preferences"
      description="How should your mentor explain things?"
      onSave={() => void run(() => savePreferences({ response_style: style }))}
      isSaving={isSaving}
      isDirty={style !== prefs.response_style}
      flash={flash}
      onDismissFlash={dismiss}
    >
      <div>
        <p className={labelClass}>Response style</p>
        <OptionGroup label="Response style" options={RESPONSE_STYLES} value={style} onChange={setStyle} />
      </div>
    </SectionCard>
  );
}

export function LearningPreferences({ prefs }: { prefs: UserPreferences }) {
  const savePreferences = useProfileStore((s) => s.savePreferences);
  const [difficulty, setDifficulty] = useState<LearningDifficulty>(prefs.difficulty);
  const [style, setStyle] = useState<LearningStyle>(prefs.learning_style);
  const { isSaving, flash, run, dismiss } = useSave(SAVED, FAILED);
  return (
    <SectionCard
      title="Learning preferences"
      description="Stored now so practice can be personalized in later updates."
      onSave={() => void run(() => savePreferences({ difficulty, learning_style: style }))}
      isSaving={isSaving}
      isDirty={difficulty !== prefs.difficulty || style !== prefs.learning_style}
      flash={flash}
      onDismissFlash={dismiss}
    >
      <div>
        <p className={labelClass}>Learning difficulty</p>
        <OptionGroup label="Learning difficulty" options={LEARNING_DIFFICULTIES} value={difficulty} onChange={setDifficulty} />
      </div>
      <div>
        <p className={labelClass}>Learning style</p>
        <OptionGroup label="Learning style" options={LEARNING_STYLES} value={style} onChange={setStyle} />
      </div>
    </SectionCard>
  );
}

export function InterviewPreferences({ prefs }: { prefs: UserPreferences }) {
  const savePreferences = useProfileStore((s) => s.savePreferences);
  const [focus, setFocus] = useState<InterviewFocus[]>(prefs.interview_focus);
  const { isSaving, flash, run, dismiss } = useSave(SAVED, FAILED);
  return (
    <SectionCard
      title="Interview preferences"
      description="Optional. Choose the areas you most want to be interviewed on."
      onSave={() => void run(() => savePreferences({ interview_focus: focus }))}
      isSaving={isSaving}
      isDirty={JSON.stringify(focus) !== JSON.stringify(prefs.interview_focus)}
      flash={flash}
      onDismissFlash={dismiss}
    >
      <div>
        <p className={labelClass}>Focus areas</p>
        <ChipSelect label="Interview focus areas" options={INTERVIEW_FOCUS_AREAS} value={focus} onChange={setFocus} />
      </div>
    </SectionCard>
  );
}
