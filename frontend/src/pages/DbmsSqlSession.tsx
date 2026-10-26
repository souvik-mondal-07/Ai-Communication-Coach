import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ChevronLeft, ChevronRight, Flag, Table2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ErrorState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { APP_FALLBACK_TITLE } from "@/components/common/navigation";
import { ExamTimer } from "@/features/aptitude/ExamTimer";
import { MODE_LABELS, sessionCounts } from "@/features/dbms-sql/dbmsSqlMeta";
import { QuestionCard } from "@/features/dbms-sql/QuestionCard";
import { QuestionNavigator } from "@/features/dbms-sql/QuestionNavigator";
import { SchemaViewer } from "@/features/dbms-sql/SchemaViewer";
import { SqlWorkbench } from "@/features/dbms-sql/SqlWorkbench";
import { useDbmsSqlStore } from "@/store/dbmsSqlStore";

const isTyping = (t: EventTarget | null) => t instanceof HTMLElement && (["INPUT", "TEXTAREA", "SELECT"].includes(t.tagName) || t.isContentEditable);

/**
 * The question runner. No entrance animation: nothing moves while you read or the clock runs. Every answer is saved as it is given, so a
 * refresh resumes here with the server's remaining time. Keyboard shortcuts apply to multiple-choice questions and are off while typing.
 */
