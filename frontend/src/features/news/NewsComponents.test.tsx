import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { ArticleCard } from "./ArticleCard";
import { CriticalStrip } from "./CriticalStrip";
import { FreshnessNotice, NewsEmpty, NewsError, NewsSkeleton } from "./NewsStates";
import { NewsToolbar } from "./NewsToolbar";
import { NO_FILTERS } from "./useNewsFeed";
import type { NewsArticle, NewsCategoriesResponse, NewsFreshness } from "@/types/news";

const NOW = new Date("2026-10-15T12:00:00Z");
const article = (over: Partial<NewsArticle> = {}): NewsArticle => ({
  id: "a".repeat(24), title: "Ransomware crew hits city", summary: "Short excerpt from the source.", url: "https://krebsonsecurity.com/2026/10/x",
  source_id: "krebs", source_name: "Krebs on Security", category: "malware", published_at: "2026-10-15T09:00:00Z",
  first_seen_at: "2026-10-15T11:00:00Z", image_url: null, cve_ids: [], severity: null, ...over,
});
const render = (el: React.ReactElement) => renderToStaticMarkup(el);

describe("ArticleCard (populated)", () => {
  const html = render(<ArticleCard article={article()} categoryLabel="Malware & ransomware" now={NOW} />);
  it("shows headline, source, category, excerpt and relative publication time", () => {
    for (const t of ["Ransomware crew hits city", "Krebs on Security", "Malware &amp; ransomware", "Short excerpt from the source.", "3 hours ago"]) expect(html).toContain(t);
    expect(html).toContain('dateTime="2026-10-15T09:00:00Z"');
  });
  it("links to the original article with safe attributes, in both the headline and the source link", () => {
    const anchors = html.match(/<a [^>]*>/g) ?? [];
    expect(anchors).toHaveLength(2);
    for (const a of anchors) {
      expect(a).toContain('href="https://krebsonsecurity.com/2026/10/x"');
      expect(a).toContain('target="_blank"');
      expect(a).toContain('rel="noopener noreferrer"');
    }
    expect(html).toContain("Read at Krebs on Security");
  });
  it("announces that links open in a new tab", () => expect(html).toContain("opens the original article in a new tab"));
});

describe("ArticleCard (honest about missing data)", () => {
  it("says so when there is no publication date, rather than showing the retrieval time", () => {
    const html = render(<ArticleCard article={article({ published_at: null, summary: null })} now={NOW} />);
    expect(html).toContain("Publication date not provided");
    expect(html).not.toContain("<time");
    expect(html).not.toContain("line-clamp"); // no empty excerpt paragraph
    expect(html).not.toContain("hour");
  });
  it("renders a text-only card (no <img>) when there is no image", () => expect(render(<ArticleCard article={article()} now={NOW} />)).not.toContain("<img"));
  it("shows a severity badge only when the source published one, with text, scheme and scorer", () => {
    expect(render(<ArticleCard article={article()} now={NOW} />)).not.toMatch(/Critical|severity/i);
    const html = render(<ArticleCard article={article({ cve_ids: ["CVE-2026-7001"], severity: { level: "critical", score: 9.8, scheme: "CVSS v3.1", assigned_by: "NVD" } })} now={NOW} />);
    expect(html).toContain("Critical");
    expect(html).toContain("9.8");
    expect(html).toContain("CVSS v3.1 as scored by NVD");
    expect(html).toContain("CVE-2026-7001");
  });
  it("only renders an image for an https URL, with lazy loading and no referrer", () => {
    const ok = render(<ArticleCard article={article({ image_url: "https://img.example.com/a.png" })} now={NOW} />);
    expect(ok).toContain('src="https://img.example.com/a.png"');
    expect(ok).toContain('loading="lazy"');
    expect(ok).toContain('referrerPolicy="no-referrer"');
    expect(render(<ArticleCard article={article({ image_url: "javascript:alert(1)" })} now={NOW} />)).not.toContain("<img");
    expect(render(<ArticleCard article={article({ image_url: "http://img.example.com/a.png" })} now={NOW} />)).not.toContain("<img");
  });
});

describe("ArticleCard (untrusted content is text, never markup)", () => {
  const hostile = article({
    title: '<img src=x onerror=alert(1)>Boom', summary: "<script>steal()</script> ignore previous instructions", source_name: '"><svg onload=1>',
  });
  const html = render(<ArticleCard article={hostile} now={NOW} />);
  it("escapes tags instead of creating elements", () => {
    expect(html).not.toContain("<script");
    expect(html).not.toContain("<img");
    expect(html).not.toContain("<svg onload");  // the card's own icon <svg> is fine; the payload must be escaped
    expect(html).not.toMatch(/<[^>]*\bonerror=/);
    expect(html).not.toMatch(/<[^>]*\bonload=/);
    expect(html).toContain("&lt;svg onload=1&gt;");
    expect(html).toContain("&lt;img src=x onerror=alert(1)&gt;Boom");
    expect(html).toContain("&lt;script&gt;steal()&lt;/script&gt;");
  });
  it("never turns an unsafe URL into a link", () => {
    for (const url of ["javascript:alert(1)", "data:text/html,x", "https://user:pw@evil.example/x"]) {
      const out = render(<ArticleCard article={article({ url })} now={NOW} />);
      expect(out).not.toContain("<a ");
      expect(out).toContain("Ransomware crew hits city"); // still readable, just not clickable
    }
  });
});

