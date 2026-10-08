import { useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { useDailyPracticeStore } from "@/store/dailyPracticeStore";
import { useNotificationStore } from "@/store/notificationStore";
import { useProfileStore } from "@/store/profileStore";
import type { AppNotification } from "@/types/notification";

const SYNC_INTERVAL_MS = 5 * 60 * 1000;

/** Browser timezone as an IANA name, or null when the runtime cannot tell. */
export function detectTimezone(): string | null {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || null;
  } catch {
    return null;
  }
}

/**
 * While a signed-in user has the app open:
 *  - saves the browser timezone once if the user has never chosen one (so "today" and the
 *    streak follow their local day instead of UTC);
 *  - asks the server to run its (idempotent) due-reminder check on load, every 5 minutes,
 *    and when the tab becomes visible again;
 *  - clears per-user notification/practice state on sign-out.
 * There is no background delivery: reminders are generated while the app is open.
 */
export function useReminderSync(userId: string | undefined) {
  const navigate = useNavigate();
  const profileLoaded = useProfileStore((s) => s.profile !== null);
  const sync = useNotificationStore((s) => s.sync);
  const savedTimezone = useRef(false);

  useEffect(() => {
    if (!userId || !profileLoaded) return;

    const { profile, savePreferences } = useProfileStore.getState();
    const tz = detectTimezone();
    if (!savedTimezone.current && profile && !profile.preferences.preferred_timezone && tz) {
      savedTimezone.current = true;
      void savePreferences({ preferred_timezone: tz }).catch(() => {
        savedTimezone.current = false;
      });
    }

    const open = (n: AppNotification) => {
      if (n.action?.type === "route") navigate(n.action.target);
    };
    void sync(open);
    const timer = window.setInterval(() => void sync(open), SYNC_INTERVAL_MS);
    const onVisible = () => {
      if (document.visibilityState === "visible") void sync(open);
    };
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      window.clearInterval(timer);
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, [userId, profileLoaded, sync, navigate]);

  useEffect(
    () => () => {
      useNotificationStore.getState().reset();
      useDailyPracticeStore.getState().reset();
      savedTimezone.current = false;
    },
    [userId]
  );
}
