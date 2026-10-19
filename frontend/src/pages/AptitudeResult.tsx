import { useEffect } from "react";
import { Link, useParams } from "react-router-dom";
import { Calculator } from "lucide-react";
import { buttonVariants } from "@/components/ui/button-variants";
import { ErrorState } from "@/components/ui/empty-state";
import { PageHeader } from "@/components/ui/page-header";
import { Skeleton } from "@/components/ui/skeleton";
import { APP_FALLBACK_TITLE } from "@/components/common/navigation";
import { ResultView } from "@/features/aptitude/ResultView";
import { useAptitudeStore } from "@/store/aptitudeStore";

export default function AptitudeResult() {
  const { sessionId = "" } = useParams();
  const { result, resultStatus, resultError, loadResult } = useAptitudeStore();

  useEffect(() => {
    document.title = `Aptitude result · ${APP_FALLBACK_TITLE}`;
    if (useAptitudeStore.getState().result?.session_id !== sessionId) void loadResult(sessionId);
  }, [sessionId, loadResult]);

  const ready = result && result.session_id === sessionId;
  return (
    <div className="space-y-6">
      <PageHeader icon={Calculator} title="Aptitude result"
        actions={<><Link to="/aptitude" className={buttonVariants({ variant: "primary", size: "sm" })}>Practice again</Link><Link to="/history?type=aptitude" className={buttonVariants({ variant: "secondary", size: "sm" })}>History</Link></>} />
      {resultStatus === "error" && !ready && <ErrorState message={resultError ?? "Unable to load this result."} onRetry={() => void loadResult(sessionId)} />}
      {!ready && resultStatus !== "error" && <div role="status" aria-label="Loading your result" className="space-y-3"><Skeleton className="h-24 w-full" /><Skeleton className="h-48 w-full" /></div>}
      {ready && <ResultView result={result} />}
    </div>
  );
}
