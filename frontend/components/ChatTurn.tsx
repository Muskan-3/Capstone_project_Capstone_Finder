"use client";

import Link from "next/link";
import { CompassMark } from "./CompassMark";
import { RecommendationCard } from "./RecommendationCard";
import type { ChatMessage } from "@/lib/types";

function AssistantAvatar() {
  return (
    <span
      className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-white shadow-sm"
      style={{ background: "linear-gradient(135deg, var(--brass), var(--deep-teal))" }}
      aria-hidden
    >
      <CompassMark size={16} />
    </span>
  );
}

function TypingDots() {
  return (
    <span className="flex items-center gap-1" aria-hidden>
      <span className="bounce-dot h-1.5 w-1.5 rounded-full" style={{ background: "var(--brass)", animationDelay: "0ms" }} />
      <span className="bounce-dot h-1.5 w-1.5 rounded-full" style={{ background: "var(--brass)", animationDelay: "150ms" }} />
      <span className="bounce-dot h-1.5 w-1.5 rounded-full" style={{ background: "var(--brass)", animationDelay: "300ms" }} />
    </span>
  );
}

const modeTone: Record<string, string> = {
  routed: "border-l-brass",
  low_confidence: "border-l-deep-teal",
  no_signal: "border-l-charcoal-text/30",
};

export function ChatTurn({ message }: { message: ChatMessage }) {
  if (message.role === "user") {
    return (
      <div className="chat-turn-in flex justify-end">
        <div
          className="max-w-[85%] whitespace-pre-wrap rounded-2xl rounded-tr-sm px-4 py-2.5 text-sm text-white shadow-sm sm:max-w-[70%]"
          style={{ background: "linear-gradient(135deg, var(--brass), var(--deep-teal))" }}
        >
          {message.text}
        </div>
      </div>
    );
  }

  const result = message.result;

  return (
    <div className="chat-turn-in flex gap-3">
      <AssistantAvatar />
      <div className="min-w-0 flex-1">
        {message.pending ? (
          <div className="flex items-center gap-2.5 rounded-2xl rounded-tl-sm border border-hairline bg-parchment-raised px-4 py-3 text-sm text-charcoal-text/60">
            <TypingDots />
            Charting a bearing…
          </div>
        ) : message.error ? (
          <div className="rounded-2xl rounded-tl-sm border border-hairline bg-parchment-raised px-4 py-3 text-sm">
            <p className="text-deep-teal">{message.text}</p>
          </div>
        ) : (
          <div className="space-y-3">
            {message.text && result && (
              <ModeBanner mode={result.mode} text={message.text} detail={message.detail} />
            )}
            {message.text && !result && (
              <div className="max-w-[85%] rounded-2xl rounded-tl-sm border border-hairline bg-parchment-raised px-4 py-2.5 text-sm text-charcoal-text/85">
                {message.text}
              </div>
            )}

            {result && result.recommendations.length === 0 && result.mode !== "routed" && (
              <div className="chart-card max-w-[85%] p-4 text-sm text-charcoal-text/70">
                Nothing to chart from that yet.{" "}
                <Link href="/login" className="link-teal">
                  Add a few more concrete skills or interests
                </Link>{" "}
                and ask again.
              </div>
            )}

            {result && result.recommendations.length > 0 && (
              <div className="space-y-4">
                {result.recommendations.map((rec) => (
                  <RecommendationCard
                    key={`${message.id}-${rec.project_id}`}
                    rec={rec}
                    primary={rec.rank === 1 && result.mode === "routed"}
                    settle
                  />
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export function ModeBanner({ mode, text, detail }: { mode: string; text: string; detail?: string }) {
  return (
    <div className={`chart-card border-l-2 ${modeTone[mode] ?? "border-l-hairline"} max-w-[85%] p-3 text-xs text-charcoal-text/70`}>
      <p>{text}</p>
      {detail && detail !== text && (
        <details className="mt-1.5">
          <summary className="cursor-pointer text-charcoal-text/50 hover:text-brass">
            Routing details
          </summary>
          <p className="mt-1 text-charcoal-text/60">{detail}</p>
        </details>
      )}
    </div>
  );
}
