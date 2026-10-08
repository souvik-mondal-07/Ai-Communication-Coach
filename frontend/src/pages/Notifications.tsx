import { useCallback, useEffect, useState } from "react";
import { NotificationItem } from "@/components/notifications/NotificationItem";
import { useNotificationActions } from "@/components/notifications/useNotificationActions";
import { Button } from "@/components/ui/button";
import * as notificationService from "@/services/notificationService";
import { useNotificationStore } from "@/store/notificationStore";
import { NOTIFICATION_TYPES, type AppNotification, type NotificationPage, type NotificationType, type ReadFilter } from "@/types/notification";
import { typeLabel } from "@/components/notifications/notificationFormat";
import { getApiErrorMessage } from "@/utils/apiError";

const FILTERS: { value: ReadFilter; label: string }[] = [
  { value: "all", label: "All" },
  { value: "unread", label: "Unread" },
  { value: "read", label: "Read" },
];
const PAGE_SIZE = 20;

export default function Notifications() {
  const [read, setRead] = useState<ReadFilter>("all");
  const [type, setType] = useState<NotificationType | "">("");
  const [page, setPage] = useState(1);
  const [data, setData] = useState<NotificationPage | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const setUnreadCount = useNotificationStore((s) => s.setUnreadCount);
  const { open } = useNotificationActions();

  const load = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await notificationService.listNotifications({ read, type: type || undefined, page, limit: PAGE_SIZE });
      setData(result);
      setUnreadCount(result.unread_count);
    } catch (err) {
      setError(getApiErrorMessage(err, "Unable to load notifications."));
    } finally {
      setIsLoading(false);
    }
  }, [read, type, page, setUnreadCount]);

  useEffect(() => {
    void load();
  }, [load]);

  async function run(action: () => Promise<unknown>) {
    try {
      await action();
      await load();
    } catch (err) {
      setError(getApiErrorMessage(err, "That didn't work. Please try again."));
    }
  }

  const items = data?.items ?? [];
  return (
    <div className="mx-auto max-w-3xl space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="font-display text-xl font-semibold text-text-primary">Notifications</h2>
          <p className="mt-1 text-sm text-text-secondary">
            {data ? `${data.unread_count} unread` : "Your practice reminders and progress updates."}
          </p>
        </div>
        <Button variant="secondary" size="sm" disabled={!data || data.unread_count === 0} onClick={() => void run(notificationService.markAllRead)}>
          Mark all as read
        </Button>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <div role="radiogroup" aria-label="Filter by read state" className="flex gap-1">
          {FILTERS.map((f) => (
            <button
              key={f.value}
              type="button"
              role="radio"
              aria-checked={read === f.value}
              onClick={() => { setRead(f.value); setPage(1); }}
              className={`rounded-full border px-3 py-1 text-xs ${read === f.value ? "border-signal bg-signal/10 text-signal" : "border-border text-text-secondary hover:border-border-strong"}`}
            >
              {f.label}
            </button>
          ))}
        </div>
        <label className="sr-only" htmlFor="notification-type">Type</label>
        <select
          id="notification-type"
          value={type}
          onChange={(e) => { setType(e.target.value as NotificationType | ""); setPage(1); }}
          className="rounded-[var(--radius-panel)] border border-border bg-base px-2 py-1 text-xs text-text-primary"
        >
          <option value="">All types</option>
          {NOTIFICATION_TYPES.map((t) => (
            <option key={t} value={t}>{typeLabel(t)}</option>
          ))}
        </select>
      </div>

      {error && (
        <div role="alert" className="text-sm text-danger">
          {error}{" "}
          <button type="button" onClick={() => void load()} className="underline">Retry</button>
        </div>
      )}
      {isLoading && !data && <p className="text-sm text-text-muted">Loading notifications…</p>}
      {!isLoading && !error && items.length === 0 && (
        <p className="rounded-[var(--radius-panel)] border border-border px-4 py-10 text-center text-sm text-text-muted">
          {read === "unread" ? "No unread notifications." : "No notifications yet. Reminders appear here as you practice."}
        </p>
      )}

      <ul className="space-y-2">
        {items.map((n: AppNotification) => (
          <NotificationItem
            key={n.id}
            notification={n}
            onOpen={open}
            onMarkRead={(item) => void run(() => notificationService.markRead(item.id))}
            onDelete={(item) => void run(() => notificationService.deleteNotification(item.id))}
          />
        ))}
      </ul>

      {data && (page > 1 || data.has_next) && (
        <div className="flex items-center justify-between">
          <Button variant="ghost" size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>Previous</Button>
          <span className="text-xs text-text-muted">Page {page}</span>
          <Button variant="ghost" size="sm" disabled={!data.has_next} onClick={() => setPage((p) => p + 1)}>Next</Button>
        </div>
      )}
    </div>
  );
}
