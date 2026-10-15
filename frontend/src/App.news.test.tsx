// @vitest-environment jsdom
/**
 * Phase 22 navigation tests. These render the REAL <App /> (real routes, guards, layouts and the
 * real News page) in jsdom with a router, so redirects actually happen. Only the network is faked:
 * the shared Axios instance gets a fake adapter, which also lets us assert what was sent.
 */
import { act, useEffect } from "react";
import { createRoot, type Root } from "react-dom/client";
import { MemoryRouter, useLocation } from "react-router-dom";
import { AxiosError, type InternalAxiosRequestConfig } from "axios";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "@/App";
import { api } from "@/services/api";
import { clearStoredToken, setStoredToken } from "@/services/tokenStorage";
import { useAuthStore } from "@/store/authStore";
import type { NewsArticle } from "@/types/news";

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const FRESH = {
  state: "fresh", last_successful_refresh_at: new Date().toISOString(), last_attempt_at: null, refreshing: false,
  refresh_interval_minutes: 30, sources_ok: 8, sources_failed: 0, message: null,
};
const article = (n: number, over: Partial<NewsArticle> = {}): NewsArticle => ({
  id: String(n).padStart(24, "0"), title: `Headline number ${n}`, summary: `Excerpt ${n}`, url: `https://krebsonsecurity.com/a${n}`,
  source_id: "krebs", source_name: "Krebs on Security", category: "malware", published_at: new Date(Date.now() - n * 3_600_000).toISOString(),
  first_seen_at: new Date().toISOString(), image_url: null, cve_ids: [], severity: null, ...over,
});
const CATEGORIES = { total: 3, categories: [{ id: "malware", label: "Malware & ransomware", description: "d", count: 3 }, { id: "careers", label: "Careers & skills", description: "d", count: 0 }] };
const SOURCES = [{ id: "krebs", name: "Krebs on Security", homepage_url: "https://krebsonsecurity.com/", kind: "rss", status: "ok", last_success_at: null, last_error: null, article_count: 3 }];

type Handler = (config: InternalAxiosRequestConfig) => unknown;
let requests: InternalAxiosRequestConfig[] = [];
let newsHandler: Handler;

function respond(config: InternalAxiosRequestConfig, data: unknown, status = 200) {
  const response = { data, status, statusText: "", headers: {}, config };
  if (status >= 400) throw new AxiosError("fail", "ERR_BAD_RESPONSE", config, null, response as never);
  return response;
}

const defaultNews: Handler = (config) => {
  const page = Number(config.params?.page ?? 1);
  if (config.params?.severity) return { success: true, message: "", data: { items: [], total: 0, page: 1, limit: 3, has_more: false, freshness: FRESH } };
  const all = [1, 2, 3].map((n) => article(n));
  const q = String(config.params?.q ?? "").toLowerCase();
  const items = all.filter((a) => a.title.toLowerCase().includes(q));
  return { success: true, message: "", data: { items: page === 1 ? items : [article(4)], total: items.length, page, limit: 12, has_more: false, freshness: FRESH } };
};

let root: Root;
let container: HTMLDivElement;
let lastPath = "";

function Probe() {
  const { pathname } = useLocation();
  useEffect(() => { lastPath = pathname; }, [pathname]); // not during render
  return null;
}

async function waitFor(check: () => boolean, ms = 4000) {
  const start = Date.now();
  while (!check()) {
    if (Date.now() - start > ms) throw new Error(`Timed out. Path=${lastPath}. DOM:\n${container.textContent?.slice(0, 600)}`);
    await act(async () => { await new Promise((r) => setTimeout(r, 25)); });
  }
}
const text = () => container.textContent ?? "";

async function visit(path: string) {
  await act(async () => {
    // key: MemoryRouter ignores a new initialEntries on re-render, so remount per visit.
    root.render(<MemoryRouter key={path} initialEntries={[path]}><App /><Probe /></MemoryRouter>);
  });
}

function signedIn() {
  useAuthStore.setState({ isAuthenticated: true, user: { id: "u1", name: "Ada Lovelace", email: "ada@example.com" }, accessToken: "tok", isLoading: false, loadCurrentUser: async () => undefined });
}
function visitor() {
  useAuthStore.setState({ isAuthenticated: false, user: null, accessToken: null, isLoading: false, loadCurrentUser: async () => undefined });
}

beforeEach(() => {
  requests = [];
  newsHandler = defaultNews;
  window.scrollTo = vi.fn();
  window.matchMedia = window.matchMedia ?? ((q: string) => ({ matches: false, media: q, addEventListener() {}, removeEventListener() {}, addListener() {}, removeListener() {}, onchange: null, dispatchEvent: () => false }) as MediaQueryList);
  window.HTMLElement.prototype.scrollIntoView = vi.fn();
  (globalThis as Record<string, unknown>).ResizeObserver ??= class { observe() {} unobserve() {} disconnect() {} };
  (globalThis as Record<string, unknown>).IntersectionObserver ??= class { observe() {} unobserve() {} disconnect() {} takeRecords() { return []; } };
  api.defaults.adapter = async (config) => {
    requests.push(config);
    const url = config.url ?? "";
    if (url === "/news") return respond(config, newsHandler(config)) as never;
    if (url === "/news/categories") return respond(config, { success: true, message: "", data: CATEGORIES }) as never;
    if (url === "/news/sources") return respond(config, { success: true, message: "", data: { sources: SOURCES } }) as never;
    return respond(config, { success: false, message: "Not available in tests.", error_code: "NOT_FOUND" }, 404) as never;
  };
  container = document.createElement("div");
  document.body.appendChild(container);
  root = createRoot(container);
});