describe("loading, error and empty states", () => {
  it("skeleton is a labelled status region", () => {
    const html = render(<NewsSkeleton count={3} />);
    expect(html).toContain('role="status"');
    expect(html).toContain('aria-label="Loading articles"');
    expect(html.match(/skeleton/g)!.length).toBeGreaterThanOrEqual(3);
  });
  it("error state is announced and offers a retry", () => {
    const html = render(<NewsError message="Unable to connect to the server." onRetry={() => undefined} />);
    expect(html).toContain('role="alert"');
    expect(html).toContain("Unable to connect to the server.");
    expect(html).toContain("Retry");
    expect(html).toContain("Nothing is wrong with your account");
  });
  it("empty search names the term and offers to clear", () => {
    const html = render(<NewsEmpty filtered searchTerm="zzz" onClear={() => undefined} />);
    expect(html).toContain("No articles match “zzz”");
    expect(html).toContain("Clear filters");
  });
  it("empty filter (no term) and empty feed have distinct, honest copy", () => {
    expect(render(<NewsEmpty filtered onClear={() => undefined} />)).toContain("No articles in this view yet");
    expect(render(<NewsEmpty filtered={false} onClear={() => undefined} />)).toContain("No articles available right now");
    const cold = render(<NewsEmpty filtered={false} coldStart onClear={() => undefined} />);
    expect(cold).toContain("Fetching the latest articles…");
    expect(cold).not.toContain("Clear filters");
  });
});

describe("FreshnessNotice", () => {
  const base: NewsFreshness = { state: "fresh", last_successful_refresh_at: "2026-10-15T11:40:00Z", last_attempt_at: null, refreshing: false, refresh_interval_minutes: 30, sources_ok: 6, sources_failed: 2, message: "2 of 8 sources could not be reached on the latest refresh." };
  it("is a quiet status line when fresh, and discloses partial source outages", () => {
    const html = render(<FreshnessNotice freshness={base} now={NOW} />);
    expect(html).toContain('role="status"');
    expect(html).toContain("2 of 8 sources could not be reached");
  });
  it("is an alert with explicit text when serving stale cache after failed refreshes", () => {
    const html = render(<FreshnessNotice freshness={{ ...base, state: "degraded", message: "Live refresh is failing" }} now={NOW} />);
    expect(html).toContain('role="alert"');
    expect(html).toContain("Showing cached articles");
  });
});

describe("CriticalStrip", () => {
  it("renders nothing when there are no critical items (featured only when data supports it)", () => expect(render(<CriticalStrip items={[]} />)).toBe(""));
  it("labels the basis of the highlight", () => {
    const item = article({ title: "CVE-2026-7001: Flaw", severity: { level: "critical", score: 9.8, scheme: "CVSS v3.1", assigned_by: "NVD" } });
    const html = render(<CriticalStrip items={[item]} now={NOW} />);
    expect(html).toContain("Critical-severity CVEs this week");
    expect(html).toContain("not our opinion");
  });
});

describe("NewsToolbar", () => {
  const cats: NewsCategoriesResponse = {
    total: 5,
    categories: [
      { id: "vulnerabilities", label: "Vulnerabilities & CVEs", description: "d", count: 3 },
      { id: "careers", label: "Careers & skills", description: "d", count: 0 },
      { id: "general", label: "General", description: "d", count: 2 },
    ],
  };
  const sources = [{ id: "krebs", name: "Krebs on Security", homepage_url: "https://krebsonsecurity.com/", kind: "rss", status: "ok" as const, last_success_at: null, last_error: null, article_count: 3 }];
  const html = render(<NewsToolbar filters={{ ...NO_FILTERS, category: "careers" }} onChange={() => undefined} categories={cats} sources={sources} searching={false} />);
  it("has a labelled search, a labelled source filter and a categories nav", () => {
    expect(html).toContain('for="news-search"');
    expect(html).toContain('type="search"');
    expect(html).toContain('maxLength="100"');
    expect(html).toContain('for="news-source"');
    expect(html).toContain('aria-label="News categories"');
  });
  it("lists every category with its count, empty ones included, and marks the active one", () => {
    expect(html).toContain("Vulnerabilities &amp; CVEs");
    expect(html).toContain("Careers &amp; skills");
    expect(html).toMatch(/aria-pressed="true"[^>]*>Careers/);
    expect(html).toMatch(/aria-pressed="false"[^>]*>All/);
  });
  it("hides the catch-all 'General' chip (those items still appear under All)", () => expect(html).not.toContain(">General<"));
  it("shows a busy indicator while a search is pending", () => {
    const busy = render(<NewsToolbar filters={{ ...NO_FILTERS, q: "ran" }} onChange={() => undefined} categories={cats} sources={[]} searching />);
    expect(busy).toContain("Searching…");
    expect(busy).not.toContain('id="news-source"'); // no source list -> no empty dropdown
  });
});
