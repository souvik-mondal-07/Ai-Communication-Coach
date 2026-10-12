import { type KeyboardEvent, useCallback, useEffect, useId, useMemo, useRef, useState } from "react";
import { Bot, CornerDownLeft, Search } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { SEARCH_DESTINATIONS } from "@/components/common/navigation";
import { useDismiss } from "@/hooks/useDismiss";
import { cn } from "@/lib/utils";

const MENTOR = { label: "Open AI Mentor", path: "/mentor", keywords: "ask chat help question" };
const isMac = typeof navigator !== "undefined" && /mac/i.test(navigator.platform);

/**
 * Jump-to-page search. It only searches the app's own pages (no content index
 * exists), and always offers the AI Mentor so a question has somewhere to go.
 * Ctrl/Cmd+K focuses it.
 */
export function HeaderSearch() {
  const navigate = useNavigate();
  const listId = useId();
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const wrapRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const close = useCallback(() => setOpen(false), []);
  useDismiss(wrapRef, open, close);

  const results = useMemo(() => {
    const q = query.trim().toLowerCase();
    const pages = q ? SEARCH_DESTINATIONS.filter((d) => `${d.label} ${d.keywords}`.toLowerCase().includes(q)) : SEARCH_DESTINATIONS.slice(0, 6);
    return [...pages.slice(0, 7), MENTOR];
  }, [query]);

  useEffect(() => {
    function onKey(e: globalThis.KeyboardEvent) {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        inputRef.current?.focus();
        setOpen(true);
      }
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, []);

  function go(path: string) {
    setOpen(false);
    setQuery("");
    inputRef.current?.blur();
    navigate(path);
  }

  function onKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setOpen(true);
      setActive((i) => (i + 1) % results.length);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive((i) => (i - 1 + results.length) % results.length);
    } else if (e.key === "Enter" && open) {
      e.preventDefault();
      go(results[Math.min(active, results.length - 1)].path);
    }
  }

  return (
    <div ref={wrapRef} className="relative w-full max-w-[34rem]">
      <Search size={18} className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-text-muted" aria-hidden="true" />
      <input
        ref={inputRef}
        type="search"
        role="combobox"
        aria-expanded={open}
        aria-controls={listId}
        aria-autocomplete="list"
        aria-activedescendant={open ? `${listId}-${active}` : undefined}
        aria-label="Search pages or open your mentor"
        placeholder="Search for topics, labs, or ask your mentor..."
        value={query}
        onChange={(e) => {
          setQuery(e.target.value);
          setActive(0);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        onKeyDown={onKeyDown}
        className="h-11 w-full rounded-[var(--radius-panel)] border border-border-strong bg-surface-raised/60 pl-10 pr-16 text-sm text-text-primary transition-[border-color,box-shadow] duration-200 placeholder:text-text-muted focus:border-signal focus:outline-none focus:ring-2 focus:ring-signal/30 [&::-webkit-search-cancel-button]:hidden"
      />
      <kbd className="pointer-events-none absolute right-3 top-1/2 hidden -translate-y-1/2 rounded border border-border-strong px-1.5 py-0.5 text-[11px] text-text-muted sm:block" aria-hidden="true">
        {isMac ? "⌘" : "Ctrl"} K
      </kbd>

      {open && (
        <ul id={listId} role="listbox" aria-label="Search results" className="glass animate-pop-in absolute left-0 right-0 z-30 mt-2 origin-top overflow-hidden rounded-[var(--radius-card)] border border-border-strong p-1.5 shadow-pop">
          {results.map((r, i) => (
            <li
              key={r.path + r.label}
              id={`${listId}-${i}`}
              role="option"
              aria-selected={i === active}
              onMouseEnter={() => setActive(i)}
              onMouseDown={(e) => e.preventDefault()}
              onClick={() => go(r.path)}
              className={cn("flex cursor-pointer items-center gap-2.5 rounded-md px-2.5 py-2 text-sm transition-colors", i === active ? "bg-surface-raised text-text-primary" : "text-text-secondary")}
            >
              {r.path === "/mentor" ? <Bot size={15} aria-hidden="true" /> : <Search size={15} aria-hidden="true" />}
              <span className="flex-1 truncate">{r.label}</span>
              {i === active && <CornerDownLeft size={14} className="text-text-muted" aria-hidden="true" />}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
