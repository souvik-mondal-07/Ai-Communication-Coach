import { renderToStaticMarkup } from "react-dom/server";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import type {
  AnalyticsMeta, CommunicationData, DomainsData, InsightsData, OverviewData, PressureData, SpeakingData, TrendsData,
} from "@/types/analytics";
import { DataBanner, SectionCard } from "./AnalyticsStates";
import { DomainsSection, ModesSection } from "./BreakdownSection";
import { CommunicationSection, SpeakingSection, WeaknessList } from "./CommunicationSection";
import { OverviewSection } from "./OverviewSection";
import { InsightsSection, PressureSection } from "./PressureAndInsights";
import { TrendsSection } from "./TrendsSection";

const render = (node: React.ReactNode) => renderToStaticMarkup(<MemoryRouter>{node}</MemoryRouter>);
const meta = (status: AnalyticsMeta["data"]["status"], sessions = 0): AnalyticsMeta => ({
  range: "30d", start: null, end: "2026-10-06T00:00:00+00:00", truncated: false,
  data: { status, sessions, message: status === "none" ? "Complete your first interview to unlock analytics." : null },
});

describe("states", () => {
  it("shows a labelled skeleton while loading", () => {
    const html = render(<SectionCard title="Speaking" state={{ status: "loading" }} onRetry={vi.fn()} render={() => <p>x</p>} />);
    expect(html).toContain('aria-label="Loading Speaking"');
    expect(html).not.toContain("<p>x</p>");
  });
  it("shows an alert with retry on error", () => {
    const html = render(<SectionCard title="Speaking" state={{ status: "error", message: "boom" }} onRetry={vi.fn()} render={() => <p>x</p>} />);
    expect(html).toContain('role="alert"');
    expect(html).toContain("boom");
    expect(html).toContain("Retry");
  });
  it("renders data when ready", () => {
    const html = render(<SectionCard title="T" state={{ status: "ready", data: 5 }} onRetry={vi.fn()} render={(n) => <p>value {n}</p>} />);
    expect(html).toContain("value 5");
  });
  it("banner: empty prompt, early-data warning, and silence when sufficient", () => {
    expect(render(<DataBanner meta={meta("none")} />)).toContain("Complete your first interview to unlock analytics.");
    const early = render(<DataBanner meta={meta("early", 2)} />);
    expect(early).toContain("Early data");
    expect(early).toContain("More practice is needed for reliable trends");
    expect(render(<DataBanner meta={meta("sufficient", 9)} />)).toBe("");
  });
});

const noReadiness = { available: false, score: null, band: null, coverage: 0, message: "Not enough data", detail: "Complete at least 3 interviews", formula: { technical: 0.35 }, components: [], missing_components: [] };

describe("overview", () => {
  const base = { ...meta("none"), readiness: noReadiness, counts: { interviews: 0, pressure: 0, communication: 0, practice: 0 },
    scores: { technical: null, communication: null, confidence: null, overall: null },
    comparison: { available: false as const, reason: "x" } } satisfies OverviewData;
  it("shows 'Not enough data' and N/A instead of fabricated numbers", () => {
    const html = render(<OverviewSection data={base} />);
    expect(html).toContain("Not enough data");
    expect(html.match(/N\/A/g)?.length).toBe(4);
    expect(html).not.toMatch(/>0</);
  });
  it("shows readiness, band, previous-vs-current and a change label", () => {
    const cmp = { available: true, previous: 68, current: 81, change: 13, label: "Significant improvement" as const, previous_samples: 3, current_samples: 3, higher_is_better: true };
    const html = render(<OverviewSection data={{
      ...base, readiness: { ...noReadiness, available: true, score: 77, band: "Developing well", coverage: 0.7, message: null,
        components: [{ label: "Technical", score: 81, samples: 4, weight: 0.35 }] },
      scores: { technical: 81, communication: 74, confidence: null, overall: 78 },
      comparison: { available: true, technical: cmp, communication: { ...cmp, previous: 61, current: 74 }, overall: cmp, confidence: { ...cmp, available: false, previous: null, current: null, change: null, label: null } },
    }} />);
    expect(html).toContain("77");
    expect(html).toContain("Developing well");
    expect(html).toContain("Previous 68 → 81");
    expect(html).toContain("+13 · Significant improvement");
  });
});

describe("trends", () => {
  const trends = (points: [string, number][]): TrendsData => {
    const mk = (label: string) => ({ label, higher_is_better: true, direction: "improving" as const, points: points.map(([period, value]) => ({ period, value, samples: 1 })) });
    const empty = { label: "e", higher_is_better: true, direction: "insufficient_data" as const, points: [] };
    return { ...meta("sufficient", 9), granularity: "day", series: { technical: mk("Technical"), communication: mk("Communication"), confidence: empty, overall: mk("Interview overall"), structure: empty, clarity: empty, filler_rate: empty, speaking_speed: empty } };
  };
  it("renders the chart container with an accessible label and trend legend", () => {
    const html = render(<TrendsSection data={trends([["2026-10-01", 60], ["2026-10-03", 70]])} />);
    expect(html).toContain('aria-label="Performance trend chart by day"');
    expect(html).toContain("Technical");
    expect(html).toContain("Improving");
    expect(html).toContain('role="tablist"');
  });
  it("explains missing or single-period data instead of drawing an empty chart", () => {
    expect(render(<TrendsSection data={trends([])} />)).toContain("No data for these metrics in this range yet.");
    expect(render(<TrendsSection data={trends([["2026-10-01", 60]])} />)).toContain("Only one time period has data");
  });
});

