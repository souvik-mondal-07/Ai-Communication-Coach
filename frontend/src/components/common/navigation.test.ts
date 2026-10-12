import { describe, expect, it } from "vitest";
import { breadcrumbsFor, documentTitleFor, NAV_SECTIONS } from "./navigation";

describe("navigation", () => {
  it("has no duplicate routes", () => {
    const paths = NAV_SECTIONS.flatMap((s) => s.items.map((i) => i.path));
    expect(new Set(paths).size).toBe(paths.length);
  });

  it("labels top-level routes, including ones missing from the old NAV_ITEMS", () => {
    expect(breadcrumbsFor("/analytics")).toEqual([{ label: "Analytics" }]);
    expect(breadcrumbsFor("/voice-conversation")).toEqual([{ label: "Voice Conversation" }]);
    expect(breadcrumbsFor("/notifications")).toEqual([{ label: "Notifications" }]);
  });

  it("builds a parent link plus current page for nested routes", () => {
    expect(breadcrumbsFor("/ctf/abc")).toEqual([{ label: "CTF & Labs", to: "/ctf" }, { label: "Session" }]);
    expect(breadcrumbsFor("/cybersecurity/practice/9")[1]).toEqual({ label: "Practice session" });
    expect(breadcrumbsFor("/cybersecurity/network-basics")[1]).toEqual({ label: "Topic" });
    expect(breadcrumbsFor("/history/practice/5")[1]).toEqual({ label: "Details" });
  });

  it("falls back for unknown routes", () => {
    expect(breadcrumbsFor("/nope")).toEqual([{ label: "AI Cybersecurity Mentor" }]);
    expect(breadcrumbsFor("/")).toEqual([{ label: "AI Cybersecurity Mentor" }]);
  });

  it("builds document titles most-specific first without repeating the app name", () => {
    expect(documentTitleFor("/progress")).toBe("Progress · AI Cybersecurity Mentor");
    expect(documentTitleFor("/ctf/abc")).toBe("Session · CTF & Labs · AI Cybersecurity Mentor");
    expect(documentTitleFor("/nope")).toBe("AI Cybersecurity Mentor");
  });
});
