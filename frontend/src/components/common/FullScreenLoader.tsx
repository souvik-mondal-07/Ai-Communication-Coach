import { ShieldHalf } from "lucide-react";

/**
 * Shown while the app determines whether a stored token maps to a valid
 * session, so an authenticated user never sees a flash of the login page.
 */
export function FullScreenLoader() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-base">
      <div className="flex flex-col items-center gap-3">
        <div className="flex h-10 w-10 animate-pulse items-center justify-center rounded-[var(--radius-panel)] bg-signal/15 text-signal">
          <ShieldHalf size={20} />
        </div>
        <p className="text-sm text-text-muted">Loading…</p>
      </div>
    </div>
  );
}
