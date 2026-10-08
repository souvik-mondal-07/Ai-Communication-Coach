import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import type { UserPreferences } from "@/types/profile";

vi.mock("@/services/browserNotificationService", () => ({
  getBrowserPermission: vi.fn(() => "default"),
  requestBrowserPermission: vi.fn(),
}));

import { getBrowserPermission } from "@/services/browserNotificationService";
import { NotificationPreferences, PracticePreferences } from "./PracticeSettings";
import { ToggleRow } from "./ToggleRow";

const prefs = (over: Partial<UserPreferences> = {}): UserPreferences => ({
  response_style: "balanced", difficulty: "adaptive", learning_style: "mixed", interview_focus: [], theme: "system",
  daily_practice_enabled: true, daily_practice_minutes: 15, preferred_practice_time: "18:00",
  preferred_timezone: "Asia/Kolkata", practice_days: ["mon", "tue", "wed", "thu", "fri"],
  reminders_enabled: true, interview_reminders_enabled: true, communication_reminders_enabled: false,
  cybersecurity_reminders_enabled: true, browser_notifications_enabled: false, ...over,
});

describe("ToggleRow", () => {
  it("exposes switch state to assistive tech", () => {
    const on = renderToStaticMarkup(<ToggleRow label="Reminders" checked onChange={vi.fn()} />);
    expect(on).toContain('role="switch"');
    expect(on).toContain('aria-checked="true"');
    expect(renderToStaticMarkup(<ToggleRow label="x" checked={false} onChange={vi.fn()} disabled />)).toContain("disabled");
  });
});

describe("PracticePreferences", () => {
  it("renders the saved values", () => {
    const html = renderToStaticMarkup(<PracticePreferences prefs={prefs()} />);
    expect(html).toContain("Daily practice");
    expect(html).toContain("15 min");
    expect(html).toContain('value="18:00"');
    expect(html).toContain("Asia/Kolkata");
    expect(html).toContain("Practice days");
  });
});

describe("NotificationPreferences", () => {
  it("explains permission before it is requested and never asks on render", () => {
    const html = renderToStaticMarkup(<NotificationPreferences prefs={prefs()} />);
    expect(html).toContain("ask your browser for permission when you turn this on");
    expect(html).toContain("Browser notifications");
  });
  it.each([
    ["denied", "blocked"],
    ["unsupported", "doesn&#x27;t support notifications"],
    ["granted", "allowed for this site"],
  ] as const)("describes the %s state", (permission, text) => {
    vi.mocked(getBrowserPermission).mockReturnValue(permission);
    expect(renderToStaticMarkup(<NotificationPreferences prefs={prefs()} />)).toContain(text);
  });
  it("disables the sub-toggles and browser switch when reminders are off", () => {
    vi.mocked(getBrowserPermission).mockReturnValue("default");
    const html = renderToStaticMarkup(<NotificationPreferences prefs={prefs({ reminders_enabled: false })} />);
    expect((html.match(/disabled=""/g) ?? []).length).toBeGreaterThanOrEqual(4);
  });
});
