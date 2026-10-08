import type { NotificationType } from "@/types/notification";

const TYPE_LABELS: Record<NotificationType, string> = {
  daily_practice: "Daily practice",
  practice_reminder: "Reminder",
  weakness: "Needs practice",
  progress: "Progress",
  streak: "Streak",
  interview: "Interview",
  communication: "Communication",
  system: "System",
};

export function typeLabel(type: NotificationType): string {
  return TYPE_LABELS[type] ?? "Notification";
}

/** Button text for a notification's action, by where it leads. */
export function actionLabel(target: string): string {
  if (target.startsWith("/daily-practice")) return "Start practice";
  if (target.startsWith("/interview")) return "Practice now";
  if (target.startsWith("/communication")) return "Practice communication";
  if (target.startsWith("/cybersecurity") || target.startsWith("/practice")) return "Practice now";
  if (target.startsWith("/progress")) return "View progress";
  return "Open";
}

/** "just now", "5 min ago", "3 h ago", "2 d ago"; falls back to a date for older items. */
export function relativeTime(iso: string, now: Date = new Date()): string {
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "";
  const seconds = Math.max(0, Math.round((now.getTime() - then) / 1000));
  if (seconds < 60) return "just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} h ago`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days} d ago`;
  return new Date(iso).toLocaleDateString();
}

/** Badge text: hidden at 0, capped at "9+". */
export function badgeText(count: number): string | null {
  if (!Number.isFinite(count) || count <= 0) return null;
  return count > 9 ? "9+" : String(count);
}
