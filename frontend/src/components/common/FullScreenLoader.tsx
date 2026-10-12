import { ShieldHalf } from "lucide-react";

/**
 * Shown while the app determines whether a stored token maps to a valid
 * session, so an authenticated user never sees a flash of the login page.
 */
export function FullScreenLoader() {
  return (
    <div role="status" className="flex min-h-screen items-center justify-center">
      <div className="flex flex-col items-center gap-3">
        <div className="flex h-11 w-11 animate-pulse items-center justify-center rounded-[var(--radius-card)] bg-brand text-white shadow-[0_10px_30px_-8px_rgb(91_141_255/0.7)]">
          <ShieldHalf size={22} aria-hidden="true" />
        </div>
        <p className="text-sm text-text-muted">Loading…</p>
      </div>
    </div>
  );
}
