import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ChevronLeft, ChevronRight, Flag } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ErrorState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { APP_FALLBACK_TITLE } from "@/components/common/navigation";
import { ExamTimer } from "@/features/aptitude/ExamTimer";
import { CodingPanel } from "@/features/dsa/CodingPanel";
import { MODE_LABELS, sessionCounts } from "@/features/dsa/dsaMeta";
import { QuestionCard } from "@/features/dsa/QuestionCard";
import { QuestionNavigator } from "@/features/dsa/QuestionNavigator";
import { useDsaStore } from "@/store/dsaStore";

const isTyping = (t: EventTarget | null) => t instanceof HTMLElement && (["INPUT", "TEXTAREA", "SELECT"].includes(t.tagName) || t.isContentEditable);

/**
 * The question runner. No entrance animation: nothing moves while you read or the clock runs. Every answer is saved as it
 * is given, so a refresh resumes here with the server's remaining time. Multiple-choice questions use the keyboard
 * shortcuts below; coding questions use a plain text area (shortcuts are off while typing).
 */
export default function DsaSession() {
  const { sessionId = "" } = useParams();
  const navigate = useNavigate();
  const s = useDsaStore();
  const [confirming, setConfirming] = useState(false);
  const confirmRef = useRef<HTMLButtonElement>(null);
  const { session, currentIndex } = s;

  useEffect(() => {
    document.title = `DSA practice session · ${APP_FALLBACK_TITLE}`;
    if (s.session?.session_id !== sessionId || s.sessionStatus === "idle") void s.loadSession(sessionId);
    // Only when the id changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId]);

  useEffect(() => {
    if (s.ended && session?.session_id === sessionId) navigate(`/dsa/result/${sessionId}`, { replace: true });
  }, [s.ended, session?.session_id, sessionId, navigate]);

  const submit = useCallback(async () => {
    const result = await useDsaStore.getState().submit();
    if (result) navigate(`/dsa/result/${result.session_id}`, { replace: true });
  }, [navigate]);

  const q = session?.questions[currentIndex];
  const total = session?.questions.length ?? 0;

  useEffect(() => {
    if (!session || session.status !== "in_progress" || confirming) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.defaultPrevented || isTyping(e.target) || e.ctrlKey || e.metaKey || e.altKey) return;
      const cur = useDsaStore.getState();
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
        <Link to="/dsa" className="text-sm text-link underline-offset-2 hover:underline">Back to DSA Interview Practice</Link>
      </div>
    );
  }

  const counts = sessionCounts(session.questions);
  const isLast = currentIndex === total - 1;
  const draft = s.drafts[q.question_id] ?? q.code_answer ?? q.coding?.template ?? "";

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

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_16rem]">
        <Card><CardContent className="space-y-5 py-5">
          {q.interaction === "code" ? (
            <CodingPanel key={q.question_id} question={q} index={currentIndex} total={total} draft={draft} saving={s.savingCode === q.question_id}
              canReveal={session.immediate_feedback} onChange={(c) => s.setDraft(q.question_id, c)} onSave={(o) => void s.saveCode(q.question_id, o)} />
          ) : (
            <QuestionCard key={q.question_id} question={q} index={currentIndex} total={total} onSelect={(i) => void s.selectAnswer(q.question_id, i)} disabled={s.isSubmitting} />
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
          <p className="text-xs text-text-muted">Keyboard: 1–4 or A–D to answer · ← → to move · M to mark for review (shortcuts are off while typing code).</p>
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
