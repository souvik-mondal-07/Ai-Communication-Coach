import { Flag, Gauge, AudioLines, MessagesSquare, Mic, ShieldHalf, type LucideIcon } from "lucide-react";
import type {
  DateRangePreset,
  HistoryActivityType,
  HistoryFilters,
  HistoryQuery,
  HistoryStatus,
} from "@/types/history";

export const PAGE_SIZE = 20;

interface TypeMeta {
  icon: LucideIcon;
  /** Short label for filter tabs. */
  tab: string;
  /** Where this module lives (also where "start one" links go). */
  modulePath: string;
  /** Base of the existing session page, used to continue an unfinished session. */
  sessionPath: string;
  empty: { title: string; hint: string; cta: string };
}

export const TYPE_META: Record<HistoryActivityType, TypeMeta> = {
  cybersecurity_practice: {
    icon: ShieldHalf,
    tab: "Cybersecurity",
    modulePath: "/cybersecurity",
    sessionPath: "/cybersecurity/practice",
    empty: {
      title: "No practice sessions yet.",
      hint: "Pick a topic and answer a few questions to see your results here.",
      cta: "Start practicing",
    },
  },
  ctf: {
    icon: Flag,
    tab: "CTF/Lab",
    modulePath: "/ctf",
    sessionPath: "/ctf",
    empty: {
      title: "No CTF or lab sessions yet.",
      hint: "Get guided help on a challenge to build a record here.",
      cta: "Open CTF & Labs",
    },
  },
  communication: {
    icon: MessagesSquare,
    tab: "Communication",
    modulePath: "/communication",
    sessionPath: "/communication",
    empty: {
      title: "No communication sessions yet.",
      hint: "Practice a real-life conversation to see your feedback here.",
      cta: "Practice communication",
    },
  },
  interview: {
    icon: Mic,
    tab: "Interview",
    modulePath: "/interview",
    sessionPath: "/interview",
    empty: {
      title: "No interview sessions yet.",
      hint: "Start your first cybersecurity interview to see your results here.",
      cta: "Start an interview",
    },
  },
  pressure_training: {
    icon: Gauge,
    tab: "Pressure Training",
    modulePath: "/pressure-training",
    sessionPath: "/pressure-training",
    empty: {
      title: "No pressure training sessions yet.",
      hint: "Practice staying composed under pressure to see your results here.",
      cta: "Start pressure training",
    },
  },
  voice_conversation: {
    icon: AudioLines,
    tab: "Voice",
    modulePath: "/voice-conversation",
    sessionPath: "/voice-conversation",
    empty: {
      title: "No voice conversations yet.",
      hint: "Start a voice practice session to build your communication skills.",
      cta: "Start a voice conversation",
    },
  },
};

export const ACTIVITY_TYPES = Object.keys(TYPE_META) as HistoryActivityType[];

export function isActivityType(value: string | undefined): value is HistoryActivityType {
  return value !== undefined && value in TYPE_META;
}

export const STATUS_LABELS: Record<HistoryStatus, string> = {
  completed: "Completed",
  in_progress: "In progress",
  abandoned: "Ended early",
};

export const RANGE_LABELS: Record<DateRangePreset, string> = {
  all: "All time",
  today: "Today",
  "7d": "Last 7 days",
  "30d": "Last 30 days",
  custom: "Custom range",
};

export const DEFAULT_FILTERS: HistoryFilters = {
  type: "all",
  search: "",
  range: "all",
  customStart: "",
  customEnd: "",
  sort: "newest",
};

/** Parse a yyyy-mm-dd value as a local date (not UTC), at the start or end of that day. */
function localDay(value: string, endOfDay: boolean): Date | null {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  if (!match) return null;
  const [, y, m, d] = match.map(Number);
  return endOfDay ? new Date(y, m - 1, d, 23, 59, 59, 999) : new Date(y, m - 1, d, 0, 0, 0, 0);
}

/** The date bounds for a filter, in the user's local time, as ISO strings the API accepts. */
export function dateBounds(
  filters: Pick<HistoryFilters, "range" | "customStart" | "customEnd">,
  now: Date = new Date()
): { start?: string; end?: string } {
  switch (filters.range) {
    case "today":
      return { start: new Date(now.getFullYear(), now.getMonth(), now.getDate()).toISOString() };
    case "7d":
      return { start: new Date(now.getTime() - 7 * 86_400_000).toISOString() };
    case "30d":
      return { start: new Date(now.getTime() - 30 * 86_400_000).toISOString() };
    case "custom": {
      const start = localDay(filters.customStart, false);
      const end = localDay(filters.customEnd, true);
      return { start: start?.toISOString(), end: end?.toISOString() };
    }
    default:
      return {};
  }
}

/** A custom range whose start is after its end can't be sent; the UI explains instead. */
export function isInvalidCustomRange(filters: HistoryFilters): boolean {
  if (filters.range !== "custom" || !filters.customStart || !filters.customEnd) return false;
  return filters.customStart > filters.customEnd;
}

export function toQuery(filters: HistoryFilters, page: number): HistoryQuery {
  const { start, end } = dateBounds(filters);
  const search = filters.search.trim();
  return {
    type: filters.type === "all" ? undefined : filters.type,
    search: search || undefined,
    start_date: start,
    end_date: end,
    sort: filters.sort,
    page,
    limit: PAGE_SIZE,
  };
}

export function hasActiveFilters(filters: HistoryFilters): boolean {
  return filters.search.trim() !== "" || filters.range !== "all";
}

export function formatElapsed(totalSeconds: number): string {
  if (totalSeconds < 60) return `${totalSeconds} sec`;
  const minutes = Math.round(totalSeconds / 60);
  if (minutes < 60) return `${minutes} min`;
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  return rest ? `${hours} hr ${rest} min` : `${hours} hr`;
}
