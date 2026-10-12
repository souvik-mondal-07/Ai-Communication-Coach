import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

const TONE: Record<string, string> = {
  signal: "bg-signal",
  success: "bg-success",
  warn: "bg-warn",
  danger: "bg-danger",
  brand: "bg-brand",
};

interface ProgressBarProps {
  /** 0 to 100. Clamped. */
  value: number;
  label: string;
  tone?: keyof typeof TONE;
  /** Any CSS color or gradient (e.g. var(--color-success)); overrides `tone`. For score bands computed at runtime. */
  color?: string;
  className?: string;
}

/**
 * Accessible progress bar. The fill is already at its final width in the markup;
 * the entrance animation is a pure-CSS scaleX, so it never delays or hides data
 * and is removed automatically under prefers-reduced-motion.
 */
export function ProgressBar({ value, label, tone = "signal", color, className }: ProgressBarProps) {
  const pct = Math.max(0, Math.min(100, Math.round(value)));
  return (
    <div
      role="progressbar"
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={pct}
      aria-label={label}
      className={cn("h-2 overflow-hidden rounded-full bg-surface-raised", className)}
    >
      <div
        className={cn("h-full origin-left animate-bar-grow rounded-full", color ? undefined : TONE[tone])}
        style={{ width: `${pct}%`, ...(color ? { background: color } : null) }}
      />
    </div>
  );
}

interface ProgressRingProps {
  value: number;
  size?: number;
  stroke?: number;
  label: string;
  children?: ReactNode;
}

/** Circular progress with the brand gradient. Children render centered inside. */
export function ProgressRing({ value, size = 132, stroke = 10, label, children }: ProgressRingProps) {
  const pct = Math.max(0, Math.min(100, Math.round(value)));
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  return (
    <div
      role="progressbar"
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={pct}
      aria-label={label}
      className="relative shrink-0"
      style={{ width: size, height: size }}
    >
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="-rotate-90" aria-hidden="true">
        <defs>
          <linearGradient id="ring-brand" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="#5b8dff" />
            <stop offset="100%" stopColor="#8b6dff" />
          </linearGradient>
        </defs>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" strokeWidth={stroke} className="stroke-border-strong/60" />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          strokeWidth={stroke}
          strokeLinecap="round"
          stroke="url(#ring-brand)"
          strokeDasharray={c}
          strokeDashoffset={c * (1 - pct / 100)}
          style={{ transition: "stroke-dashoffset 900ms var(--ease-out-quint)" }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center text-center">{children}</div>
    </div>
  );
}