afterEach(async () => {
  await act(async () => root.unmount());
  container.remove();
  clearStoredToken();
  vi.restoreAllMocks();
});

describe("visitor (not signed in)", () => {
  beforeEach(visitor);

  it("can open /news directly: no redirect to login, public shell, articles shown", async () => {
    await visit("/news");
    await waitFor(() => text().includes("Headline number 1"));
    expect(lastPath).toBe("/news");
    expect(container.querySelector("h1")?.textContent).toContain("Cybersecurity News");
    expect(text()).toContain("Log in");
    expect(text()).toContain("Sign up");
    expect(text()).not.toContain("AI Mentor"); // no private app sidebar for visitors
    expect(container.querySelectorAll("article")).toHaveLength(3);
  });

  it("is offered login/sign-up without being blocked from reading", async () => {
    await visit("/news");
    await waitFor(() => text().includes("Headline number 1"));
    const hrefs = [...container.querySelectorAll("a")].map((a) => a.getAttribute("href"));
    expect(hrefs).toContain("/login");
    expect(hrefs).toContain("/register");
    expect(text()).toContain("Create free account");
  });

  it("sends no Authorization header to the news API, even with a stale token in storage", async () => {
    setStoredToken("stale-or-expired-token");
    await visit("/news");
    await waitFor(() => text().includes("Headline number 1"));
    const newsCalls = requests.filter((r) => (r.url ?? "").startsWith("/news"));
    expect(newsCalls.length).toBeGreaterThanOrEqual(3);
    for (const call of newsCalls) expect(call.headers.get("Authorization")).toBeUndefined();
  });

  it("is redirected from '/' to the public news, not the login page", async () => {
    await visit("/");
    await waitFor(() => lastPath === "/news");
    await waitFor(() => text().includes("Headline number 1"));
  });

  it.each(["/dashboard", "/mentor", "/history", "/profile", "/progress", "/notifications", "/settings"])("is still sent to /login from private route %s", async (path) => {
    await visit(path);
    await waitFor(() => lastPath === "/login");
    expect(text()).not.toContain("Headline number");
    expect(requests.filter((r) => (r.url ?? "").startsWith("/news"))).toHaveLength(0);
  });

  it("unknown URLs still go through the guarded app, not the news", async () => {
    await visit("/no-such-page");
    await waitFor(() => lastPath === "/login");
  });

  it("finds a visible path to the news from the login and register pages", async () => {
    for (const page of ["/login", "/register"]) {
      await visit(page);
      await waitFor(() => lastPath === page && text().includes("Read cybersecurity news"));
      const link = [...container.querySelectorAll("a")].find((a) => a.textContent?.includes("Read cybersecurity news"));
      expect(link?.getAttribute("href")).toBe("/news");
    }
    const link = [...container.querySelectorAll("a")].find((a) => a.textContent?.includes("Read cybersecurity news"))!;
    await act(async () => { link.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true, button: 0 })); });
    await waitFor(() => lastPath === "/news");
    await waitFor(() => text().includes("Headline number 1"));
  });
});

describe("signed-in user", () => {
  beforeEach(signedIn);

  it("sees /news inside the normal app shell (sidebar), not the public header", async () => {
    await visit("/news");
    await waitFor(() => text().includes("Headline number 1"));
    expect(lastPath).toBe("/news");
    expect(text()).toContain("AI Mentor"); // sidebar present
    expect(text()).not.toContain("Sign up");
    expect(text()).not.toContain("Create free account");
    const navLink = [...container.querySelectorAll("nav a")].find((a) => a.getAttribute("href") === "/news");
    expect(navLink?.textContent).toContain("Cybersecurity News");
  });

  it("goes from '/' to the dashboard and keeps private routes reachable", async () => {
    await visit("/");
    await waitFor(() => lastPath === "/dashboard");
    await visit("/history");
    await waitFor(() => lastPath === "/history");
  });

  it("is still bounced away from the login page", async () => {
    await visit("/login");
    await waitFor(() => lastPath === "/dashboard");
  });
});

