import { beforeEach, describe, expect, it, vi } from "vitest";
import type { AppNotification } from "@/types/notification";

vi.mock("@/services/notificationService", () => ({
  syncReminders: vi.fn(), listNotifications: vi.fn(), getUnreadCount: vi.fn(),
  markRead: vi.fn(), markAllRead: vi.fn(), deleteNotification: vi.fn(),
}));
vi.mock("@/services/browserNotificationService", () => ({ showBrowserNotification: vi.fn() }));
vi.mock("@/store/profileStore", () => ({ useProfileStore: { getState: vi.fn() } }));

import { showBrowserNotification } from "@/services/browserNotificationService";
import * as svc from "@/services/notificationService";
import { useProfileStore } from "@/store/profileStore";
import { useNotificationStore } from "./notificationStore";

const n = (id: string, read = false): AppNotification => ({
  id, type: "daily_practice", priority: "medium", title: id, message: "m", action: null,
  is_read: read, created_at: "2026-10-08T00:00:00Z", read_at: null, expires_at: null,
});
const prefs = (browser: boolean) =>
  vi.mocked(useProfileStore.getState).mockReturnValue({ profile: { preferences: { browser_notifications_enabled: browser } } } as never);

beforeEach(() => {
  vi.clearAllMocks();
  useNotificationStore.getState().reset();
  prefs(false);
});

describe("sync", () => {
  it("updates the unread badge from the server", async () => {
    vi.mocked(svc.syncReminders).mockResolvedValue({ created: [], unread_count: 4 });
    await useNotificationStore.getState().sync();
    expect(useNotificationStore.getState().unreadCount).toBe(4);
  });
  it("offers only newly created reminders to the browser, honouring the setting", async () => {
    vi.mocked(svc.syncReminders).mockResolvedValue({ created: [n("a")], unread_count: 1 });
    await useNotificationStore.getState().sync();
    expect(showBrowserNotification).toHaveBeenCalledWith(expect.objectContaining({ id: "a" }), expect.objectContaining({ enabled: false }));
    prefs(true);
    await useNotificationStore.getState().sync();
    expect(showBrowserNotification).toHaveBeenLastCalledWith(expect.anything(), expect.objectContaining({ enabled: true }));
  });
  it("does not notify when nothing new was created (e.g. a reload)", async () => {
    vi.mocked(svc.syncReminders).mockResolvedValue({ created: [], unread_count: 2 });
    await useNotificationStore.getState().sync();
    expect(showBrowserNotification).not.toHaveBeenCalled();
  });
  it("swallows a failed check and keeps the last count", async () => {
    useNotificationStore.getState().setUnreadCount(5);
    vi.mocked(svc.syncReminders).mockRejectedValue(new Error("offline"));
    await expect(useNotificationStore.getState().sync()).resolves.toBeUndefined();
    expect(useNotificationStore.getState().unreadCount).toBe(5);
  });
});

describe("list actions", () => {
  it("loads recent items and the count", async () => {
    vi.mocked(svc.listNotifications).mockResolvedValue({ items: [n("a"), n("b")], page: 1, limit: 8, total: 2, has_next: false, unread_count: 2 });
    await useNotificationStore.getState().loadRecent();
    expect(useNotificationStore.getState().recent).toHaveLength(2);
    expect(useNotificationStore.getState().unreadCount).toBe(2);
  });
  it("exposes a load error", async () => {
    vi.mocked(svc.listNotifications).mockRejectedValue(new Error("x"));
    await useNotificationStore.getState().loadRecent();
    expect(useNotificationStore.getState().error).toBeTruthy();
  });
  it("marking read decrements the count and updates the item", async () => {
    useNotificationStore.setState({ recent: [n("a"), n("b")], unreadCount: 2 });
    vi.mocked(svc.markRead).mockResolvedValue({ notification: n("a", true), unread_count: 1 });
    await useNotificationStore.getState().markRead("a");
    const s = useNotificationStore.getState();
    expect(s.unreadCount).toBe(1);
    expect(s.recent.find((x) => x.id === "a")?.is_read).toBe(true);
    expect(s.recent.find((x) => x.id === "b")?.is_read).toBe(false);
  });
  it("mark all read zeroes the count; delete removes the item", async () => {
    useNotificationStore.setState({ recent: [n("a"), n("b")], unreadCount: 2 });
    vi.mocked(svc.markAllRead).mockResolvedValue(2);
    await useNotificationStore.getState().markAllRead();
    expect(useNotificationStore.getState().unreadCount).toBe(0);
    expect(useNotificationStore.getState().recent.every((x) => x.is_read)).toBe(true);
    vi.mocked(svc.deleteNotification).mockResolvedValue(0);
    await useNotificationStore.getState().remove("a");
    expect(useNotificationStore.getState().recent.map((x) => x.id)).toEqual(["b"]);
  });
});
