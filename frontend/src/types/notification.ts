/** Step 19 -- notification center types (mirror backend/app/schemas/notification.py). */

export const NOTIFICATION_TYPES = [
  "daily_practice",
  "practice_reminder",
  "weakness",
  "progress",
  "streak",
  "interview",
  "communication",
  "system",
] as const;
export type NotificationType = (typeof NOTIFICATION_TYPES)[number];

export type NotificationPriority = "high" | "medium" | "low";
export type ReadFilter = "all" | "unread" | "read";

export interface AppNotification {
  id: string;
  type: NotificationType;
  priority: NotificationPriority;
  title: string;
  message: string;
  action: { type: "route"; target: string } | null;
  is_read: boolean;
  created_at: string;
  read_at: string | null;
  expires_at: string | null;
}

export interface NotificationPage {
  items: AppNotification[];
  page: number;
  limit: number;
  total: number;
  has_next: boolean;
  unread_count: number;
}

export interface SyncResult {
  created: AppNotification[];
  unread_count: number;
}
