import { renderToStaticMarkup } from "react-dom/server";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import type { AppNotification } from "@/types/notification";
import { NotificationBadge } from "./NotificationBadge";
import { NotificationItem } from "./NotificationItem";
import { NotificationPanel } from "./NotificationPanel";

const render = (node: React.ReactNode) => renderToStaticMarkup(<MemoryRouter>{node}</MemoryRouter>);

const note = (over: Partial<AppNotification> = {}): AppNotification => ({
  id: "n1", type: "daily_practice", priority: "medium", title: "Today's Practice",
  message: "Your daily practice is waiting.", action: { type: "route", target: "/daily-practice" },
  is_read: false, created_at: "2026-10-08T11:00:00Z", read_at: null, expires_at: null, ...over,
});
const noop = vi.fn();
const panel = (over: Partial<Parameters<typeof NotificationPanel>[0]> = {}) =>
  render(
    <NotificationPanel items={[]} unreadCount={0} isLoading={false} error={null} onOpen={noop} onMarkRead={noop}
      onDelete={noop} onMarkAllRead={noop} onRetry={noop} {...over} />
  );

describe("NotificationBadge", () => {
  it("renders nothing for zero and the count otherwise", () => {
    expect(render(<NotificationBadge count={0} />)).toBe("");
    expect(render(<NotificationBadge count={3} />)).toContain(">3<");
    expect(render(<NotificationBadge count={42} />)).toContain("9+");
  });
});

describe("NotificationItem", () => {
  it("shows an unread item with its action and a mark-read control", () => {
    const html = render(<NotificationItem notification={note()} onOpen={noop} onMarkRead={noop} onDelete={noop} />);
    expect(html).toContain('data-unread="true"');
    expect(html).toContain("Today&#x27;s Practice");
    expect(html).toContain("Daily practice");
    expect(html).toContain("Start practice");
    expect(html).toContain("as read");
  });
  it("hides mark-read for a read item", () => {
    const html = render(<NotificationItem notification={note({ is_read: true })} onOpen={noop} onMarkRead={noop} onDelete={noop} />);
    expect(html).toContain('data-unread="false"');
    expect(html).not.toContain("as read");
  });
  it("omits the action button when there is no action", () => {
    const html = render(<NotificationItem notification={note({ action: null })} onOpen={noop} onMarkRead={noop} onDelete={noop} />);
    expect(html).not.toContain("Start practice");
  });
});

describe("NotificationPanel states", () => {
  it("shows loading, empty and error states", () => {
    expect(panel({ isLoading: true })).toContain("Loading");
    expect(panel()).toContain("all caught up");
    const err = panel({ error: "boom" });
    expect(err).toContain('role="alert"');
    expect(err).toContain("Retry");
  });
  it("lists items, links to the full page, and disables mark-all when nothing is unread", () => {
    const html = panel({ items: [note(), note({ id: "n2", title: "Weakness" })], unreadCount: 2 });
    expect(html).toContain("Weakness");
    expect(html).toContain('href="/notifications"');
    expect(panel({ items: [note({ is_read: true })], unreadCount: 0 })).toContain("disabled");
  });
});
