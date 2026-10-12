import {
  AudioLines, BarChart3, Bot, CalendarCheck, Flag, Gauge, History, LayoutDashboard,
  MessagesSquare, Mic, Settings, ShieldHalf, Target, TrendingUp, UserRound, type LucideIcon,
} from "lucide-react";

export interface NavItem {
  label: string;
  path: string;
  icon: LucideIcon;
}
export interface NavSection {
  heading?: string;
  items: NavItem[];
}

/** Sidebar structure. Same routes and order as before Phase 21. */
export const NAV_SECTIONS: NavSection[] = [
  {
    items: [
      { label: "Dashboard", path: "/dashboard", icon: LayoutDashboard },
      { label: "AI Mentor", path: "/mentor", icon: Bot },
    ],
  },
  {
    heading: "Train",
    items: [
      { label: "Cybersecurity", path: "/cybersecurity", icon: ShieldHalf },
      { label: "Daily Practice", path: "/daily-practice", icon: CalendarCheck },
      { label: "Practice", path: "/practice", icon: Target },
      { label: "CTF & Labs", path: "/ctf", icon: Flag },
      { label: "Communication", path: "/communication", icon: MessagesSquare },
      { label: "Voice Conversation", path: "/voice-conversation", icon: AudioLines },
      { label: "Interview", path: "/interview", icon: Mic },
      { label: "Pressure Training", path: "/pressure-training", icon: Gauge },
    ],
  },
  {
    heading: "Track",
    items: [
      { label: "Progress", path: "/progress", icon: TrendingUp },
      { label: "Analytics", path: "/analytics", icon: BarChart3 },
      { label: "History", path: "/history", icon: History },
    ],
  },
  {
    heading: "Account",
    items: [
      { label: "Profile", path: "/profile", icon: UserRound },
      { label: "Settings", path: "/settings", icon: Settings },
    ],
  },
];

/** Routes that are reachable but not in the sidebar. */
const EXTRA_LABELS: Record<string, string> = { notifications: "Notifications" };

const ROOT_LABELS: Record<string, string> = {
  ...EXTRA_LABELS,
  ...Object.fromEntries(NAV_SECTIONS.flatMap((s) => s.items).map((i) => [i.path.slice(1), i.label])),
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
