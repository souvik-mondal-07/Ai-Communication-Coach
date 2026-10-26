import { useEffect, useMemo } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Database } from "lucide-react";
import { EmptyState, ErrorState } from "@/components/ui/empty-state";
import { PageHeader } from "@/components/ui/page-header";
import { Skeleton } from "@/components/ui/skeleton";
import { APP_FALLBACK_TITLE } from "@/components/common/navigation";
import { defaultForm, MODE_BY_ID } from "@/features/dbms-sql/dbmsSqlMeta";
import { Playground } from "@/features/dbms-sql/Playground";
import { PracticeSetup } from "@/features/dbms-sql/PracticeSetup";
import { ProgressPanel } from "@/features/dbms-sql/ProgressPanel";
import { SyllabusBrowser } from "@/features/dbms-sql/SyllabusBrowser";
import { cn } from "@/lib/utils";
import { useDbmsSqlStore } from "@/store/dbmsSqlStore";
import type { DbmsMode } from "@/types/dbmsSql";

type Tab = "practice" | "playground" | "syllabus" | "progress";
const TABS: { id: Tab; label: string }[] = [
  { id: "practice", label: "Practice" },
  { id: "playground", label: "SQL playground" },
  { id: "syllabus", label: "Syllabus" },
  { id: "progress", label: "My progress" },
];

function LoadingBlock({ label }: { label: string }) {
  return <div role="status" aria-label={label} className="space-y-3"><Skeleton className="h-24 w-full" /><Skeleton className="h-24 w-full" /><Skeleton className="h-24 w-full" /></div>;
}

/** DBMS & SQL Interview Lab: twelve practice modes, a SQL playground, the syllabus with real coverage, and personal progress. */
export default function DbmsSql() {
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const tab: Tab = (TABS.find((t) => t.id === params.get("tab"))?.id ?? "practice") as Tab;
  const s = useDbmsSqlStore();

  useEffect(() => {
    document.title = `DBMS & SQL Interview Lab · ${APP_FALLBACK_TITLE}`;
    if (s.syllabusStatus === "idle") void s.loadSyllabus();
    void s.loadProgress();
    // Load once on entry; the store functions are stable.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (tab === "playground") void s.loadDataset("practice");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab]);

  const initial = useMemo(() => {
    const m = params.get("mode");
    const mode = (m && m in MODE_BY_ID ? m : "topic") as DbmsMode;
    const topic = params.get("topic");
    const unit = params.get("unit");
    return { ...defaultForm(mode), topicIds: topic ? [topic] : [], unitIds: unit ? [unit] : [] };
  }, [params]);

  const setTab = (next: Tab) => { const p = new URLSearchParams(params); p.set("tab", next); setParams(p, { replace: true }); };

  async function start(request: Parameters<typeof s.startSession>[0]) {
    const id = await s.startSession(request);
    if (id) navigate(`/dbms-sql/session/${id}`);
  }

  const hasWeak = (s.recommendations?.weak_topics.length ?? 0) > 0;

  return (
    <div className="space-y-6">
      <PageHeader icon={Database} title="DBMS & SQL Interview Lab"
        description="Database theory, SQL query writing, output prediction, debugging, normalization, transactions and MongoDB for placement tests and technical interviews. SQL runs in an isolated read-only sandbox and is graded by comparing results; design and transaction answers are computed, not guessed." />

      <div role="tablist" aria-label="DBMS and SQL sections" className="flex flex-wrap gap-1 border-b border-border">
        {TABS.map((t) => (
          <button key={t.id} id={`dbms-tab-${t.id}`} role="tab" type="button" aria-selected={tab === t.id} aria-controls={`dbms-panel-${t.id}`} tabIndex={tab === t.id ? 0 : -1} onClick={() => setTab(t.id)}
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

      <div role="tabpanel" id={`dbms-panel-${tab}`} aria-labelledby={`dbms-tab-${tab}`} tabIndex={0}>
        {tab === "practice" && (
          s.syllabusStatus === "error" ? <ErrorState message={s.syllabusError ?? "Unable to load the syllabus."} onRetry={() => void s.loadSyllabus()} />
          : s.syllabusStatus !== "ready" || !s.syllabus ? <LoadingBlock label="Loading practice options" />
          : s.syllabus.question_total === 0 ? <EmptyState title="No questions are available yet" description="The DBMS & SQL question bank is empty. Ask an administrator to check the server's startup log." />
          : <PracticeSetup key={params.toString()} syllabus={s.syllabus} initial={initial} starting={s.isStarting} error={s.startError} hasWeakTopics={hasWeak} onStart={(r) => void start(r)} />
        )}
        {tab === "playground" && (
          <Playground dataset={s.datasets.practice} datasetStatus={s.datasetStatus} datasetError={s.datasetError} engine={s.syllabus?.sql_engine} result={s.playground} busy={s.playgroundBusy}
            error={s.playgroundError} onRun={(sql) => void s.runPlayground(sql)} onRetryDataset={() => void s.loadDataset("practice")} />
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
