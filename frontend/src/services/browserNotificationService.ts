import type { AppNotification } from "@/types/notification";

/**
 * Browser (OS-level) notifications via the standard Notification API (Step 19).
 *
 * This is the only module that touches `window.Notification`, so delivery stays behind
 * one boundary: there is no push infrastructure, service worker or server-side delivery.
 * Notifications are shown only while the app is open (in a background tab), for reminders
 * the server has just created -- they are never shown on a plain page load.
 *
 * Permission is requested only from `requestBrowserPermission()`, which callers must
 * invoke in response to a user action (the Settings toggle), after explaining why.
 */

export type BrowserPermission = "granted" | "denied" | "default" | "unsupported";

export function getBrowserPermission(): BrowserPermission {
  if (typeof window === "undefined" || !("Notification" in window)) return "unsupported";
  return window.Notification.permission;
}

/** Must be called from a click/tap handler. Never prompts if already decided or unsupported. */
export async function requestBrowserPermission(): Promise<BrowserPermission> {
  const current = getBrowserPermission();
  if (current !== "default") return current;
  try {
    return await window.Notification.requestPermission();
  } catch {
    return getBrowserPermission();
  }
}

export interface ShowOptions {
  /** The user's `browser_notifications_enabled` preference. Off means never show. */
  enabled: boolean;
  /** Called when the user clicks the OS notification. */
  onClick?: (notification: AppNotification) => void;
}

/** True when an OS notification was actually shown. */
export function showBrowserNotification(notification: AppNotification, { enabled, onClick }: ShowOptions): boolean {
  if (!enabled || getBrowserPermission() !== "granted") return false;
  // The in-app bell already tells a user who is looking at the app.
  if (typeof document !== "undefined" && document.visibilityState === "visible") return false;
  try {
    const shown = new window.Notification(notification.title, {
      body: notification.message,
      tag: notification.id, // one OS notification per app notification
    });
    shown.onclick = () => {
      window.focus();
      onClick?.(notification);
      shown.close();
    };
    return true;
  } catch {
    return false;
  }
}
