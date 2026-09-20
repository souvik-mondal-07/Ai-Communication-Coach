import { useState } from "react";
import { Button } from "@/components/ui/button";
import type { TranscribeResult } from "@/features/voice/voiceTypes";

interface TranscriptPreviewProps {
  transcript: TranscribeResult;
  /** Called with the final text and whether the user changed the transcript. */
  onSend: (text: string, edited: boolean) => void | Promise<void>;
  onDiscard: () => void;
  isSending?: boolean;
}

/**
 * Shows what was heard and lets the user edit, send, or discard it. Nothing
 * is sent to the AI until the user presses Send.
 */
export function TranscriptPreview({ transcript, onSend, onDiscard, isSending }: TranscriptPreviewProps) {
  const [text, setText] = useState(transcript.text);
  const [isEditing, setIsEditing] = useState(false);

  const trimmed = text.trim();
  const edited = trimmed !== transcript.text.trim();

  return (
    <div className="space-y-3 rounded-[var(--radius-panel)] border border-border bg-surface-raised p-3">
      <p className="text-xs font-medium text-text-muted">Transcript:</p>

      {isEditing ? (
        <>
          <label htmlFor="transcript-edit" className="sr-only">
            Edit transcript
          </label>
          <textarea
            id="transcript-edit"
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={4}
            disabled={isSending}
            className="w-full resize-y rounded-[var(--radius-panel)] border border-border bg-surface px-3 py-2 text-sm text-text-primary"
          />
        </>
      ) : (
        <p className="whitespace-pre-wrap text-sm leading-relaxed text-text-primary">“{text}”</p>
      )}

      <div className="flex flex-wrap items-center gap-2">
        <Button
          variant="secondary"
          size="sm"
          onClick={() => setIsEditing((value) => !value)}
          disabled={isSending}
        >
          {isEditing ? "Done" : "Edit"}
        </Button>
        <Button
          size="sm"
          onClick={() => void onSend(trimmed, edited)}
          disabled={isSending || trimmed.length === 0}
        >
          {isSending ? "Sending..." : "Send"}
        </Button>
        <Button variant="ghost" size="sm" onClick={onDiscard} disabled={isSending}>
          Discard
        </Button>
      </div>
    </div>
  );
}
