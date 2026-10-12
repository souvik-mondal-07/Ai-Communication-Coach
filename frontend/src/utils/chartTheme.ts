import type { CSSProperties } from "react";

/**
 * Chart colors as CSS variables, so charts follow the active light/dark theme
 * instead of hardcoded hex values.
 */
export const chartColors = {
  signal: "var(--color-signal)",
  violet: "var(--color-violet)",
  success: "var(--color-success)",
  warn: "var(--color-warn)",
  danger: "var(--color-danger)",
  muted: "var(--color-text-muted)",
  grid: "var(--color-border)",
  gridStrong: "var(--color-border-strong)",
} as const;

export const chartTooltipStyle: CSSProperties = {
  background: "var(--color-surface-raised)",
  border: "1px solid var(--color-border-strong)",
  borderRadius: 10,
  boxShadow: "var(--shadow-pop)",
  color: "var(--color-text-primary)",
  fontSize: 12,
};

export const chartLabelStyle: CSSProperties = { color: "var(--color-text-secondary)" };
