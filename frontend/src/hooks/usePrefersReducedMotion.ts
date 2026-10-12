import { useSyncExternalStore } from "react";

const QUERY = "(prefers-reduced-motion: reduce)";

function subscribe(callback: () => void): () => void {
  const mql = window.matchMedia?.(QUERY);
  mql?.addEventListener("change", callback);
  return () => mql?.removeEventListener("change", callback);
}

/** True when the user asked the OS to reduce motion. Used to switch off JS-driven animation (e.g. charts). */
export function usePrefersReducedMotion(): boolean {
  return useSyncExternalStore(
    subscribe,
    () => window.matchMedia?.(QUERY).matches ?? false,
    () => false
  );
}
