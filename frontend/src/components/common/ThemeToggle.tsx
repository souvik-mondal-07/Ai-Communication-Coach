import { useEffect, useState } from "react";
import { Moon, Sun } from "lucide-react";
import { useProfileStore } from "@/store/profileStore";
import { applyTheme } from "@/utils/theme";

function current(): "light" | "dark" {
  return document.documentElement.dataset.theme === "light" ? "light" : "dark";
}

/** Switches light/dark. Applies immediately and saves to the account when the profile is loaded. */
export function ThemeToggle() {
  const [theme, setTheme] = useState(current);

  // The profile load can change the theme after mount; follow <html data-theme>.
  useEffect(() => {
    const obs = new MutationObserver(() => setTheme(current()));
    obs.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
    return () => obs.disconnect();
  }, []);

  function toggle() {
    const next = theme === "dark" ? "light" : "dark";
    applyTheme(next);
    setTheme(next);
    if (useProfileStore.getState().profile) void useProfileStore.getState().savePreferences({ theme: next }).catch(() => undefined);
  }

  const Icon = theme === "dark" ? Moon : Sun;
  return (
    <button
      type="button"
      onClick={toggle}
      aria-label={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
      className="rounded-[var(--radius-panel)] p-2 text-text-secondary transition-[background-color,color,transform] duration-150 hover:bg-surface-raised hover:text-text-primary active:scale-95"
    >
      <Icon size={20} strokeWidth={1.75} aria-hidden="true" />
    </button>
  );
}
