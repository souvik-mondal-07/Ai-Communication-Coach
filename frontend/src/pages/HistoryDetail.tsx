import { useCallback, useEffect, useState } from "react";
import { ArrowLeft } from "lucide-react";
import { Link, Navigate, useParams } from "react-router-dom";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { DetailErrorBoundary } from "@/features/history/DetailErrorBoundary";
import { ActivityDetailBody } from "@/features/history/ActivityDetailBody";
import { formatElapsed, isActivityType, STATUS_LABELS, TYPE_META } from "@/features/history/historyMeta";
import * as historyService from "@/services/historyService";
import { formatDateTime } from "@/utils/formatters";
import type { HistoryDetail as HistoryDetailData } from "@/types/history";
import axios from "axios";

type State =
  | { status: "loading" }
  | { status: "not_found" }
  | { status: "error" }
  | { status: "ready"; data: HistoryDetailData };

export default function HistoryDetail() {
  const { type, id } = useParams<{ type: string; id: string }>();
  const [state, setState] = useState<State>({ status: "loading" });
  const [reloadKey, setReloadKey] = useState(0);
  const valid = isActivityType(type) && !!id;

  useEffect(() => {
    if (!isActivityType(type) || !id) return;
    const controller = new AbortController();
    setState({ status: "loading" });
    historyService
      .getActivity(type, id, controller.signal)
      .then((data) => setState({ status: "ready", data }))
      .catch((err) => {
        if (controller.signal.aborted) return;
        // Someone else's id and a missing id look identical on purpose.
        setState(axios.isAxiosError(err) && err.response?.status === 404 ? { status: "not_found" } : { status: "error" });
      });
    return () => controller.abort();
  }, [type, id, reloadKey]);

  const retry = useCallback(() => setReloadKey((k) => k + 1), []);

  if (!valid) return <Navigate to="/history" replace />;

  const back = (
    <Link to="/history" className="inline-flex items-center gap-1.5 text-sm text-text-secondary hover:text-text-primary">
      <ArrowLeft size={15} aria-hidden="true" /> Back to history
    </Link>
  );

  if (state.status === "loading") {
    return (
      <div className="mx-auto w-full max-w-4xl space-y-4">
        {back}
        <p role="status" className="text-sm text-text-muted">
          Loading activity...
        </p>
      </div>
    );
  }

  if (state.status !== "ready") {
    return (
      <div className="mx-auto w-full max-w-4xl space-y-4">
        {back}
        <Card>
          <CardContent className="space-y-3 py-8 text-center" role="alert">
            <p className="text-sm font-medium text-text-primary">
              {state.status === "not_found" ? "This activity couldn't be found." : "Unable to load this activity."}
            </p>
            {state.status === "error" && (
              <>
                <p className="text-sm text-text-muted">Please try again.</p>
                <Button variant="secondary" onClick={retry}>
                  Retry
                </Button>
              </>
            )}
          </CardContent>
        </Card>
      </div>
    );
  }

  const { activity, detail } = state.data;
  const meta = TYPE_META[activity.type];
  const facts = [
    formatDateTime(activity.created_at),
    activity.duration_seconds != null ? formatElapsed(activity.duration_seconds) : null,
    activity.score != null ? `Score: ${activity.score}` : null,
    STATUS_LABELS[activity.status],
  ].filter(Boolean);

  return (
    <div className="mx-auto w-full max-w-4xl space-y-5">
      {back}

      <header className="space-y-1">
        <p className="text-[11px] font-medium uppercase tracking-wide text-text-muted">{activity.type_label}</p>
        <h1 className="font-display text-xl font-semibold text-text-primary">{activity.title}</h1>
        {activity.description && <p className="text-sm text-text-secondary">{activity.description}</p>}
        <p className="text-xs text-text-muted">{facts.join(" · ")}</p>
        {activity.status === "in_progress" && (
          <div className="pt-2">
            <Link
              to={`${meta.sessionPath}/${activity.id}`}
              className="inline-flex h-9 items-center rounded-[var(--radius-panel)] bg-signal px-4 text-sm font-medium text-[#08120f] hover:bg-signal/90"
            >
              Continue this session
            </Link>
          </div>
        )}
      </header>

      {/* keyed so opening another activity starts with a fresh boundary */}
      <DetailErrorBoundary key={`${activity.type}-${activity.id}`}>
        <ActivityDetailBody type={activity.type} detail={detail} />
      </DetailErrorBoundary>
    </div>
  );
}
