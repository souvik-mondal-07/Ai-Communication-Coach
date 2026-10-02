import { useState } from "react";
import { SectionCard } from "@/features/profile/SectionCard";
import { hintClass, inputClass, labelClass } from "@/features/profile/formStyles";
import { useSave } from "@/features/profile/useSave";
import { useProfileStore } from "@/store/profileStore";
import { EXPERIENCE_LEVELS, FIELD_LIMITS, type ExperienceLevel, type UserProfile } from "@/types/profile";

export function PersonalInfoForm({ user }: { user: UserProfile }) {
  const saveProfile = useProfileStore((s) => s.saveProfile);
  const [fullName, setFullName] = useState(user.full_name);
  const [bio, setBio] = useState(user.profile.bio);
  const [education, setEducation] = useState(user.profile.education);
  const [careerGoal, setCareerGoal] = useState(user.profile.career_goal);
  const [level, setLevel] = useState<ExperienceLevel | "">(user.profile.experience_level ?? "");
  const [nameError, setNameError] = useState<string | null>(null);
  const { isSaving, flash, run, dismiss } = useSave("Profile updated successfully.", "Unable to update profile. Please try again.");

  const dirty =
    fullName.trim() !== user.full_name ||
    bio.trim() !== user.profile.bio ||
    education.trim() !== user.profile.education ||
    careerGoal.trim() !== user.profile.career_goal ||
    (level !== "" && level !== user.profile.experience_level);

  function handleSave() {
    if (!fullName.trim()) {
      setNameError("Full name is required.");
      return;
    }
    setNameError(null);
    void run(() =>
      saveProfile({
        full_name: fullName.trim(),
        bio: bio.trim(),
        education: education.trim(),
        career_goal: careerGoal.trim(),
        ...(level !== "" ? { experience_level: level } : {}),
      })
    );
  }

  return (
    <SectionCard
      title="Personal information"
      description="Helps your mentor address you and pitch explanations at the right level."
      onSave={handleSave}
      isSaving={isSaving}
      isDirty={dirty}
      flash={flash}
      onDismissFlash={dismiss}
    >
      <div className="grid gap-5 md:grid-cols-2">
        <div>
          <label htmlFor="pf-name" className={labelClass}>Full name</label>
          <input id="pf-name" className={inputClass} value={fullName} maxLength={FIELD_LIMITS.name}
            onChange={(e) => setFullName(e.target.value)} autoComplete="name" aria-invalid={nameError !== null} />
          {nameError && <p className="mt-1 text-xs text-danger">{nameError}</p>}
        </div>
        <div>
          <label htmlFor="pf-level" className={labelClass}>Experience level</label>
          <select id="pf-level" className={inputClass} value={level}
            onChange={(e) => setLevel(e.target.value as ExperienceLevel | "")}>
            <option value="" disabled>Select a level</option>
            {EXPERIENCE_LEVELS.map((l) => <option key={l.value} value={l.value}>{l.label}</option>)}
          </select>
        </div>
        <div>
          <label htmlFor="pf-edu" className={labelClass}>Education</label>
          <input id="pf-edu" className={inputClass} value={education} maxLength={FIELD_LIMITS.education}
            placeholder="e.g. B.Tech in Computer Science" onChange={(e) => setEducation(e.target.value)} />
        </div>
        <div>
          <label htmlFor="pf-goal" className={labelClass}>Career goal</label>
          <input id="pf-goal" className={inputClass} value={careerGoal} maxLength={FIELD_LIMITS.careerGoal}
            placeholder="e.g. Penetration Tester" onChange={(e) => setCareerGoal(e.target.value)} />
        </div>
        <div className="md:col-span-2">
          <label htmlFor="pf-bio" className={labelClass}>Bio</label>
          <textarea id="pf-bio" className={inputClass} rows={4} value={bio} maxLength={FIELD_LIMITS.bio}
            placeholder="A few lines about your background and what you want to achieve."
            onChange={(e) => setBio(e.target.value)} />
          <p className={hintClass}>{bio.length}/{FIELD_LIMITS.bio}</p>
        </div>
      </div>
    </SectionCard>
  );
}