describe("breakdowns", () => {
  it("shows only existing modes and an empty state otherwise", () => {
    expect(render(<ModesSection modes={[]} />)).toContain("No completed interviews");
    const html = render(<ModesSection modes={[{ mode: "hr", label: "HR", sessions: 1, overall_score: 66, technical_score: 60, communication_score: 70, band: "developing", reliable: false }]} />);
    expect(html).toContain("HR interview");
    expect(html).toContain("(early)");
    expect(html).not.toContain("SOC");
  });
  it("domains: percentages only for rated domains; sparse ones listed without a score", () => {
    const data: DomainsData = { ...meta("sufficient", 9), modes: [], strongest: [], weakest: [],
      domains: [{ domain: "Networking", score: 84, band: "strong", questions: 10 }],
      insufficient_data: [{ domain: "Digital Forensics", score: null, band: null, questions: 2 }] };
    const html = render(<DomainsSection data={data} />);
    expect(html).toContain("Networking");
    expect(html).toContain("84%");
    expect(html).toContain("Digital Forensics (2 q)");
    expect(html).not.toContain("Digital Forensics</span>");
  });
});

describe("communication / speaking / pressure / insights", () => {
  it("speaking shows an empty state without voice data and N/A for unmeasured metrics", () => {
    const off: SpeakingData = { ...meta("early", 2), available: false, spoken_answers: 0, message: "No voice answers yet.", metrics: null, not_tracked: [] };
    expect(render(<SpeakingSection data={off} />)).toContain("No voice answers yet.");
    const on: SpeakingData = { ...off, available: true, spoken_answers: 4, message: null, not_tracked: ["self_corrections"],
      metrics: { spoken_answers: 4, words_per_minute: 128, filler_per_100_words: 2.5, pauses_per_minute: null, long_pauses: null, average_pause_seconds: null, average_answer_seconds: 31 } };
    const html = render(<SpeakingSection data={on} />);
    expect(html).toContain("128");
    expect(html).toContain("N/A");
    expect(html).toContain("self-corrections");
  });
  it("communication handles empty data, and weaknesses require evidence", () => {
    const empty: CommunicationData = { ...meta("none"), dimensions: [], samples: { answers: 0, communication_sessions: 0 }, structure: { by_kind: [], note: "" }, length: { available: false, answers: 0 }, weaknesses: [] };
    expect(render(<CommunicationSection data={empty} />)).toContain("No evaluated answers");
    expect(render(<WeaknessList items={[]} />)).toContain("needs repeated evidence");
    const html = render(<WeaknessList items={[{ id: "filler_words", label: "High filler-word usage", samples: 6, occurrences: 5, rate: 0.83, severity: "high", evidence: "5 of 6 spoken answers" }]} />);
    expect(html).toContain("High filler-word usage");
    expect(html).toContain("5 of 6 spoken answers");
  });
  it("pressure: empty state, and a normal-vs-pressure table with accessible caption", () => {
    const none: PressureData = { ...meta("none"), available: false, message: "No pressure sessions yet.", normal: null, pressure: null, differences: {}, insights: [], pressure_handling_score: null };
    expect(render(<PressureSection data={none} />)).toContain("No pressure sessions yet.");
    const side = { sessions: 2, technical: 82, communication: 78, confidence: null, words_per_minute: null, filler_per_100_words: null };
    const html = render(<PressureSection data={{ ...none, available: true, message: null, comparison_available: true, normal: side, pressure: { ...side, technical: 80, communication: 62 }, differences: { technical: -2, communication: -16 }, insights: ["Your technical performance stays stable under pressure, but communication drops noticeably."], pressure_handling_score: 60 }} />);
    expect(html).toContain("<caption");
    expect(html).toContain("-16");
    expect(html).toContain("stays stable under pressure");
  });
  it("insights: empty state, evidence and routed next actions", () => {
    const empty: InsightsData = { ...meta("none"), insights: [], strengths: [], weaknesses: [], next_actions: [], recommendations: [], ai_summary: null };
    expect(render(<InsightsSection data={empty} />)).toContain("Keep practising");
    const html = render(<InsightsSection data={{ ...empty, insights: [{ kind: "domain", text: "Linux is your weakest domain (55%).", evidence: "6 scored questions" }],
      next_actions: [{ weakness: "Weak Linux reasoning", action: "Practise Linux questions.", route: "/cybersecurity", evidence: "55%" }] }} />);
    expect(html).toContain("Evidence: 6 scored questions");
    expect(html).toContain('href="/cybersecurity"');
  });
});
