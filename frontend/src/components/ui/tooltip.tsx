import { type ReactNode, useId } from "react";

/**
 * CSS-only tooltip for short hints on icon buttons. Shows on hover AND keyboard
 * focus, and is linked to the trigger with aria-describedby (children receive the id).
 */
export function Tooltip({ text, children }: { text: string; children: (describedBy: string) => ReactNode }) {
  const id = useId();
  return (
    <span className="group/tip relative inline-flex">
      {children(id)}
      <span
        id={id}
        role="tooltip"
        className="pointer-events-none absolute left-1/2 top-full z-50 mt-2 -translate-x-1/2 whitespace-nowrap rounded-md border border-border-strong bg-surface-raised px-2 py-1 text-xs text-text-primary opacity-0 shadow-pop transition-opacity duration-150 group-focus-within/tip:opacity-100 group-hover/tip:opacity-100"
      >
        {text}
      </span>
    </span>
  );
}
