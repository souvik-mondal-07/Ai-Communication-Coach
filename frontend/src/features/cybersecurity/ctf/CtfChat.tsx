import { type KeyboardEvent, useEffect, useRef, useState } from "react";
import { Check, Copy, SendHorizontal, ShieldHalf, UserRound } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { cn } from "@/lib/utils";
import type { CtfChatMessage } from "@/features/cybersecurity/ctf/ctfTypes";

interface CtfChatProps {
  messages: CtfChatMessage[];
  onSend: (message: string) => Promise<void>;
  isSending: boolean;
}

function CodeBlock({ className, children }: { className?: string; children?: React.ReactNode }) {
  const [copied, setCopied] = useState(false);
  const codeText = String(children ?? "").replace(/\n$/, "");

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(codeText);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // Ignore clipboard failures (e.g. insecure context).
    }
  }

  return (
    <div className="my-2 overflow-hidden rounded-[var(--radius-panel)] border border-border bg-base">
      <div className="flex items-center justify-between border-b border-border px-3 py-1.5">
        <span className="text-[11px] text-text-muted">code — never executed automatically</span>
        <button
          type="button"
          onClick={handleCopy}
          className="flex items-center gap-1 rounded px-1.5 py-0.5 text-[11px] text-text-muted hover:bg-surface-raised hover:text-text-primary"
          aria-label="Copy code"
        >
          {copied ? <Check size={12} /> : <Copy size={12} />}
          {copied ? "Copied" : "Copy"}
        </button>
      </div>
      <pre className="overflow-x-auto px-3 py-2.5 text-[13px] leading-relaxed">
        <code className={className}>{codeText}</code>
      </pre>
    </div>
  );
}

function CtfMessageBubble({ message }: { message: CtfChatMessage }) {
  const isUser = message.role === "user";
  return (
    <div className={cn("flex gap-2.5", isUser && "flex-row-reverse")}>
      <div
        className={cn(
          "flex h-7 w-7 shrink-0 items-center justify-center rounded-[var(--radius-panel)]",
          isUser ? "bg-surface-raised text-text-secondary" : "bg-signal/15 text-signal"
        )}
      >
        {isUser ? <UserRound size={14} /> : <ShieldHalf size={14} />}
      </div>
      <div
        className={cn(
          "max-w-[85%] rounded-[var(--radius-panel)] px-3.5 py-2.5 text-sm leading-relaxed",
          isUser ? "bg-signal/10 text-text-primary" : "border border-border bg-surface text-text-primary"
        )}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap">{message.content}</p>
        ) : (
          <div className="prose-mentor">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                code: (props) => {
                  const { className, children } = props;
                  const isBlock = /language-/.test(className ?? "");
                  if (!isBlock) {
                    return (
                      <code className="rounded bg-surface-raised px-1 py-0.5 text-[13px]">
                        {children}
                      </code>
                    );
                  }
                  return <CodeBlock className={className}>{children}</CodeBlock>;
                },
                pre: ({ children }) => <>{children}</>,
                p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
                ul: ({ children }) => <ul className="my-1.5 list-disc space-y-1 pl-5">{children}</ul>,
                ol: ({ children }) => <ol className="my-1.5 list-decimal space-y-1 pl-5">{children}</ol>,
              }}
            >
              {message.content}
            </ReactMarkdown>
          </div>
        )}
      </div>
    </div>
  );
}

export function CtfChat({ messages, onSend, isSending }: CtfChatProps) {
  const [value, setValue] = useState("");
  const scrollAnchorRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollAnchorRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length, isSending]);

  const canSubmit = value.trim().length > 0 && !isSending;

  async function handleSubmit() {
    if (!canSubmit) return;
    const message = value;
    setValue("");
    try {
      await onSend(message);
    } catch {
      // Preserve the text so the user can retry.
      setValue(message);
    }
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void handleSubmit();
    }
  }

  return (
    <div className="flex h-full flex-col">
      <div className="mb-3 flex-1 space-y-4 overflow-y-auto">
        {messages.length === 0 ? (
          <p className="py-6 text-center text-sm text-text-muted">
            Tell the mentor what you've found — it'll ask questions and help you reason through it.
          </p>
        ) : (
          messages.map((message, idx) => <CtfMessageBubble key={idx} message={message} />)
        )}
        {isSending && (
          <div className="flex items-center gap-2.5">
            <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-[var(--radius-panel)] bg-signal/15 text-signal">
              <ShieldHalf size={14} />
            </div>
            <div className="rounded-[var(--radius-panel)] border border-border bg-surface px-3.5 py-2.5 text-sm text-text-muted">
              Mentor is thinking…
            </div>
          </div>
        )}
        <div ref={scrollAnchorRef} />
      </div>

      <div className="flex items-end gap-2 border-t border-border pt-3">
        <label htmlFor="ctf-chat-input" className="sr-only">
          Ask the mentor
        </label>
        <textarea
          id="ctf-chat-input"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isSending}
          rows={2}
          placeholder="Ask Mentor... (Enter to send, Shift+Enter for a new line)"
          className="max-h-40 flex-1 resize-none rounded-[var(--radius-panel)] border border-border bg-surface-raised px-3 py-2 text-sm text-text-primary placeholder:text-text-muted disabled:cursor-not-allowed disabled:opacity-60"
        />
        <button
          type="button"
          onClick={() => void handleSubmit()}
          disabled={!canSubmit}
          aria-label="Send message"
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-[var(--radius-panel)] bg-signal text-[#08120f] transition-colors hover:bg-signal/90 disabled:cursor-not-allowed disabled:opacity-40"
        >
          <SendHorizontal size={16} />
        </button>
      </div>
    </div>
  );
}
