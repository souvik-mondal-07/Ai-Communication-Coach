import { useEffect, useState } from "react";
import { useInterviewStore } from "@/store/interviewStore";

/**
 * The backend sends naive UTC timestamps ("2026-09-21T10:00:00", no zone).
 * JavaScript would read those as *local* time, so treat a missing zone as UTC.
 */
export function parseServerDate(iso: string): number {
  const hasZone = /(?:[zZ]|[+-]\d{2}:?\d{2})$/.test(iso);
  return new Date(hasZone ? iso : `${iso}Z`).getTime();
}

/** Whole seconds since `startedAt`, ticking once a second while `running`. */
export function useElapsedSeconds(startedAt: string | undefined, running: boolean): number {
  // The tick only stores "now"; elapsed time is derived from it during render, so
  // it is correct the moment a session loads (e.g. after a page refresh).
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    if (!running || !startedAt) return;
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, [startedAt, running]);

  return startedAt ? Math.max(0, Math.floor((now - parseServerDate(startedAt)) / 1000)) : 0;
}

/**
 * Loads one interview and exposes its state and actions plus the elapsed time.
 * Time is informational only — there is no time pressure in this step.
 */
export function useInterview(sessionId: string | undefined) {
  const store = useInterviewStore();
  const { loadSession, reset } = store;

  useEffect(() => {
    if (sessionId) void loadSession(sessionId);
    return () => reset();
  }, [sessionId, loadSession, reset]);

  const elapsedSeconds = useElapsedSeconds(store.session?.started_at, store.session?.status === "in_progress");
  return { ...store, elapsedSeconds };
}
