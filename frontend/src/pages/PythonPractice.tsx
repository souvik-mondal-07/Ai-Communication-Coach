import { useEffect, useMemo } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Code2 } from "lucide-react";
import { EmptyState, ErrorState } from "@/components/ui/empty-state";
import { PageHeader } from "@/components/ui/page-header";
import { Skeleton } from "@/components/ui/skeleton";
import { APP_FALLBACK_TITLE } from "@/components/common/navigation";
import { defaultForm, MODE_BY_ID } from "@/features/python-practice/pythonPracticeMeta";
import { CoveragePanel, HistoryPanel, RunnerBanner } from "@/features/python-practice/Panels";
import { PracticeSetup } from "@/features/python-practice/PracticeSetup";
import { ProgressPanel } from "@/features/python-practice/ProgressPanel";
import { SyllabusBrowser } from "@/features/python-practice/SyllabusBrowser";
import { cn } from "@/lib/utils";
import { usePythonPracticeStore } from "@/store/pythonPracticeStore";
import type { PyMode } from "@/types/pythonPractice";

type Tab = "practice" | "syllabus" | "progress" | "history";
const TABS: { id: Tab; label: string }[] = [
  { id: "practice", label: "Practice" },
  { id: "syllabus", label: "Syllabus & coverage" },
  { id: "progress", label: "My progress" },
  { id: "history", label: "History" },
];

function LoadingBlock({ label }: { label: string }) {
  return <div role="status" aria-label={label} className="space-y-3"><Skeleton className="h-24 w-full" /><Skeleton className="h-24 w-full" /><Skeleton className="h-24 w-full" /></div>;
}

/** Python Interview Lab: fourteen practice modes, a coding workspace, the syllabus with real coverage, personal progress and history. */
export default function PythonPractice() {
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const tab: Tab = (TABS.find((t) => t.id === params.get("tab"))?.id ?? "practice") as Tab;
  const s = usePythonPracticeStore();

  useEffect(() => {
    document.title = `Python Interview Lab · ${APP_FALLBACK_TITLE}`;
    if (s.syllabusStatus === "idle") void s.loadSyllabus();
    void s.loadProgress();
    // Load once on entry; the store functions are stable.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const initial = useMemo(() => {
    const m = params.get("mode");
    const mode = (m && m in MODE_BY_ID ? m : "topic") as PyMode;
    const topic = params.get("topic");
    const unit = params.get("unit");
    return { ...defaultForm(mode), topicIds: topic ? [topic] : [], unitIds: unit ? [unit] : [] };
  }, [params]);

  const setTab = (next: Tab) => { const p = new URLSearchParams(params); p.set("tab", next); setParams(p, { replace: true }); };

  async function start(request: Parameters<typeof s.startSession>[0]) {
    const id = await s.startSession(request);
    if (id) navigate(`/python-practice/session/${id}`);
  }

  const hasWeak = (s.recommendations?.weak_topics.length ?? 0) > 0;

  return (
    <div className="space-y-6">
      <PageHeader icon={Code2} title="Python Interview Lab"
        description="Python concepts, output prediction, tracing, debugging, coding challenges, complexity and cybersecurity automation for placements and technical interviews. Code runs in an isolated runner and is graded by tests on the server; answers are never guessed or self-reported." />

      <div role="tablist" aria-label="Python practice sections" className="flex flex-wrap gap-1 border-b border-border">
        {TABS.map((t) => (
          <button key={t.id} id={`py-tab-${t.id}`} role="tab" type="button" aria-selected={tab === t.id} aria-controls={`py-panel-${t.id}`} tabIndex={tab === t.id ? 0 : -1} onClick={() => setTab(t.id)}
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

      <div role="tabpanel" id={`py-panel-${tab}`} aria-labelledby={`py-tab-${tab}`} tabIndex={0}>
        {tab === "practice" && (
          s.syllabusStatus === "error" ? <ErrorState message={s.syllabusError ?? "Unable to load the syllabus."} onRetry={() => void s.loadSyllabus()} />
          : s.syllabusStatus !== "ready" || !s.syllabus ? <LoadingBlock label="Loading practice options" />
          : s.syllabus.question_total === 0 ? <EmptyState title="No questions are available yet" description="The Python question bank is empty. Ask an administrator to check the server's startup log." />
          : <div className="space-y-4"><RunnerBanner runner={s.syllabus.runner} /><PracticeSetup key={params.toString()} syllabus={s.syllabus} initial={initial} starting={s.isStarting} error={s.startError} hasWeakTopics={hasWeak} onStart={(r) => void start(r)} /></div>
        )}
        {tab === "syllabus" && (
          s.syllabusStatus === "error" ? <ErrorState message={s.syllabusError ?? "Unable to load the syllabus."} onRetry={() => void s.loadSyllabus()} />
          : s.syllabusStatus !== "ready" || !s.syllabus ? <LoadingBlock label="Loading syllabus" />
          : <div className="space-y-6"><SyllabusBrowser syllabus={s.syllabus} /><section aria-labelledby="coverage-h" className="space-y-2"><h2 id="coverage-h" className="font-display text-base font-semibold text-text-primary">Coverage matrix</h2><CoveragePanel /></section></div>
        )}
        {tab === "history" && <HistoryPanel />}
        {tab === "progress" && (
          s.progressStatus === "error" ? <ErrorState message={s.progressError ?? "Unable to load progress."} onRetry={() => void s.loadProgress()} />
          : s.progressStatus !== "ready" || !s.progress ? <LoadingBlock label="Loading progress" />
          : <ProgressPanel progress={s.progress} recommendations={s.recommendations} />
        )}
      </div>
    </div>
  );
}
