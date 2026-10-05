import { useEffect, useRef, useState } from "react";
import { Timer } from "lucide-react";
import { formatClock } from "@/features/cybersecurity/practice/practiceUtils";

interface PracticeTimerProps {
  /** Wall-clock ms at which time runs out. */
  deadlineMs: number;
  /** Called once when the countdown reaches zero. */
  onExpire: () => void;
}

export function PracticeTimer({ deadlineMs, onExpire }: PracticeTimerProps) {
  const [remaining, setRemaining] = useState(() => Math.max(0, Math.ceil((deadlineMs - Date.now()) / 1000)));
  const fired = useRef(false);
  const onExpireRef = useRef(onExpire);

  useEffect(() => {
    onExpireRef.current = onExpire;
  });

  useEffect(() => {
    fired.current = false;
    const tick = () => {
      const left = Math.max(0, Math.ceil((deadlineMs - Date.now()) / 1000));
      setRemaining(left);
      if (left === 0 && !fired.current) {
        fired.current = true;
        onExpireRef.current();
      }
    };
    tick();
    const id = window.setInterval(tick, 1000);
    return () => window.clearInterval(id);
  }, [deadlineMs]);

  return (
    <span
      role="timer"
      aria-label="Time remaining"
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium tabular-nums ${
        remaining <= 60 ? "border-danger/50 text-danger" : "border-border text-text-secondary"
      }`}
    >
      <Timer size={12} />
      {formatClock(remaining)} remaining
    </span>
  );
}
