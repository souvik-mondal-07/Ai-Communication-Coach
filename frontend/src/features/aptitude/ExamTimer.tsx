import { useEffect, useRef, useState } from "react";
import { Clock } from "lucide-react";
import { formatClock, remainingSeconds } from "@/features/aptitude/aptitudeMeta";
import { cn } from "@/lib/utils";

interface Props {
  expiresAt: string | null;
  clockOffsetMs: number;
  /** Called once when the countdown reaches zero. */
  onExpire: () => void;
  now?: () => number;
}

const ANNOUNCE_AT = [300, 60, 10];

/**
 * Countdown driven by the server's expiry time (so changing the device clock cannot extend a test).
 * It only re-renders its own text once a second - no animation - and a screen-reader live region
 * announces just the 5 minute, 1 minute and 10 second marks rather than every tick.
 */
export function ExamTimer({ expiresAt, clockOffsetMs, onExpire, now = Date.now }: Props) {
  const [left, setLeft] = useState<number | null>(() => remainingSeconds(expiresAt, now(), clockOffsetMs));
  const [announcement, setAnnouncement] = useState("");
  const fired = useRef(false);
  const onExpireRef = useRef(onExpire);
  useEffect(() => { onExpireRef.current = onExpire; }, [onExpire]);

  useEffect(() => {
    fired.current = false;
    const tick = () => {
      const remaining = remainingSeconds(expiresAt, now(), clockOffsetMs);
      setLeft(remaining);
      if (remaining !== null && ANNOUNCE_AT.includes(remaining)) {
        setAnnouncement(remaining >= 60 ? `${remaining / 60} minute${remaining === 60 ? "" : "s"} remaining` : `${remaining} seconds remaining`);
      }
      if (remaining === 0 && !fired.current) {
        fired.current = true;
        setAnnouncement("Time is up. Submitting your test.");
        onExpireRef.current();
      }
    };
    tick();
    const id = window.setInterval(tick, 1000);
    return () => window.clearInterval(id);
  }, [expiresAt, clockOffsetMs, now]);

  if (left === null) return null;
  const urgent = left <= 60;
  return (
    <div className={cn("inline-flex items-center gap-2 rounded-[var(--radius-panel)] border px-3 py-1.5 font-mono text-sm tabular-nums", urgent ? "border-danger text-danger" : "border-border-strong text-text-primary")}>
      <Clock size={15} aria-hidden="true" />
      <span role="timer" aria-live="off" aria-label="Time remaining">{formatClock(left)}</span>
      <span className="sr-only" role="status" aria-live="polite">{announcement}</span>
    </div>
  );
}