describe("news page states (real page, faked network)", () => {
  beforeEach(visitor);

  it("shows a skeleton first, then articles with working source links", async () => {
    let release!: () => void;
    const gate = new Promise<void>((r) => { release = r; });
    const original = api.defaults.adapter as (c: InternalAxiosRequestConfig) => Promise<never>;
    api.defaults.adapter = async (config) => { if (config.url === "/news" && !config.params?.severity) await gate; return original(config); };
    await visit("/news");
    await waitFor(() => !!container.querySelector('[aria-label="Loading articles"]'));
    expect(container.querySelector('section[aria-label="Articles"]')?.getAttribute("aria-busy")).toBe("true");
    await act(async () => release());
    await waitFor(() => text().includes("Headline number 1"));
    const link = [...container.querySelectorAll("article a")].find((a) => a.textContent?.includes("Read at Krebs on Security"))!;
    expect(link.getAttribute("href")).toBe("https://krebsonsecurity.com/a1");
    expect(link.getAttribute("target")).toBe("_blank");
    expect(link.getAttribute("rel")).toBe("noopener noreferrer");
  });

  it("shows a recoverable error with Retry, then recovers", async () => {
    let failures = 1;
    newsHandler = (config) => {
      if (failures > 0 && !config.params?.severity) { failures -= 1; return respond(config, { success: false, message: "Database is currently unavailable.", error_code: "SERVICE_UNAVAILABLE" }, 503); }
      return defaultNews(config);
    };
    await visit("/news");
    await waitFor(() => !!container.querySelector('[role="alert"]'));
    expect(text()).toContain("Database is currently unavailable.");
    const retry = [...container.querySelectorAll("button")].find((b) => b.textContent?.includes("Retry"))!;
    await act(async () => retry.click());
    await waitFor(() => text().includes("Headline number 1"));
    expect(container.querySelector('[role="alert"]')).toBeNull();
  });

  it("explains an empty search and clears it", async () => {
    await visit("/news");
    await waitFor(() => text().includes("Headline number 1"));
    const input = container.querySelector<HTMLInputElement>("#news-search")!;
    await act(async () => {
      Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")!.set!.call(input, "zzz-nothing");
      input.dispatchEvent(new Event("input", { bubbles: true }));
    });
    await waitFor(() => text().includes("No articles match “zzz-nothing”"));
    expect(requests.some((r) => r.params?.q === "zzz-nothing")).toBe(true);
    const clear = [...container.querySelectorAll("button")].find((b) => b.textContent === "Clear filters")!;
    await act(async () => clear.click());
    await waitFor(() => text().includes("Headline number 1"));
  });

  it("filters by category through the API and marks the active chip", async () => {
    await visit("/news");
    await waitFor(() => text().includes("Headline number 1") && text().includes("Malware & ransomware"));
    const chip = [...container.querySelectorAll("nav[aria-label='News categories'] button")].find((b) => b.textContent?.includes("Malware"))!;
    await act(async () => chip.dispatchEvent(new MouseEvent("click", { bubbles: true })));
    await waitFor(() => requests.some((r) => r.url === "/news" && r.params?.category === "malware"));
    expect(chip.getAttribute("aria-pressed")).toBe("true");
  });

  it("loads more articles and appends them without duplicates", async () => {
    newsHandler = (config) => {
      if (config.params?.severity) return defaultNews(config);
      const page = Number(config.params?.page ?? 1);
      const items = page === 1 ? [article(1), article(2)] : [article(2), article(3)];
      return { success: true, message: "", data: { items, total: 3, page, limit: 2, has_more: page === 1, freshness: FRESH } };
    };
    await visit("/news");
    await waitFor(() => text().includes("Headline number 2"));
    const more = [...container.querySelectorAll("button")].find((b) => b.textContent?.includes("Load more"))!;
    await act(async () => more.click());
    await waitFor(() => text().includes("Headline number 3"));
    expect(container.querySelectorAll("article")).toHaveLength(3); // article 2 was not duplicated
    expect(text()).toContain("reached the end");
  });

  it("warns honestly when the server is serving stale cache", async () => {
    newsHandler = (config) => {
      const base = defaultNews(config) as { data: { freshness: unknown } };
      return { ...base, data: { ...base.data, freshness: { ...FRESH, state: "degraded", last_successful_refresh_at: new Date(Date.now() - 8 * 3_600_000).toISOString(), message: "Live refresh is failing" } } };
    };
    await visit("/news");
    await waitFor(() => text().includes("Showing cached articles"));
    expect(container.querySelector('[role="alert"]')?.textContent).toContain("Last successful update 8 hours ago");
    expect(text()).toContain("Headline number 1"); // articles are still shown
  });

  it("shows the critical-CVE strip only when critical items exist", async () => {
    await visit("/news");
    await waitFor(() => text().includes("Headline number 1"));
    expect(text()).not.toContain("Critical-severity CVEs this week");
    await act(async () => root.unmount());
    root = createRoot(container);
    newsHandler = (config) => config.params?.severity
      ? { success: true, message: "", data: { items: [article(9, { title: "CVE-2026-7001: Flaw", cve_ids: ["CVE-2026-7001"], severity: { level: "critical", score: 9.8, scheme: "CVSS v3.1", assigned_by: "NVD" } })], total: 1, page: 1, limit: 3, has_more: false, freshness: FRESH } }
      : defaultNews(config);
    await visit("/news");
    await waitFor(() => text().includes("Critical-severity CVEs this week"));
    expect(text()).toContain("CVE-2026-7001");
  });
});
