import { useCallback, useRef, useState } from "react";
import { Bell } from "lucide-react";
import { NotificationBadge } from "@/components/notifications/NotificationBadge";
import { NotificationPanel } from "@/components/notifications/NotificationPanel";
import { useDismiss } from "@/hooks/useDismiss";
import { useNotificationActions } from "@/components/notifications/useNotificationActions";
import { useNotificationStore } from "@/store/notificationStore";

/** Header bell with the unread count; opens the recent-notifications panel. */
export function NotificationBell() {
  const [isOpen, setIsOpen] = useState(false);
  const { unreadCount, recent, isLoading, error, loadRecent, markRead, markAllRead, remove } = useNotificationStore();
  const { open } = useNotificationActions(() => setIsOpen(false));
  const wrapRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const close = useCallback(() => {
    setIsOpen(false);
  }, []);
  useDismiss(wrapRef, isOpen, close);

  function toggle() {
    const next = !isOpen;
    setIsOpen(next);
    if (next) void loadRecent();
  }

  return (
    <div ref={wrapRef} className="relative">
      <button
        ref={triggerRef}
        type="button"
        onClick={toggle}
        className="relative rounded-[var(--radius-panel)] p-2 text-text-secondary transition-colors hover:bg-surface-raised hover:text-text-primary"
        aria-label={unreadCount > 0 ? `Notifications, ${unreadCount} unread` : "Notifications"}
        aria-haspopup="dialog"
        aria-expanded={isOpen}
      >
        <Bell size={20} strokeWidth={1.75} />
        <NotificationBadge count={unreadCount} />
      </button>

      {isOpen && (
        <>
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
