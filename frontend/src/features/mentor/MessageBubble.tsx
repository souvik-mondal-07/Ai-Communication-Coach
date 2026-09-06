import { useState } from "react";
import { Check, Copy, ShieldHalf, UserRound } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { cn } from "@/lib/utils";
import type { ChatMessage } from "@/types/chat";

interface MessageBubbleProps {
  message: ChatMessage;
}

function CodeBlock({ className, children }: { className?: string; children?: React.ReactNode }) {
  const [copied, setCopied] = useState(false);
  const codeText = String(children ?? "").replace(/\n$/, "");
  const language = /language-(\w+)/.exec(className ?? "")?.[1];

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(codeText);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // Clipboard access can fail (e.g. insecure context) — fail silently.
    }
  }

  return (
    <div className="group relative my-2 overflow-hidden rounded-[var(--radius-panel)] border border-border bg-base">
      <div className="flex items-center justify-between border-b border-border px-3 py-1.5">
        <span className="text-[11px] text-text-muted">{language ?? "code"}</span>
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

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user";

  return (
    <div className={cn("flex gap-3", isUser && "flex-row-reverse")}>
      <div
        className={cn(
          "flex h-8 w-8 shrink-0 items-center justify-center rounded-[var(--radius-panel)]",
          isUser ? "bg-surface-raised text-text-secondary" : "bg-signal/15 text-signal"
        )}
        aria-hidden="true"
      >
        {isUser ? <UserRound size={16} /> : <ShieldHalf size={16} />}
      </div>

      <div className={cn("flex max-w-[85%] flex-col gap-1", isUser && "items-end")}>
        <div
          className={cn(
            "rounded-[var(--radius-panel)] px-3.5 py-2.5 text-sm leading-relaxed",
            isUser
              ? "bg-signal/10 text-text-primary"
              : "border border-border bg-surface text-text-primary"
          )}
        >
          {isUser ? (
            <p className="whitespace-pre-wrap">{message.content}</p>
          ) : (
            <div className="prose-mentor">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                // No rehype-raw plugin is used, so any raw HTML in the AI's
                // response is never parsed/rendered — only Markdown syntax is.
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
                  a: ({ href, children }) => (
                    <a
                      href={href}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-link hover:underline"
                    >
                      {children}
                    </a>
                  ),
                  ul: ({ children }) => (
                    <ul className="my-1.5 list-disc space-y-1 pl-5">{children}</ul>
                  ),
                  ol: ({ children }) => (
                    <ol className="my-1.5 list-decimal space-y-1 pl-5">{children}</ol>
                  ),
                  p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
                  table: ({ children }) => (
                    <div className="my-2 overflow-x-auto">
                      <table className="w-full border-collapse text-xs">{children}</table>
                    </div>
                  ),
                  th: ({ children }) => (
                    <th className="border border-border bg-surface-raised px-2 py-1 text-left">
                      {children}
                    </th>
                  ),
                  td: ({ children }) => (
                    <td className="border border-border px-2 py-1">{children}</td>
                  ),
                }}
              >
                {message.content}
              </ReactMarkdown>
            </div>
          )}
        </div>
        <span className="px-1 text-[11px] text-text-muted">
          {new Date(message.createdAt).toLocaleTimeString(undefined, {
            hour: "2-digit",
            minute: "2-digit",
          })}
        </span>
      </div>
    </div>
  );
}
