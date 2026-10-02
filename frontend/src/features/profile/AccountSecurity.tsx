import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { SectionCard } from "@/features/profile/SectionCard";
import { StatusMessage, type Flash } from "@/features/profile/StatusMessage";
import { inputClass, labelClass } from "@/features/profile/formStyles";
import { changePassword } from "@/services/profileService";
import { getApiErrorMessage } from "@/utils/apiError";
import { MIN_PASSWORD_LENGTH } from "@/utils/validators";

export function AccountSecurity({ email }: { email: string }) {
  return (
    <div className="space-y-6">
      <SectionCard title="Account" description="Your sign-in email. Changing it isn't supported yet.">
        <div>
          <label htmlFor="acct-email" className={labelClass}>Email</label>
          <input id="acct-email" className={inputClass} value={email} readOnly disabled />
        </div>
      </SectionCard>
      <ChangePasswordForm />
    </div>
  );
}

function ChangePasswordForm() {
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [flash, setFlash] = useState<Flash | null>(null);

  function validate(): string | null {
    if (!current) return "Enter your current password.";
    if (next.length < MIN_PASSWORD_LENGTH) return `Password must be at least ${MIN_PASSWORD_LENGTH} characters.`;
    if (next !== confirm) return "New passwords do not match.";
    return null;
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (isSaving) return;
    const problem = validate();
    if (problem) {
      setFlash({ type: "error", text: problem });
      return;
    }
    setIsSaving(true);
    setFlash(null);
    try {
      await changePassword({ current_password: current, new_password: next, confirm_new_password: confirm });
      // Don't keep passwords in state any longer than needed.
      setCurrent("");
      setNext("");
      setConfirm("");
      setFlash({ type: "success", text: "Password changed successfully." });
    } catch (err) {
      setFlash({ type: "error", text: getApiErrorMessage(err, "Unable to change password. Please try again.") });
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <SectionCard title="Change password" description={`Use at least ${MIN_PASSWORD_LENGTH} characters. You'll stay signed in on this device.`}>
      <form onSubmit={handleSubmit} className="space-y-4" noValidate>
        <div>
          <label htmlFor="pw-current" className={labelClass}>Current password</label>
          <input id="pw-current" type="password" className={inputClass} value={current} autoComplete="current-password"
            onChange={(e) => setCurrent(e.target.value)} />
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          <div>
            <label htmlFor="pw-new" className={labelClass}>New password</label>
            <input id="pw-new" type="password" className={inputClass} value={next} autoComplete="new-password"
              onChange={(e) => setNext(e.target.value)} />
          </div>
          <div>
            <label htmlFor="pw-confirm" className={labelClass}>Confirm new password</label>
            <input id="pw-confirm" type="password" className={inputClass} value={confirm} autoComplete="new-password"
              onChange={(e) => setConfirm(e.target.value)} />
          </div>
        </div>
        <div className="flex flex-col gap-3 border-t border-border pt-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="min-w-0 flex-1">
            <StatusMessage flash={flash} onDismiss={() => setFlash(null)} />
          </div>
          <Button type="submit" disabled={isSaving}>
            {isSaving ? "Changing password..." : "Change password"}
          </Button>
        </div>
      </form>
    </SectionCard>
  );
}
