import { api } from "@/services/api";
import type { AppNotification, NotificationPage, NotificationType, ReadFilter, SyncResult } from "@/types/notification";

/** Client for `/api/v1/notifications` (Step 19). The user always comes from the JWT. */

interface ApiEnvelope<T> {
  success: boolean;
  message: string;
  data: T;
}

export async function listNotifications(
  params: { read?: ReadFilter; type?: NotificationType; page?: number; limit?: number } = {}
): Promise<NotificationPage> {
  const { data } = await api.get<ApiEnvelope<NotificationPage>>("/notifications", { params });
  return data.data;
}

export async function getUnreadCount(): Promise<number> {
  const { data } = await api.get<ApiEnvelope<{ unread_count: number }>>("/notifications/unread-count");
  return data.data.unread_count;
}

/** Ask the server to run due-reminder detection. Idempotent: it never creates the same reminder twice. */
export async function syncReminders(): Promise<SyncResult> {
  const { data } = await api.post<ApiEnvelope<SyncResult>>("/notifications/sync");
  return data.data;
}

export async function markRead(id: string): Promise<{ notification: AppNotification; unread_count: number }> {
  const { data } = await api.post<ApiEnvelope<{ notification: AppNotification; unread_count: number }>>(
    `/notifications/${encodeURIComponent(id)}/read`
  );
  return data.data;
}

export async function markAllRead(): Promise<number> {
  const { data } = await api.post<ApiEnvelope<{ updated: number; unread_count: number }>>("/notifications/read-all");
  return data.data.updated;
}

export async function deleteNotification(id: string): Promise<number> {
  const { data } = await api.delete<ApiEnvelope<{ unread_count: number }>>(`/notifications/${encodeURIComponent(id)}`);
  return data.data.unread_count;
}
