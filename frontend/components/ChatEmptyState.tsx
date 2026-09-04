"use client";

import { CompassMark } from "./CompassMark";

const SUGGESTIONS = [
  {
    title: "Quantum machine learning",
    body: "I know Python and linear algebra, interested in QML",
    icon: "◈",
  },
  {
    title: "Something web-based",
    body: "Show me web development or full-stack project ideas",
    icon: "◆",
  },
  {
    title: "Cybersecurity angle",
    body: "I like cryptography and post-quantum security",
    icon: "◇",
  },
  {
    title: "Not sure yet",
    body: "Surprise me with something well-scoped and interesting",
    icon: "○",
  },
];

export function ChatEmptyState({
  name,
  onPick,
}: {
  name: string;
  onPick: (text: string) => void;
}) {
  return (
    <div className="chat-turn-in mx-auto max-w-2xl py-6 text-center">
      <span
        className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl text-white shadow-lg"
        style={{ background: "linear-gradient(135deg, var(--brass), var(--deep-teal))" }}
      >
        <CompassMark size={28} />
      </span>
      <h1 className="mt-4 font-display text-2xl">
        Hey {name.split(" ")[0] || "there"}, where should we look?
      </h1>
      <p className="mt-2 text-sm text-charcoal-text/65">
        Name a skill, an interest, or just describe what you're into - I'll chart the closest
        matches in the catalogue.
      </p>

      <div className="mt-7 grid gap-3 text-left sm:grid-cols-2">
        {SUGGESTIONS.map((s) => (
          <button
            key={s.title}
            type="button"
            onClick={() => onPick(s.body)}
            className="group rounded-2xl border border-hairline bg-parchment-raised p-4 text-left transition-all hover:-translate-y-0.5 hover:border-brass hover:shadow-lg"
          >
            <span className="text-lg" style={{ color: "var(--deep-teal)" }} aria-hidden>
              {s.icon}
            </span>
            <p className="mt-1.5 text-sm font-medium">{s.title}</p>
            <p className="mt-0.5 text-xs text-charcoal-text/55">{s.body}</p>
          </button>
        ))}
      </div>
    </div>
  );
}
