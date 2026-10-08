import { badgeText } from "@/components/notifications/notificationFormat";

/** Small unread-count pill. Renders nothing when there is nothing unread. */
export function NotificationBadge({ count }: { count: number }) {
  const text = badgeText(count);
  if (!text) return null;
  return (
    <span
      className="absolute -right-1 -top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-signal px-1 text-[10px] font-semibold leading-none text-[#08120f]"
      aria-hidden="true"
    >
      {text}
    </span>
  );
}
