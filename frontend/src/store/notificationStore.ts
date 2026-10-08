import { create } from "zustand";
import * as notificationService from "@/services/notificationService";
import { showBrowserNotification } from "@/services/browserNotificationService";
import { useProfileStore } from "@/store/profileStore";
import type { AppNotification } from "@/types/notification";
import { getApiErrorMessage } from "@/utils/apiError";

const RECENT_LIMIT = 8;

interface NotificationState {
  unreadCount: number;
  recent: AppNotification[];
  isLoading: boolean;
  error: string | null;

  /** Run due-reminder detection on the server, then refresh the badge. Safe to call often. */
  sync: (onOpen?: (n: AppNotification) => void) => Promise<void>;
  loadRecent: () => Promise<void>;
  refreshUnread: () => Promise<void>;
  markRead: (id: string) => Promise<void>;
  markAllRead: () => Promise<void>;
  remove: (id: string) => Promise<void>;
  setUnreadCount: (count: number) => void;
  reset: () => void;
}

const initial = { unreadCount: 0, recent: [] as AppNotification[], isLoading: false, error: null as string | null };

export const useNotificationStore = create<NotificationState>((set) => ({
  ...initial,

  sync: async (onOpen) => {
    try {
      const result = await notificationService.syncReminders();
      set({ unreadCount: result.unread_count });
      const enabled = useProfileStore.getState().profile?.preferences.browser_notifications_enabled ?? false;
      // Only reminders created by *this* sync are surfaced, so a reload never replays old ones.
      result.created.forEach((n) => showBrowserNotification(n, { enabled, onClick: onOpen }));
    } catch {
      // Reminders are a convenience; a failed check must never disturb the page.
    }
  },

  loadRecent: async () => {
    set({ isLoading: true, error: null });
    try {
      const page = await notificationService.listNotifications({ limit: RECENT_LIMIT });
      set({ recent: page.items, unreadCount: page.unread_count, isLoading: false });
    } catch (err) {
      set({ isLoading: false, error: getApiErrorMessage(err, "Unable to load notifications.") });
    }
  },

  refreshUnread: async () => {
    try {
      set({ unreadCount: await notificationService.getUnreadCount() });
    } catch {
      /* keep the last known count */
    }
  },

  markRead: async (id) => {
    const result = await notificationService.markRead(id);
    set((s) => ({
      unreadCount: result.unread_count,
      recent: s.recent.map((n) => (n.id === id ? result.notification : n)),
    }));
  },

  markAllRead: async () => {
    await notificationService.markAllRead();
    set((s) => ({
      unreadCount: 0,
      recent: s.recent.map((n) => ({ ...n, is_read: true, read_at: n.read_at ?? new Date().toISOString() })),
    }));
  },

  remove: async (id) => {
    const unread = await notificationService.deleteNotification(id);
    set((s) => ({ unreadCount: unread, recent: s.recent.filter((n) => n.id !== id) }));
  },

  setUnreadCount: (count) => set({ unreadCount: count }),
  reset: () => set({ ...initial }),
}));

