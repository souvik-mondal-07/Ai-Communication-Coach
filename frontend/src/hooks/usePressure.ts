import { useEffect, useRef, useState } from "react";
import { parseServerDate, useElapsedSeconds } from "@/hooks/useInterview";
import { usePressureStore } from "@/store/pressureStore";

export { parseServerDate };

/**
 * Loads one pressure session and exposes its state, actions, and timing.
 *
 * Unlike the interview simulator, pressure sessions can carry a real time
 * limit per question — `secondsRemaining` counts down from the current
 * prompt's `time_limit_seconds` (null when the level has no time limit, e.g.
 * Level 1). The frontend timer is a UI convenience only: the backend
 * independently measures how long each answer actually took (see
 * `pressure_service.py`), so nothing here needs to be tamper-proof.
 */
export function usePressure(sessionId: string | undefined) {
  const store = usePressureStore();
  const { loadSession, reset, session } = store;

  useEffect(() => {
    if (sessionId) void loadSession(sessionId);
    return () => reset();
  }, [sessionId, loadSession, reset]);

  const elapsedSeconds = useElapsedSeconds(session?.started_at, session?.status === "in_progress");

  const limit = session?.current_prompt?.time_limit_seconds ?? null;
  const promptKey = session?.current_prompt
    ? `${session.current_prompt.question_number}-${session.current_prompt.follow_up_kind ?? "main"}`
    : null;

  const [promptStartedAt, setPromptStartedAt] = useState<number | null>(() => (promptKey ? Date.now() : null));
  const lastPromptKey = useRef(promptKey);
  if (lastPromptKey.current !== promptKey) {
    lastPromptKey.current = promptKey;
    setPromptStartedAt(() => (promptKey ? Date.now() : null));
  }

  const promptElapsed = useCountdownTick(promptStartedAt, session?.status === "in_progress" && limit !== null);
  const secondsRemaining = limit === null ? null : Math.max(0, limit - promptElapsed);

  return { ...store, elapsedSeconds, secondsRemaining, timeLimitSeconds: limit, promptElapsedSeconds: promptElapsed };
}

/** Whole seconds since `startedAt` (a local Date.now() timestamp), ticking once a second while `running`. */
function useCountdownTick(startedAt: number | null, running: boolean): number {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (!running || startedAt === null) return;
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, [startedAt, running]);
  return startedAt === null ? 0 : Math.max(0, Math.floor((now - startedAt) / 1000));
}
