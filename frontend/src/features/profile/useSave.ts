import { useCallback, useRef, useState } from "react";
import type { Flash } from "@/features/profile/StatusMessage";

/**
 * Wraps an async save with a busy flag (a ref guards against double-clicks that
 * land before React re-renders) and success/error notices.
 */
export function useSave(successText: string, errorText: string) {
  const [isSaving, setIsSaving] = useState(false);
  const [flash, setFlash] = useState<Flash | null>(null);
  const busy = useRef(false);

  const run = useCallback(
    async (action: () => Promise<void>) => {
      if (busy.current) return;
      busy.current = true;
      setIsSaving(true);
      setFlash(null);
      try {
        await action();
        setFlash({ type: "success", text: successText });
      } catch {
        setFlash({ type: "error", text: errorText });
      } finally {
        busy.current = false;
        setIsSaving(false);
      }
    },
    [successText, errorText]
  );

  const dismiss = useCallback(() => setFlash(null), []);
  return { isSaving, flash, run, dismiss };
}
