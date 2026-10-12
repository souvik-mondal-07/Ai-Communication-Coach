import { useId } from "react";

/** Local SVG artwork for the dashboard. All decorative (aria-hidden); nothing is fetched. */

export function HeroArt({ className }: { className?: string }) {
  const id = useId();
  return (
    <svg viewBox="0 0 360 200" className={className} aria-hidden="true" focusable="false">
      <defs>
        <linearGradient id={`${id}s`} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#4d9bff" />
          <stop offset="100%" stopColor="#7c3aed" />
        </linearGradient>
        <radialGradient id={`${id}g`} cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#3b6bff" stopOpacity="0.55" />
          <stop offset="100%" stopColor="#3b6bff" stopOpacity="0" />
        </radialGradient>
      </defs>
      <circle cx="250" cy="100" r="110" fill={`url(#${id}g)`} />
      {/* hooded silhouette behind the shield */}
      <path d="M250 18c-34 0-56 24-60 58-3 20-12 34-26 52-10 13-18 28-20 72h212c-2-44-10-59-20-72-14-18-23-32-26-52-4-34-26-58-60-58Z" fill="#050b22" opacity="0.85" />
      <path d="M250 30c-26 0-44 18-47 46 20 10 74 10 94 0-3-28-21-46-47-46Z" fill="#0a1236" />
      {/* circuit lines */}
      <g stroke="#3b6bff" strokeOpacity="0.45" strokeWidth="1" fill="none">
        <path d="M20 150h70l16-24h60" />
        <path d="M0 120h50l14-18h40" />
        <path d="M300 60h40l12 16h8" />
      </g>
      <g fill="#6ea8ff">
        <circle cx="166" cy="126" r="2.5" />
        <circle cx="104" cy="102" r="2.5" />
        <circle cx="352" cy="76" r="2.5" />
      </g>
      {/* shield + lock */}
      <path d="M250 52 292 66v36c0 28-17 46-42 56-25-10-42-28-42-56V66l42-14Z" fill="#0b1a55" stroke={`url(#${id}s)`} strokeWidth="5" strokeLinejoin="round" />
      <path d="M250 64 281 74v28c0 21-12 35-31 43-19-8-31-22-31-43V74l31-10Z" fill="#12266f" opacity="0.8" />
      <rect x="235" y="98" width="30" height="24" rx="5" fill="#8fb6ff" />
      <path d="M241 98v-7a9 9 0 0 1 18 0v7" fill="none" stroke="#8fb6ff" strokeWidth="5" strokeLinecap="round" />
      <circle cx="250" cy="108" r="3.5" fill="#12266f" />
      <rect x="248.5" y="108" width="3" height="8" rx="1.5" fill="#12266f" />
    </svg>
  );
}

export function MountainArt({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 220 130" className={className} aria-hidden="true" focusable="false">
      <path d="M0 130 60 62l24 22 42-62 94 108Z" fill="#ffffff" fillOpacity="0.14" />
      <path d="M40 130 112 40l36 38 28-24 44 76Z" fill="#ffffff" fillOpacity="0.1" />
      <path d="m126 22 12 18-12 6-12-6 12-18Z" fill="#ffffff" fillOpacity="0.5" />
      <path d="M126 22V4" stroke="#fff" strokeOpacity="0.7" strokeWidth="2" />
      <path d="M126 4h16l-5 5 5 5h-16Z" fill="#8fb6ff" />
    </svg>
  );
}

export function LaptopArt({ className }: { className?: string }) {
  const id = useId();
  return (
    <svg viewBox="0 0 200 130" className={className} aria-hidden="true" focusable="false">
      <defs>
        <linearGradient id={id} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#4d9bff" />
          <stop offset="100%" stopColor="#7c3aed" />
        </linearGradient>
      </defs>
      <ellipse cx="100" cy="112" rx="80" ry="10" fill="#3b6bff" fillOpacity="0.2" />
      <g stroke="#3b6bff" strokeOpacity="0.5" fill="none">
        <path d="M20 60 60 30l20 14M180 50l-30-20-20 10M30 90l20-8" />
      </g>
      <path d="M50 30h100a4 4 0 0 1 4 4v58H46V34a4 4 0 0 1 4-4Z" fill="#0b1a55" stroke={`url(#${id})`} strokeWidth="3" />
      <path d="M36 96h128l8 12H28Z" fill="#12266f" stroke={`url(#${id})`} strokeWidth="2" />
      <rect x="88" y="52" width="24" height="20" rx="4" fill="#8fb6ff" />
      <path d="M93 52v-5a7 7 0 0 1 14 0v5" fill="none" stroke="#8fb6ff" strokeWidth="4" strokeLinecap="round" />
    </svg>
  );
}
