import { Check, Trash2 } from "lucide-react";
import { actionLabel, relativeTime, typeLabel } from "@/components/notifications/notificationFormat";
import { cn } from "@/lib/utils";
import type { AppNotification } from "@/types/notification";

interface NotificationItemProps {
  notification: AppNotification;
  onOpen: (n: AppNotification) => void;
  onMarkRead: (n: AppNotification) => void;
  onDelete: (n: AppNotification) => void;
  now?: Date;
}

/** One notification row: type, title, message, time, its action, and read/delete controls. */
export function NotificationItem({ notification: n, onOpen, onMarkRead, onDelete, now }: NotificationItemProps) {
  return (
    <li
      className={cn(
        "rounded-[var(--radius-panel)] border px-3 py-3",
        n.is_read ? "border-border bg-base" : "border-signal/40 bg-signal/5"
      )}
      data-unread={n.is_read ? "false" : "true"}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="flex items-center gap-2 text-[11px] text-text-muted">
            {!n.is_read && <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-signal" aria-label="Unread" />}
            <span>{typeLabel(n.type)}</span>
            <span aria-hidden="true">·</span>
            <time dateTime={n.created_at}>{relativeTime(n.created_at, now)}</time>
          </p>
          <p className={cn("mt-1 text-sm", n.is_read ? "text-text-secondary" : "font-medium text-text-primary")}>
            {n.title}
          </p>
          <p className="mt-0.5 text-xs leading-relaxed text-text-secondary">{n.message}</p>
        </div>
        <div className="flex shrink-0 gap-1">
          {!n.is_read && (
            <button
              type="button"
              onClick={() => onMarkRead(n)}
              className="rounded p-1 text-text-muted hover:bg-surface-raised hover:text-text-primary"
              aria-label={`Mark "${n.title}" as read`}
            >
              <Check size={14} />
            </button>
          )}
          <button
            type="button"
            onClick={() => onDelete(n)}
            className="rounded p-1 text-text-muted hover:bg-surface-raised hover:text-danger"
            aria-label={`Delete "${n.title}"`}
          >
            <Trash2 size={14} />
          </button>
        </div>
      </div>
      {n.action && (
        <button
          type="button"
          onClick={() => onOpen(n)}
          className="mt-2 rounded-[var(--radius-panel)] bg-signal px-3 py-1 text-xs font-medium text-[#08120f] hover:opacity-90"
        >
          {actionLabel(n.action.target)}
        </button>
      )}
    </li>
  );
}
