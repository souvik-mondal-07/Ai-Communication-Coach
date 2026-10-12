import type { CSSProperties } from "react";

/**
 * Single place for entrance-motion helpers. `reveal(i)` returns the props for a
 * staggered fade-and-rise (defined as the `reveal` utility in index.css).
 */
export function reveal(index = 0): { className: string; style: CSSProperties } {
  return { className: "reveal", style: { "--i": index } as CSSProperties };
}
