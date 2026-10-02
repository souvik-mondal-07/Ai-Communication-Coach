import type { ThemePreference } from "@/types/profile";

/**
 * Theme handling. The chosen preference ("light" | "dark" | "system") is kept in
 * localStorage so the right theme is applied immediately on refresh, and is also
 * saved to the user's account (preferences.theme) so it follows them across
 * devices. The resolved theme is exposed to CSS as `<html data-theme="light|dark">`.
 */

const THEME_KEY = "theme_preference";
const DEFAULT_THEME: ThemePreference = "system";

function isThemePreference(value: unknown): value is ThemePreference {
  return value === "light" || value === "dark" || value === "system";
}

export function getStoredTheme(): ThemePreference {
  try {
    const value = localStorage.getItem(THEME_KEY);
    return isThemePreference(value) ? value : DEFAULT_THEME;
  } catch {
    return DEFAULT_THEME;
  }
}

function resolveTheme(preference: ThemePreference): "light" | "dark" {
  if (preference !== "system") return preference;
  return window.matchMedia?.("(prefers-color-scheme: light)").matches ? "light" : "dark";
}

export function applyTheme(preference: ThemePreference): void {
  document.documentElement.dataset.theme = resolveTheme(preference);
  try {
    localStorage.setItem(THEME_KEY, preference);
  } catch {
    // Storage unavailable — the theme just won't persist across reloads locally.
  }
}

/** Call once before the first render. Also follows OS changes while set to "system". */
export function initTheme(): void {
  applyTheme(getStoredTheme());
  window.matchMedia?.("(prefers-color-scheme: light)").addEventListener("change", () => {
    if (getStoredTheme() === "system") applyTheme("system");
  });
}
