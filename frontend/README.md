# Capstone Compass — frontend

Next.js 14 (App Router) · TypeScript · Tailwind CSS. Talks to the backend at
`NEXT_PUBLIC_API_BASE` (default `http://127.0.0.1:8000`).

```bash
npm install
npm run dev        # http://localhost:3000
npm run build && npm start
```

Nothing is fetched from the network at build or runtime: the three typefaces
(Fraunces, Inter, JetBrains Mono) are vendored as `.woff2` under
`public/fonts/` and loaded via `next/font/local`.

## Pages

| Route | What |
|---|---|
| `/` | Landing — what it is + the one-paragraph honest guardrail disclosure |
| `/onboarding` | Student profile form (tag inputs, comfort, prior projects, outcome) |
| `/recommendations` | Two-pane workspace: instrument panel (profile + cluster bearings + filters) · flowing card list · plain-language refine bar |
| `/admin` | Needs-Review queue, corpus browser, batch upload, retrain + version history, faculty-preference form |
| `/about` | TF-IDF + KMeans explanation, live corpus counts, standing disclosures |

## Design system

Tokens live once in `app/globals.css` (`--ink`, `--parchment`, `--brass`,
`--deep-teal`, …) mirrored into `tailwind.config.ts`. The compass/wayfinding
metaphor is the through-line: `MatchCompass` is a needle dial (not a progress
bar) whose reading is the real cosine on a fixed 0–0.5 scale, and the one
deliberate motion is the needle *settling* on new results — skipped entirely
under `prefers-reduced-motion`.

Quality floor: responsive to 320px, visible `:focus-visible` outlines, `aria-live`
on the results region, `aria-current` nav, keyboard-friendly tag inputs, WCAG-AA
contrast in light and dark.

## Client state

`lib/store.ts` keeps the last profile + result set in `localStorage` (wrapped in
try/catch — the app still works with storage disabled, it just won't pre-fill).
The database of record is the backend.
