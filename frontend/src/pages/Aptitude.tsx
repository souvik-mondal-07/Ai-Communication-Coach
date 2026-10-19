import { useEffect, useMemo } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Calculator } from "lucide-react";
import { EmptyState, ErrorState } from "@/components/ui/empty-state";
import { PageHeader } from "@/components/ui/page-header";
import { Skeleton } from "@/components/ui/skeleton";
import { APP_FALLBACK_TITLE } from "@/components/common/navigation";
import { MODE_BY_ID, defaultForm } from "@/features/aptitude/aptitudeMeta";
import { PracticeSetup } from "@/features/aptitude/PracticeSetup";
import { ProgressPanel } from "@/features/aptitude/ProgressPanel";
import { SyllabusBrowser } from "@/features/aptitude/SyllabusBrowser";
import { cn } from "@/lib/utils";
import { useAptitudeStore } from "@/store/aptitudeStore";
import type { AptitudeMode } from "@/types/aptitude";

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

/** General Aptitude & Logical Reasoning: practice setup, the syllabus browser and personal progress. */
export default function Aptitude() {
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const tab: Tab = (TABS.find((t) => t.id === params.get("tab"))?.id ?? "practice") as Tab;
  const s = useAptitudeStore();

  useEffect(() => {
    document.title = `Aptitude Practice · ${APP_FALLBACK_TITLE}`;
    if (s.syllabusStatus === "idle") void s.loadSyllabus();
    void s.loadProgress();
    // Load once on entry; the store functions are stable.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const initial = useMemo(() => {
    const m = params.get("mode");
    const mode = (m && m in MODE_BY_ID ? m : "topic") as AptitudeMode;
    const form = defaultForm(mode);
    const sub = params.get("subtopic");
    const topic = params.get("topic");
    return { ...form, subtopicIds: sub ? [sub] : [], topicIds: topic ? [topic] : [] };
  }, [params]);

  const setTab = (next: Tab) => { const p = new URLSearchParams(params); p.set("tab", next); setParams(p, { replace: true }); };

  async function start(request: Parameters<typeof s.startSession>[0]) {
    const id = await s.startSession(request);
    if (id) navigate(`/aptitude/session/${id}`);
  }

  const hasWeak = (s.recommendations?.weak_topics.length ?? 0) > 0;

  return (
    <div className="space-y-6">
      <PageHeader icon={Calculator} title="Aptitude Practice"
        description="Quantitative aptitude, logical reasoning and data interpretation for campus placements and screening rounds. Every question is checked against an independent calculation before it is served." />

      <div role="tablist" aria-label="Aptitude sections" className="flex gap-1 border-b border-border">
        {TABS.map((t) => (
          <button key={t.id} id={`apt-tab-${t.id}`} role="tab" type="button" aria-selected={tab === t.id} aria-controls={`apt-panel-${t.id}`} tabIndex={tab === t.id ? 0 : -1}
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

      <div role="tabpanel" id={`apt-panel-${tab}`} aria-labelledby={`apt-tab-${tab}`} tabIndex={0}>
        {tab === "practice" && (
          s.syllabusStatus === "error" ? <ErrorState message={s.syllabusError ?? "Unable to load the syllabus."} onRetry={() => void s.loadSyllabus()} />
          : s.syllabusStatus !== "ready" ? <LoadingBlock label="Loading practice options" />
          : s.syllabus && s.syllabus.totals.questions === 0 ? <EmptyState title="No questions are available yet" description="The question bank is empty. Ask an administrator to check the server's startup log." />
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
