import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

/** Inline spinner. Always render visible or sr-only text next to it. */
export function Spinner({ size = 16, className }: { size?: number; className?: string }) {
  return <Loader2 size={size} aria-hidden="true" className={cn("animate-spin text-text-muted", className)} />;
}
