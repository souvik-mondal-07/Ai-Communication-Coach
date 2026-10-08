import { useState } from "react";
import { ToggleRow } from "@/features/profile/ToggleRow";
import { ChipSelect } from "@/features/profile/ChipSelect";
import { SectionCard } from "@/features/profile/SectionCard";
import { hintClass, inputClass, labelClass } from "@/features/profile/formStyles";
import { useSave } from "@/features/profile/useSave";
import { detectTimezone } from "@/hooks/useReminderSync";
import { cn } from "@/lib/utils";
import {
  getBrowserPermission,
  requestBrowserPermission,
  type BrowserPermission,
} from "@/services/browserNotificationService";
import { useProfileStore } from "@/store/profileStore";
import { PRACTICE_MINUTE_OPTIONS, WEEKDAYS, type UserPreferences, type Weekday } from "@/types/profile";

const SAVED = "Settings saved successfully.";
const FAILED = "Unable to save settings. Please try again.";

function timezoneOptions(current: string | null): string[] {
  let zones: string[] = [];
  try {
    zones = (Intl as unknown as { supportedValuesOf?: (k: string) => string[] }).supportedValuesOf?.("timeZone") ?? [];
  } catch {
    zones = [];
  }
  const extra = [current, detectTimezone(), "UTC"].filter((z): z is string => Boolean(z));
  return Array.from(new Set([...extra, ...zones]));
}

export function PracticePreferences({ prefs }: { prefs: UserPreferences }) {
  const savePreferences = useProfileStore((s) => s.savePreferences);
  const [enabled, setEnabled] = useState(prefs.daily_practice_enabled);
  const [minutes, setMinutes] = useState(prefs.daily_practice_minutes);
  const [time, setTime] = useState(prefs.preferred_practice_time);
  const initialTz = prefs.preferred_timezone ?? detectTimezone() ?? "UTC";
  const [tz, setTz] = useState(initialTz);
  const [days, setDays] = useState<Weekday[]>(prefs.practice_days);
  const { isSaving, flash, run, dismiss } = useSave(SAVED, FAILED);

  const dirty =
    enabled !== prefs.daily_practice_enabled ||
    minutes !== prefs.daily_practice_minutes ||
    time !== prefs.preferred_practice_time ||
    tz !== initialTz ||
    JSON.stringify([...days].sort()) !== JSON.stringify([...prefs.practice_days].sort());
  const valid = days.length > 0 && /^([01]\d|2[0-3]):[0-5]\d$/.test(time);

  return (
    <SectionCard
      title="Practice preferences"
      description="Your daily practice is built from your goals, weaknesses and recent results."
      onSave={() =>
        void run(() =>
          savePreferences({
            daily_practice_enabled: enabled,
            daily_practice_minutes: minutes,
            preferred_practice_time: time,
            preferred_timezone: tz,
            practice_days: days,
          })
        )
      }
      isSaving={isSaving}
      isDirty={dirty && valid}
      flash={flash}
      onDismissFlash={dismiss}
    >
      <ToggleRow label="Daily practice" description="Show a personalized practice plan each day." checked={enabled} onChange={setEnabled} />

      <div>
        <p className={labelClass}>Daily goal</p>
        <div role="radiogroup" aria-label="Daily goal in minutes" className="flex flex-wrap gap-2">
          {PRACTICE_MINUTE_OPTIONS.map((m) => (
            <button
              key={m}
              type="button"
              role="radio"
              aria-checked={minutes === m}
              onClick={() => setMinutes(m)}
              className={cn(
                "rounded-full border px-3 py-1.5 text-sm",
                minutes === m ? "border-signal bg-signal/15 text-signal" : "border-border text-text-secondary hover:border-border-strong"
              )}
            >
              {m} min
            </button>
          ))}
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <label htmlFor="practice-time" className={labelClass}>Preferred practice time</label>
          <input id="practice-time" type="time" className={inputClass} value={time} onChange={(e) => setTime(e.target.value)} />
          <p className={hintClass}>Reminders are not sent before this time.</p>
        </div>
        <div>
          <label htmlFor="practice-tz" className={labelClass}>Timezone</label>
          <select id="practice-tz" className={inputClass} value={tz} onChange={(e) => setTz(e.target.value)}>
            {timezoneOptions(prefs.preferred_timezone).map((z) => (
              <option key={z} value={z}>{z}</option>
            ))}
          </select>
          <p className={hintClass}>Decides when your day, and your streak, starts and ends.</p>
        </div>
      </div>

      <div>
        <p className={labelClass}>Practice days</p>
        <ChipSelect label="Practice days" options={WEEKDAYS} value={days} onChange={setDays} />
        <p className={hintClass}>
          {days.length === 0 ? "Choose at least one day." : "Days you skip never break your streak."}
        </p>
      </div>
    </SectionCard>
  );
}

