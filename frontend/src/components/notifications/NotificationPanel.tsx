import { Link } from "react-router-dom";
import { NotificationItem } from "@/components/notifications/NotificationItem";
import type { AppNotification } from "@/types/notification";

interface NotificationPanelProps {
  items: AppNotification[];
  unreadCount: number;
  isLoading: boolean;
  error: string | null;
  onOpen: (n: AppNotification) => void;
  onMarkRead: (n: AppNotification) => void;
  onDelete: (n: AppNotification) => void;
  onMarkAllRead: () => void;
  onRetry: () => void;
  onNavigate?: () => void;
}

/** Dropdown with the most recent notifications; the full list lives at /notifications. */
export function NotificationPanel(props: NotificationPanelProps) {
  const { items, unreadCount, isLoading, error, onMarkAllRead, onRetry, onNavigate } = props;
  return (
    <div
      role="dialog"
      aria-label="Notifications"
      className="absolute right-0 z-20 mt-2 w-[min(22rem,calc(100vw-2rem))] rounded-[var(--radius-panel)] border border-border bg-surface shadow-lg"
    >
      <div className="flex items-center justify-between border-b border-border px-3 py-2">
        <p className="text-sm font-semibold text-text-primary">Notifications</p>
        <button
          type="button"
          onClick={onMarkAllRead}
          disabled={unreadCount === 0}
          className="text-xs text-signal hover:underline disabled:text-text-muted disabled:no-underline"
        >
          Mark all read
        </button>
      </div>

      <div className="max-h-96 overflow-y-auto p-2">
        {isLoading && items.length === 0 && <p className="px-2 py-6 text-center text-sm text-text-muted">Loading…</p>}
        {error && (
          <div role="alert" className="px-2 py-4 text-center text-sm text-danger">
            {error}{" "}
            <button type="button" onClick={onRetry} className="underline">
              Retry
            </button>
          </div>
        )}
        {!isLoading && !error && items.length === 0 && (
          <p className="px-2 py-6 text-center text-sm text-text-muted">You're all caught up.</p>
        )}
        <ul className="space-y-2">
          {items.map((n) => (
            <NotificationItem
              key={n.id}
              notification={n}
              onOpen={props.onOpen}
              onMarkRead={props.onMarkRead}
              onDelete={props.onDelete}
            />
          ))}
        </ul>
      </div>

      <div className="border-t border-border px-3 py-2 text-center">
        <Link to="/notifications" onClick={onNavigate} className="text-xs text-signal hover:underline">
          View all notifications
        </Link>
      </div>
    </div>
  );
}