export default function DbmsSqlSession() {
  const { sessionId = "" } = useParams();
  const navigate = useNavigate();
  const s = useDbmsSqlStore();
  const [confirming, setConfirming] = useState(false);
  const [showSchema, setShowSchema] = useState(false);
  const confirmRef = useRef<HTMLButtonElement>(null);
  const { session, currentIndex } = s;

  useEffect(() => {
    document.title = `DBMS & SQL practice session · ${APP_FALLBACK_TITLE}`;
    if (s.session?.session_id !== sessionId || s.sessionStatus === "idle") void s.loadSession(sessionId);
    // Only when the id changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId]);

  useEffect(() => {
    if (s.ended && session?.session_id === sessionId) navigate(`/dbms-sql/result/${sessionId}`, { replace: true });
  }, [s.ended, session?.session_id, sessionId, navigate]);

  const submit = useCallback(async () => {
    const result = await useDbmsSqlStore.getState().submit();
    if (result) navigate(`/dbms-sql/result/${result.session_id}`, { replace: true });
  }, [navigate]);

  const q = session?.questions[currentIndex];
  const total = session?.questions.length ?? 0;
  const needsTables = Boolean(q && (q.sql || q.dataset_id));

  useEffect(() => {
    if (needsTables) void s.loadDataset(q?.dataset_id ?? "practice");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [needsTables, q?.dataset_id]);

  useEffect(() => {
    if (!session || session.status !== "in_progress" || confirming) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.defaultPrevented || isTyping(e.target) || e.ctrlKey || e.metaKey || e.altKey) return;
      const cur = useDbmsSqlStore.getState();
      const question = cur.session?.questions[cur.currentIndex];
      if (!question) return;
      if (e.key === "ArrowRight") cur.goTo(cur.currentIndex + 1);
      else if (e.key === "ArrowLeft") cur.goTo(cur.currentIndex - 1);
      else if (e.key.toLowerCase() === "m") void cur.toggleMark(question.question_id);
      else if (question.interaction === "mcq" && /^[1-4]$/.test(e.key)) void cur.selectAnswer(question.question_id, Number(e.key) - 1);
      else if (question.interaction === "mcq" && /^[a-dA-D]$/.test(e.key)) void cur.selectAnswer(question.question_id, e.key.toLowerCase().charCodeAt(0) - 97);
      else return;
      e.preventDefault();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [session, confirming]);

  useEffect(() => { if (confirming) confirmRef.current?.focus(); }, [confirming]);

  if (s.sessionStatus === "loading" || s.sessionStatus === "idle") {
    return <div role="status" aria-label="Loading your session" className="space-y-3"><Skeleton className="h-8 w-1/3" /><Skeleton className="h-40 w-full" /><Skeleton className="h-12 w-full" /></div>;
  }
  if (s.sessionStatus === "error" || !session || !q) {
    return (
      <div className="space-y-4">
        <ErrorState message={s.sessionError ?? "This session could not be found."} onRetry={() => void s.loadSession(sessionId)} />
        <Link to="/dbms-sql" className="text-sm text-link underline-offset-2 hover:underline">Back to the DBMS & SQL Interview Lab</Link>
      </div>
    );
  }

  const counts = sessionCounts(session.questions);
  const isLast = currentIndex === total - 1;
  const draft = s.drafts[q.question_id] ?? (q.interaction === "sql" ? q.sql_answer ?? q.sql?.starter ?? "" : q.text_answer ?? "");
  const busy = s.busy[q.question_id];

  return (
    <div className="space-y-4">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="font-display text-lg font-semibold text-text-primary">{MODE_LABELS[session.mode]}</h1>
          <p className="text-xs text-text-muted" aria-live="polite">{counts.answered} of {counts.total} answered{session.requested_count > session.question_count ? ` · only ${session.question_count} of ${session.requested_count} requested questions were available` : ""}</p>
        </div>
        <div className="flex items-center gap-3">
          {session.expires_at && <ExamTimer expiresAt={session.expires_at} clockOffsetMs={s.clockOffsetMs} onExpire={() => void submit()} />}
          <Button variant="secondary" onClick={() => setConfirming(true)} disabled={s.isSubmitting}>Submit</Button>
        </div>
      </header>

      {s.answerError && (
        <div role="alert" className="flex items-center justify-between gap-3 rounded-[var(--radius-panel)] border border-danger/40 bg-danger/10 px-4 py-2 text-sm text-danger">
          <span>{s.answerError}</span>
          <button type="button" className="text-xs underline" onClick={s.clearAnswerError}>Dismiss</button>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_17rem]">
        <Card><CardContent className="space-y-5 py-5">
          {q.interaction === "sql" ? (
            <SqlWorkbench key={q.question_id} question={q} index={currentIndex} total={total} draft={draft} run={s.runs[q.question_id]} check={s.checkResults[q.question_id]} busy={busy}
              canCheck={session.immediate_feedback} onDraft={(v) => s.setDraft(q.question_id, v)} onRun={() => void s.runQuery(q.question_id)} onCheck={() => void s.checkAnswer(q.question_id)}
              onReveal={() => void s.revealSolution(q.question_id)} onHint={() => void s.requestHint(q.question_id)} />
          ) : (
            <QuestionCard key={q.question_id} question={q} index={currentIndex} total={total} draft={draft} busy={Boolean(busy)} checkResult={s.checkResults[q.question_id]} canCheck={session.immediate_feedback}
              disabled={s.isSubmitting} onSelect={(i) => void s.selectAnswer(q.question_id, i)} onDraft={(v) => s.setDraft(q.question_id, v)} onCheck={() => void s.checkAnswer(q.question_id)} onHint={() => void s.requestHint(q.question_id)} />
          )}

          {needsTables && (
            <div className="space-y-2 border-t border-border pt-4">
              <Button type="button" variant="secondary" size="sm" aria-expanded={showSchema} aria-controls="schema-panel" onClick={() => setShowSchema((v) => !v)}><Table2 size={14} aria-hidden="true" /> {showSchema ? "Hide sample tables" : "Show sample tables"}</Button>
              {showSchema && <div id="schema-panel"><SchemaViewer dataset={s.datasets[q.dataset_id ?? "practice"]} status={s.datasetStatus} error={s.datasetError} onRetry={() => void s.loadDataset(q.dataset_id ?? "practice")} /></div>}
            </div>
          )}

          <div className="flex flex-wrap items-center justify-between gap-2 border-t border-border pt-4">
            <div className="flex gap-2">
              <Button variant="secondary" size="sm" onClick={() => s.goTo(currentIndex - 1)} disabled={currentIndex === 0}><ChevronLeft size={14} aria-hidden="true" /> Previous</Button>
              <Button variant="secondary" size="sm" onClick={() => s.goTo(currentIndex + 1)} disabled={isLast}>Next <ChevronRight size={14} aria-hidden="true" /></Button>
            </div>
            <div className="flex gap-2">
              {q.interaction === "mcq" && !q.locked && q.selected_index !== null && <Button variant="ghost" size="sm" onClick={() => void s.selectAnswer(q.question_id, null)}>Clear answer</Button>}
              <Button variant={q.marked_for_review ? "primary" : "secondary"} size="sm" aria-pressed={q.marked_for_review} onClick={() => void s.toggleMark(q.question_id)}>
                <Flag size={14} aria-hidden="true" /> {q.marked_for_review ? "Marked for review" : "Mark for review"}
              </Button>
            </div>
          </div>
          <p className="text-xs text-text-muted">Keyboard: 1–4 or A–D to answer · ← → to move · M to mark for review (shortcuts are off while typing).</p>
        </CardContent></Card>

        <aside aria-label="Progress" className="space-y-3 lg:sticky lg:top-4 lg:self-start">
          <QuestionNavigator questions={session.questions} currentIndex={currentIndex} onGo={s.goTo} />
        </aside>
      </div>

      {confirming && (
        <div role="alertdialog" aria-labelledby="submit-title" aria-describedby="submit-desc" className="rounded-[var(--radius-card)] border border-border-strong bg-surface-raised p-4 shadow-pop">
          <h2 id="submit-title" className="text-sm font-semibold text-text-primary">Submit this {session.exam_mode ? "test" : "session"}?</h2>
          <p id="submit-desc" className="mt-1 text-sm text-text-secondary">
            {counts.unanswered > 0 ? `${counts.unanswered} question${counts.unanswered === 1 ? " is" : "s are"} unanswered. ` : "All questions are answered. "}
            {counts.marked > 0 ? `${counts.marked} marked for review. ` : ""}You cannot change answers after submitting.
          </p>
          <div className="mt-3 flex gap-2">
            <Button ref={confirmRef} onClick={() => void submit()} loading={s.isSubmitting}>Submit now</Button>
            <Button variant="secondary" onClick={() => setConfirming(false)} disabled={s.isSubmitting}>Keep working</Button>
          </div>
        </div>
      )}
    </div>
  );
}
