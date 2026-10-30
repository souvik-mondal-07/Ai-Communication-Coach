import { useEffect } from "react";
import { Link, useParams } from "react-router-dom";
import { Code2 } from "lucide-react";
import { buttonVariants } from "@/components/ui/button-variants";
import { ErrorState } from "@/components/ui/empty-state";
import { PageHeader } from "@/components/ui/page-header";
import { Skeleton } from "@/components/ui/skeleton";
import { APP_FALLBACK_TITLE } from "@/components/common/navigation";
import { ResultView } from "@/features/python-practice/ResultView";
import { usePythonPracticeStore } from "@/store/pythonPracticeStore";

export default function PythonPracticeResult() {
  const { sessionId = "" } = useParams();
  const { result, resultStatus, resultError, loadResult } = usePythonPracticeStore();

  useEffect(() => {
    document.title = `Python result · ${APP_FALLBACK_TITLE}`;
    if (usePythonPracticeStore.getState().result?.session_id !== sessionId) void loadResult(sessionId);
  }, [sessionId, loadResult]);

  const ready = result && result.session_id === sessionId;
  return (
    <div className="space-y-6">
      <PageHeader icon={Code2} title="Python result"
        actions={<><Link to="/python-practice" className={buttonVariants({ variant: "primary", size: "sm" })}>Practice again</Link><Link to="/history?type=python_practice" className={buttonVariants({ variant: "secondary", size: "sm" })}>History</Link></>} />
      {resultStatus === "error" && !ready && <ErrorState message={resultError ?? "Unable to load this result."} onRetry={() => void loadResult(sessionId)} />}
      {!ready && resultStatus !== "error" && <div role="status" aria-label="Loading your result" className="space-y-3"><Skeleton className="h-24 w-full" /><Skeleton className="h-48 w-full" /></div>}
      {ready && <ResultView result={result} />}
    </div>
  );
}
