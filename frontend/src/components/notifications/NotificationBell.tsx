import { useState } from "react";
import { Bell } from "lucide-react";
import { NotificationBadge } from "@/components/notifications/NotificationBadge";
import { NotificationPanel } from "@/components/notifications/NotificationPanel";
import { useNotificationActions } from "@/components/notifications/useNotificationActions";
import { useNotificationStore } from "@/store/notificationStore";

/** Header bell with the unread count; opens the recent-notifications panel. */
export function NotificationBell() {
  const [isOpen, setIsOpen] = useState(false);
  const { unreadCount, recent, isLoading, error, loadRecent, markRead, markAllRead, remove } = useNotificationStore();
  const { open } = useNotificationActions(() => setIsOpen(false));

  function toggle() {
    const next = !isOpen;
    setIsOpen(next);
    if (next) void loadRecent();
  }

  return (
    <div className="relative">
      <button
        type="button"
        onClick={toggle}
        className="relative rounded-[var(--radius-panel)] p-2 text-text-secondary hover:bg-surface-raised hover:text-text-primary"
        aria-label={unreadCount > 0 ? `Notifications, ${unreadCount} unread` : "Notifications"}
        aria-haspopup="dialog"
        aria-expanded={isOpen}
      >
        <Bell size={20} strokeWidth={1.75} />
        <NotificationBadge count={unreadCount} />
      </button>

      {isOpen && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setIsOpen(false)} aria-hidden="true" />
          <NotificationPanel
            items={recent}
            unreadCount={unreadCount}
            isLoading={isLoading}
            error={error}
            onOpen={open}
            onMarkRead={(n) => void markRead(n.id).catch(() => undefined)}
            onDelete={(n) => void remove(n.id).catch(() => undefined)}
            onMarkAllRead={() => void markAllRead().catch(() => undefined)}
            onRetry={() => void loadRecent()}
            onNavigate={() => setIsOpen(false)}
          />
        </>
      )}
    </div>
  );
}
