import { useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useNotificationStore } from "@/store/notificationStore";
import type { AppNotification } from "@/types/notification";

/** Shared handlers for the bell panel and the /notifications page. */
export function useNotificationActions(afterNavigate?: () => void) {
  const navigate = useNavigate();
  const markRead = useNotificationStore((s) => s.markRead);

  const open = useCallback(
    (n: AppNotification) => {
      if (!n.is_read) void markRead(n.id).catch(() => undefined);
      if (n.action?.type === "route") {
        navigate(n.action.target);
        afterNavigate?.();
      }
    },
    [markRead, navigate, afterNavigate]
  );
  return { open };
}
