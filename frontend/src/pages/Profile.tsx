import { Link } from "react-router-dom";
import { CompletionCard } from "@/features/profile/CompletionCard";
import { CybersecurityProfileForm } from "@/features/profile/CybersecurityProfileForm";
import { PersonalInfoForm } from "@/features/profile/PersonalInfoForm";
import { ProfileHeader } from "@/features/profile/ProfileHeader";
import { ProfileLoadState } from "@/features/profile/ProfileLoadState";
import { useProfileStore } from "@/store/profileStore";

export default function Profile() {
  const profile = useProfileStore((s) => s.profile);

  if (!profile) return <ProfileLoadState />;

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <ProfileHeader user={profile} />
      <div className="grid gap-6 lg:grid-cols-3">
        <div className="min-w-0 space-y-6 lg:col-span-2">
          <PersonalInfoForm user={profile} />
          <CybersecurityProfileForm user={profile} />
        </div>
        <div className="min-w-0 space-y-6">
          <CompletionCard user={profile} />
          <p className="text-xs text-text-muted">
            Mentor style, difficulty and interview preferences live in{" "}
            <Link to="/settings" className="text-link hover:underline">Settings</Link>.
          </p>
        </div>
      </div>
    </div>
  );
}
