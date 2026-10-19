import {
  BrainCircuit, Bell, Calculator, ChartColumn, Clock, Flag, House, MessageCircle, MessageSquare, Mic, Newspaper, Settings, Shield, UserRound, type LucideIcon,
} from "lucide-react";

export interface NavItem {
  label: string;
  path: string;
  icon: LucideIcon;
  /** Short name for breadcrumbs / document title when it differs from the sidebar label. */
  title?: string;
  /** Other top-level routes that should light this item up. */
  alsoActiveFor?: string[];
  /** Show the unread-notification count on this item. */
  badge?: "notifications";
}
export interface NavSection {
  heading?: string;
  items: NavItem[];
}

/**
 * Sidebar structure (Phase 21 redesign). Every path is an existing route.
 * /practice, /daily-practice and /analytics are still routable and are linked
 * from the dashboard, Today's Practice and the Progress page respectively.
 */
export const NAV_SECTIONS: NavSection[] = [
  {
    items: [
      { label: "Dashboard", path: "/dashboard", icon: House },
      { label: "AI Mentor", path: "/mentor", icon: MessageSquare },
      { label: "Cybersecurity Learning", path: "/cybersecurity", icon: Shield, title: "Cybersecurity" },
      { label: "Cybersecurity News", path: "/news", icon: Newspaper, title: "Cybersecurity News" },
      { label: "CTF & Labs", path: "/ctf", icon: Flag },
      { label: "Communication Practice", path: "/communication", icon: MessageCircle, title: "Communication" },
      { label: "Interview Simulator", path: "/interview", icon: UserRound, title: "Interview" },
      { label: "Pressure Training", path: "/pressure-training", icon: BrainCircuit },
      { label: "Aptitude Practice", path: "/aptitude", icon: Calculator, title: "Aptitude" },
      { label: "Voice Conversation", path: "/voice-conversation", icon: Mic },
      { label: "Progress & Analytics", path: "/progress", icon: ChartColumn, title: "Progress", alsoActiveFor: ["/analytics"] },
      { label: "History", path: "/history", icon: Clock },
      { label: "Notifications", path: "/notifications", icon: Bell, badge: "notifications" },
      { label: "Profile", path: "/profile", icon: UserRound },
      { label: "Settings", path: "/settings", icon: Settings },
    ],
  },
];

/** Routes that are reachable but not in the sidebar. */
const EXTRA_LABELS: Record<string, string> = { analytics: "Analytics", practice: "Practice", "daily-practice": "Daily Practice" };

const ROOT_LABELS: Record<string, string> = {
  ...EXTRA_LABELS,
  ...Object.fromEntries(NAV_SECTIONS.flatMap((s) => s.items).map((i) => [i.path.slice(1), i.title ?? i.label])),
};

export const APP_FALLBACK_TITLE = "AI Cybersecurity Mentor";

export interface Crumb {
  label: string;
  /** Present for ancestors; the current page has no link. */
  to?: string;
}

function detailLabel(root: string, second: string): string {
  if (root === "cybersecurity") return second === "practice" ? "Practice session" : "Topic";
  if (root === "history") return "Details";
  if (root === "aptitude") return second === "result" ? "Result" : "Session";
  return "Session";
}

/** Breadcrumb trail for a pathname, e.g. /ctf/abc123 -> CTF & Labs / Session. */
export function breadcrumbsFor(pathname: string): Crumb[] {
  const segs = pathname.split("/").filter(Boolean);
  const root = segs[0];
  if (!root) return [{ label: APP_FALLBACK_TITLE }];
  const rootLabel = ROOT_LABELS[root] ?? APP_FALLBACK_TITLE;
  if (segs.length === 1) return [{ label: rootLabel }];
  return [{ label: rootLabel, to: `/${root}` }, { label: detailLabel(root, segs[1]) }];
}

/** Text for document.title, most specific part first. */
export function documentTitleFor(pathname: string): string {
  const crumbs = breadcrumbsFor(pathname);
  const parts = crumbs.map((c) => c.label).reverse();
  return [...parts, APP_FALLBACK_TITLE].filter((p, i, a) => a.indexOf(p) === i).join(" · ");
}

/** True when `pathname` is the item's route, a child of it, or one of its alsoActiveFor routes. */
export function isNavItemActive(item: NavItem, pathname: string): boolean {
  return [item.path, ...(item.alsoActiveFor ?? [])].some((p) => pathname === p || pathname.startsWith(`${p}/`));
}

/** Pages offered by the header search. Same routes as the sidebar plus the sub-pages it does not list. */
export const SEARCH_DESTINATIONS: { label: string; path: string; keywords: string }[] = [
  ...NAV_SECTIONS.flatMap((s) => s.items).map((i) => ({ label: i.label, path: i.path, keywords: i.title ?? "" })),
  { label: "Daily Practice", path: "/daily-practice", keywords: "today streak plan" },
  { label: "Practice", path: "/practice", keywords: "questions quiz" },
  { label: "Analytics", path: "/analytics", keywords: "charts scores" },
];
