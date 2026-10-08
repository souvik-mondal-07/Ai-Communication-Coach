import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { AppNotification } from "@/types/notification";
import { getBrowserPermission, requestBrowserPermission, showBrowserNotification } from "./browserNotificationService";

const n: AppNotification = {
  id: "n1", type: "daily_practice", priority: "medium", title: "Today's Practice", message: "Waiting.",
  action: null, is_read: false, created_at: "2026-10-08T00:00:00Z", read_at: null, expires_at: null,
};

function stubBrowser(permission: NotificationPermission | null, visibility: DocumentVisibilityState = "hidden") {
  const ctor = vi.fn(function (this: { onclick?: unknown; close: () => void }) {
    this.close = vi.fn();
  });
  const requestPermission = vi.fn(async () => "granted" as NotificationPermission);
  const notif = permission === null ? undefined : Object.assign(ctor, { permission, requestPermission });
  vi.stubGlobal("window", notif ? { Notification: notif, focus: vi.fn() } : {});
  vi.stubGlobal("document", { visibilityState: visibility });
  return { ctor, requestPermission };
}

beforeEach(() => vi.unstubAllGlobals());
afterEach(() => vi.unstubAllGlobals());

describe("browser permission states", () => {
  it.each(["granted", "denied", "default"] as const)("reports %s", (p) => {
    stubBrowser(p);
    expect(getBrowserPermission()).toBe(p);
  });
  it("reports unsupported when the API is missing", () => {
    stubBrowser(null);
    expect(getBrowserPermission()).toBe("unsupported");
  });
});

describe("requestBrowserPermission", () => {
  it("prompts only when permission is still undecided", async () => {
    const { requestPermission } = stubBrowser("default");
    expect(await requestBrowserPermission()).toBe("granted");
    expect(requestPermission).toHaveBeenCalledOnce();
  });
  it.each(["granted", "denied"] as const)("never re-prompts when already %s", async (p) => {
    const { requestPermission } = stubBrowser(p);
    expect(await requestBrowserPermission()).toBe(p);
    expect(requestPermission).not.toHaveBeenCalled();
  });
  it("does nothing when unsupported", async () => {
    stubBrowser(null);
    expect(await requestBrowserPermission()).toBe("unsupported");
  });
});

describe("showBrowserNotification", () => {
  it("shows when enabled, granted and the tab is in the background", () => {
    const { ctor } = stubBrowser("granted", "hidden");
    expect(showBrowserNotification(n, { enabled: true })).toBe(true);
    expect(ctor).toHaveBeenCalledWith("Today's Practice", { body: "Waiting.", tag: "n1" });
  });
  it("respects the user's setting", () => {
    const { ctor } = stubBrowser("granted", "hidden");
    expect(showBrowserNotification(n, { enabled: false })).toBe(false);
    expect(ctor).not.toHaveBeenCalled();
  });
  it("never shows without permission", () => {
    for (const p of ["denied", "default"] as const) {
      const { ctor } = stubBrowser(p, "hidden");
      expect(showBrowserNotification(n, { enabled: true })).toBe(false);
      expect(ctor).not.toHaveBeenCalled();
    }
    stubBrowser(null);
    expect(showBrowserNotification(n, { enabled: true })).toBe(false);
  });
  it("stays quiet while the user is looking at the app", () => {
    const { ctor } = stubBrowser("granted", "visible");
    expect(showBrowserNotification(n, { enabled: true })).toBe(false);
    expect(ctor).not.toHaveBeenCalled();
  });
});
