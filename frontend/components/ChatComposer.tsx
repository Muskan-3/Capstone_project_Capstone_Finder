"use client";

import { useRef, useState, type KeyboardEvent } from "react";

export function ChatComposer({
  onSend,
  busy,
}: {
  onSend: (text: string) => void;
  busy: boolean;
}) {
  const [text, setText] = useState("");
  const ref = useRef<HTMLTextAreaElement>(null);

  const submit = () => {
    const v = text.trim();
    if (!v || busy) return;
    onSend(v);
    setText("");
    if (ref.current) ref.current.style.height = "auto";
  };

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  const grow = (el: HTMLTextAreaElement) => {
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  };

  return (
    <div className="border-t border-hairline bg-parchment-raised/95 backdrop-blur">
      <div className="mx-auto max-w-3xl px-4 py-3 sm:px-6">
        <div
          className="flex items-end gap-2 rounded-3xl border border-hairline bg-tint-blue-soft p-1.5 pl-4 shadow-sm transition-shadow focus-within:border-brass focus-within:bg-parchment-raised focus-within:shadow-[0_0_0_3px_var(--brass-soft)]"
        >
          <textarea
            ref={ref}
            value={text}
            onChange={(e) => {
              setText(e.target.value);
              grow(e.target);
            }}
            onKeyDown={onKeyDown}
            rows={1}
            aria-label="Message Capstone Compass"
            placeholder="Ask for ideas, or push back…"
            className="min-h-[38px] max-h-40 flex-1 resize-none bg-transparent py-2 text-sm leading-snug outline-none"
          />
          <button
            type="button"
            onClick={submit}
            disabled={busy || !text.trim()}
            aria-label="Send message"
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-white transition-all disabled:opacity-40"
            style={{ background: "linear-gradient(135deg, var(--brass), var(--deep-teal))" }}
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden>
              <path
                d="M2 8h11m0 0-4.5-4.5M13 8l-4.5 4.5"
                stroke="currentColor"
                strokeWidth="1.6"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </button>
        </div>
        <p className="mt-2 text-center text-[11px] text-charcoal-text/45">
          Retrieval over the local catalogue, not generative — every reply cites a real Project ID.
        </p>
      </div>
    </div>
  );
}