const PERMISSION_TEXT: Record<BrowserPermission, string> = {
  granted: "Browser notifications are allowed for this site.",
  denied: "Browser notifications are blocked. Allow them in your browser's site settings to use this.",
  default: "Your browser will ask for permission when you turn this on.",
  unsupported: "This browser doesn't support notifications.",
};

export function NotificationPreferences({ prefs }: { prefs: UserPreferences }) {
  const savePreferences = useProfileStore((s) => s.savePreferences);
  const [reminders, setReminders] = useState(prefs.reminders_enabled);
  const [interview, setInterview] = useState(prefs.interview_reminders_enabled);
  const [communication, setCommunication] = useState(prefs.communication_reminders_enabled);
  const [cyber, setCyber] = useState(prefs.cybersecurity_reminders_enabled);
  const [browser, setBrowser] = useState(prefs.browser_notifications_enabled);
  const [permission, setPermission] = useState<BrowserPermission>(getBrowserPermission());
  const { isSaving, flash, run, dismiss } = useSave(SAVED, FAILED);

  // Called from the click on the switch (a user action), after the explanation below is visible.
  async function toggleBrowser(next: boolean) {
    if (!next) {
      setBrowser(false);
      return;
    }
    const result = await requestBrowserPermission();
    setPermission(result);
    setBrowser(result === "granted");
  }

  const dirty =
    reminders !== prefs.reminders_enabled ||
    interview !== prefs.interview_reminders_enabled ||
    communication !== prefs.communication_reminders_enabled ||
    cyber !== prefs.cybersecurity_reminders_enabled ||
    browser !== prefs.browser_notifications_enabled;

  return (
    <SectionCard
      title="Notification preferences"
      description="Reminders are personalized from your real activity, limited to a few a day, and never override these settings."
      onSave={() =>
        void run(() =>
          savePreferences({
            reminders_enabled: reminders,
            interview_reminders_enabled: interview,
            communication_reminders_enabled: communication,
            cybersecurity_reminders_enabled: cyber,
            browser_notifications_enabled: browser,
          })
        )
      }
      isSaving={isSaving}
      isDirty={dirty}
      flash={flash}
      onDismissFlash={dismiss}
    >
      <ToggleRow label="Reminders" description="Practice, streak and progress reminders in your notification center." checked={reminders} onChange={setReminders} />
      <div className="space-y-4 border-l border-border pl-4">
        <ToggleRow label="Cybersecurity reminders" description="Practice suggestions for your weaker topics." checked={cyber} onChange={setCyber} disabled={!reminders} />
        <ToggleRow label="Interview reminders" description="Nudges when you haven't practiced interviews lately." checked={interview} onChange={setInterview} disabled={!reminders} />
        <ToggleRow label="Communication reminders" description="Short speaking and communication practice prompts." checked={communication} onChange={setCommunication} disabled={!reminders} />
      </div>
      <div className="border-t border-border pt-4">
        <ToggleRow
          label="Browser notifications"
          description="Show a system notification for new reminders while this app is open in another tab. We only ask your browser for permission when you turn this on."
          checked={browser && reminders}
          onChange={(next) => void toggleBrowser(next)}
          disabled={!reminders || permission === "unsupported"}
        />
        <p className={hintClass} aria-live="polite">{PERMISSION_TEXT[permission]}</p>
      </div>
    </SectionCard>
  );
}
