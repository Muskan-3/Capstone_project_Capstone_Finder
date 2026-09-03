"use client";

import { useState } from "react";

const QUICK = ["more web-based ideas", "avoid AR/VR", "more optimization", "less simulation"];

export function RefineBar({
  onRefine,
  busy,
  disabled,
}: {
  onRefine: (constraint: string) => void;
  busy: boolean;
  disabled?: boolean;
}) {
  const [text, setText] = useState("");

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const v = text.trim();
    if (v && !busy) {
      onRefine(v);
      setText("");
    }
  };

  return (
    <div className="sticky bottom-0 border-t border-hairline bg-parchment/95 backdrop-blur">
      <div className="mx-auto max-w-chart px-4 py-3 sm:px-6">
        <form onSubmit={submit} className="flex items-center gap-2">
          <input
            value={text}
            onChange={(e) => setText(e.target.value)}
            disabled={disabled}
            aria-label="Adjust course - refine the recommendations in plain language"
            placeholder='Adjust course: “show me more web-based ideas”, “avoid AR/VR”…'
            className="chart-card flex-1 bg-parchment-raised px-3 py-2 text-sm outline-none disabled:opacity-50"
          />
          <button type="submit" className="btn btn-primary" disabled={busy || disabled || !text.trim()}>
            {busy ? "Re-plotting…" : "Refine"}
          </button>
        </form>
        {!disabled && (
          <div className="mt-2 flex flex-wrap gap-1.5">
            {QUICK.map((q) => (
              <button
                key={q}
                type="button"
                onClick={() => !busy && onRefine(q)}
                className="pill hover:border-deep-teal hover:text-deep-teal"
              >
                {q}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
