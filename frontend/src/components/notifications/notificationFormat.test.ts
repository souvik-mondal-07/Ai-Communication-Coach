import { describe, expect, it } from "vitest";
import { actionLabel, badgeText, relativeTime, typeLabel } from "./notificationFormat";

describe("badgeText", () => {
  it("hides the badge at zero or invalid counts", () => {
    expect(badgeText(0)).toBeNull();
    expect(badgeText(-2)).toBeNull();
    expect(badgeText(Number.NaN)).toBeNull();
  });
  it("shows the count and caps at 9+", () => {
    expect(badgeText(3)).toBe("3");
    expect(badgeText(9)).toBe("9");
    expect(badgeText(10)).toBe("9+");
  });
});

describe("relativeTime", () => {
  const now = new Date("2026-10-08T12:00:00Z");
  it.each([
    ["2026-10-08T11:59:40Z", "just now"],
    ["2026-10-08T11:55:00Z", "5 min ago"],
    ["2026-10-08T09:00:00Z", "3 h ago"],
    ["2026-10-06T12:00:00Z", "2 d ago"],
  ])("%s -> %s", (iso, expected) => expect(relativeTime(iso, now)).toBe(expected));
  it("never shows a negative age for a future timestamp", () => {
    expect(relativeTime("2026-10-08T13:00:00Z", now)).toBe("just now");
  });
  it("returns an empty string for garbage", () => expect(relativeTime("nope", now)).toBe(""));
});

describe("labels", () => {
  it("labels every type and picks an action label from the route", () => {
    expect(typeLabel("weakness")).toBe("Needs practice");
    expect(typeLabel("daily_practice")).toBe("Daily practice");
    expect(actionLabel("/daily-practice")).toBe("Start practice");
    expect(actionLabel("/communication")).toBe("Practice communication");
    expect(actionLabel("/progress")).toBe("View progress");
    expect(actionLabel("/settings")).toBe("Open");
  });
});
