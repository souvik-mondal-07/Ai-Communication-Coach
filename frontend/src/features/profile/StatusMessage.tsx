import { useEffect } from "react";
import { cn } from "@/lib/utils";

export interface Flash {
  type: "success" | "error";
  text: string;
}

/** Inline success/error notice. Success messages dismiss themselves. */
export function StatusMessage({ flash, onDismiss }: { flash: Flash | null; onDismiss: () => void }) {
  useEffect(() => {
    if (flash?.type !== "success") return;
    const timer = window.setTimeout(onDismiss, 4000);
    return () => window.clearTimeout(timer);
  }, [flash, onDismiss]);

  if (!flash) return null;
  return (
    <p
      role={flash.type === "error" ? "alert" : "status"}
      className={cn(
        "rounded-[var(--radius-panel)] border px-3 py-2 text-sm",
        flash.type === "success"
          ? "border-signal/40 bg-signal/10 text-signal"
          : "border-danger/40 bg-danger/10 text-danger"
      )}
    >
      {flash.text}
    </p>
  );
}
