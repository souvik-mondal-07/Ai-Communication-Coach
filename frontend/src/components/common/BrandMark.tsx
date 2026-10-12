import { useId } from "react";

/** Shield logo drawn inline (no external asset). Decorative: pair with visible text. */
export function BrandMark({ size = 40 }: { size?: number }) {
  const id = useId();
  return (
    <svg width={size} height={size} viewBox="0 0 48 48" aria-hidden="true" className="shrink-0 drop-shadow-[0_6px_14px_rgb(47_107_255/0.55)]">
      <defs>
        <linearGradient id={`${id}-g`} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#4d9bff" />
          <stop offset="100%" stopColor="#6d3dff" />
        </linearGradient>
      </defs>
      <path d="M24 3 41 9.5v13.2c0 10.2-6.6 18.4-17 22.3C13.6 41.1 7 32.9 7 22.7V9.5L24 3Z" fill="#0a1740" stroke={`url(#${id}-g)`} strokeWidth="2.4" strokeLinejoin="round" />
      <path d="M24 9.5 36 14v8.2c0 7.300-4.700 13.200-12 16.300-7.300-3.100-12-9-12-16.300V14l12-4.500Z" fill={`url(#${id}-g)`} opacity="0.9" />
      <path d="m17.5 23.5 4.800 4.800 8.200-9.300" fill="none" stroke="#fff" strokeWidth="2.800" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
