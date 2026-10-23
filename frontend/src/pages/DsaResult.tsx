import { useEffect } from "react";
import { Link, useParams } from "react-router-dom";
import { Binary } from "lucide-react";
import { buttonVariants } from "@/components/ui/button-variants";
import { ErrorState } from "@/components/ui/empty-state";
import { PageHeader } from "@/components/ui/page-header";
import { Skeleton } from "@/components/ui/skeleton";
import { APP_FALLBACK_TITLE } from "@/components/common/navigation";
import { ResultView } from "@/features/dsa/ResultView";
import { useDsaStore } from "@/store/dsaStore";

export default function DsaResult() {
  const { sessionId = "" } = useParams();
  const { result, resultStatus, resultError, loadResult, assessCode } = useDsaStore();

  useEffect(() => {
    document.title = `DSA result · ${APP_FALLBACK_TITLE}`;
    if (useDsaStore.getState().result?.session_id !== sessionId) void loadResult(sessionId);
  }, [sessionId, loadResult]);

  const ready = result && result.session_id === sessionId;
  return (
    <div className="space-y-6">
      <PageHeader icon={Binary} title="DSA result"
        actions={<><Link to="/dsa" className={buttonVariants({ variant: "primary", size: "sm" })}>Practice again</Link><Link to="/history?type=dsa" className={buttonVariants({ variant: "secondary", size: "sm" })}>History</Link></>} />
      {resultStatus === "error" && !ready && <ErrorState message={resultError ?? "Unable to load this result."} onRetry={() => void loadResult(sessionId)} />}
      {resultStatus === "error" && ready && resultError && <p role="alert" className="text-sm text-danger">{resultError}</p>}
      {!ready && resultStatus !== "error" && <div role="status" aria-label="Loading your result" className="space-y-3"><Skeleton className="h-24 w-full" /><Skeleton className="h-48 w-full" /></div>}
      {ready && <ResultView result={result} onAssess={(qid, v) => void assessCode(qid, v)} />}
    </div>
  );
}
