import { useEffect, useMemo } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Binary } from "lucide-react";
import { EmptyState, ErrorState } from "@/components/ui/empty-state";
import { PageHeader } from "@/components/ui/page-header";
import { Skeleton } from "@/components/ui/skeleton";
import { APP_FALLBACK_TITLE } from "@/components/common/navigation";
import { defaultForm, MODE_BY_ID } from "@/features/dsa/dsaMeta";
import { PracticeSetup } from "@/features/dsa/PracticeSetup";
import { ProgressPanel } from "@/features/dsa/ProgressPanel";
import { SyllabusBrowser } from "@/features/dsa/SyllabusBrowser";
import { cn } from "@/lib/utils";
import { useDsaStore } from "@/store/dsaStore";
import type { DsaMode } from "@/types/dsa";

type Tab = "practice" | "syllabus" | "progress";
const TABS: { id: Tab; label: string }[] = [
  { id: "practice", label: "Practice" },
  { id: "syllabus", label: "Syllabus" },
  { id: "progress", label: "My progress" },
];

function LoadingBlock({ label }: { label: string }) {
  return (
    <div role="status" aria-label={label} className="space-y-3">
      <Skeleton className="h-24 w-full" /><Skeleton className="h-24 w-full" /><Skeleton className="h-24 w-full" />
    </div>
  );
}

/** DSA Interview Practice: practice setup (seven modes), the syllabus browser with real coverage, and personal progress. */
export default function Dsa() {
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const tab: Tab = (TABS.find((t) => t.id === params.get("tab"))?.id ?? "practice") as Tab;
  const s = useDsaStore();

  useEffect(() => {
    document.title = `DSA Interview Practice · ${APP_FALLBACK_TITLE}`;
    if (s.syllabusStatus === "idle") void s.loadSyllabus();
    void s.loadProgress();
    // Load once on entry; the store functions are stable.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const initial = useMemo(() => {
    const m = params.get("mode");
    const mode = (m && m in MODE_BY_ID ? m : "topic") as DsaMode;
    const sub = params.get("subtopic");
    const topic = params.get("topic");
    return { ...defaultForm(mode), subtopicIds: sub ? [sub] : [], topicIds: topic ? [topic] : [] };
  }, [params]);

  const setTab = (next: Tab) => { const p = new URLSearchParams(params); p.set("tab", next); setParams(p, { replace: true }); };

  async function start(request: Parameters<typeof s.startSession>[0]) {
    const id = await s.startSession(request);
    if (id) navigate(`/dsa/session/${id}`);
  }

  const hasWeak = (s.recommendations?.weak_topics.length ?? 0) > 0;

  return (
    <div className="space-y-6">
      <PageHeader icon={Binary} title="DSA Interview Practice"
        description="Data structures and algorithms for placement tests and technical interviews: concepts, scenarios, output prediction, tracing, complexity and coding. Every answer key is checked by a reference computation or by running the reference code in our tests." />

      <div role="tablist" aria-label="DSA sections" className="flex gap-1 border-b border-border">
        {TABS.map((t) => (
          <button key={t.id} id={`dsa-tab-${t.id}`} role="tab" type="button" aria-selected={tab === t.id} aria-controls={`dsa-panel-${t.id}`} tabIndex={tab === t.id ? 0 : -1}
            onClick={() => setTab(t.id)}
            onKeyDown={(e) => {
              const i = TABS.findIndex((x) => x.id === tab);
              if (e.key === "ArrowRight") { e.preventDefault(); setTab(TABS[(i + 1) % TABS.length].id); }
              if (e.key === "ArrowLeft") { e.preventDefault(); setTab(TABS[(i + TABS.length - 1) % TABS.length].id); }
            }}
            className={cn("-mb-px border-b-2 px-4 py-2 text-sm font-medium", tab === t.id ? "border-signal text-text-primary" : "border-transparent text-text-secondary hover:text-text-primary")}>
            {t.label}
          </button>
        ))}
      </div>

      <div role="tabpanel" id={`dsa-panel-${tab}`} aria-labelledby={`dsa-tab-${tab}`} tabIndex={0}>
        {tab === "practice" && (
          s.syllabusStatus === "error" ? <ErrorState message={s.syllabusError ?? "Unable to load the syllabus."} onRetry={() => void s.loadSyllabus()} />
          : s.syllabusStatus !== "ready" ? <LoadingBlock label="Loading practice options" />
          : s.syllabus && s.syllabus.totals.questions === 0 ? <EmptyState title="No questions are available yet" description="The DSA question bank is empty. Ask an administrator to check the server's startup log." />
          : <PracticeSetup key={params.toString()} syllabus={s.syllabus} initial={initial} starting={s.isStarting} error={s.startError} hasWeakTopics={hasWeak} onStart={(r) => void start(r)} />
        )}
        {tab === "syllabus" && (
          s.syllabusStatus === "error" ? <ErrorState message={s.syllabusError ?? "Unable to load the syllabus."} onRetry={() => void s.loadSyllabus()} />
          : s.syllabusStatus !== "ready" || !s.syllabus ? <LoadingBlock label="Loading syllabus" />
          : <SyllabusBrowser syllabus={s.syllabus} />
        )}
        {tab === "progress" && (
          s.progressStatus === "error" ? <ErrorState message={s.progressError ?? "Unable to load progress."} onRetry={() => void s.loadProgress()} />
          : s.progressStatus !== "ready" || !s.progress ? <LoadingBlock label="Loading progress" />
          : <ProgressPanel progress={s.progress} recommendations={s.recommendations} />
        )}
      </div>
    </div>
  );
}
