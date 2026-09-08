"""Stage 1 data prep - general human conversational tone.

    python prepare_stage1_data.py [--max-samples N] [--dedupe]

Loads bavard/personachat_truecased ("full"), and for each row builds one
(input, response) pair:
    input    = history[-1]        (the last thing the other speaker said)
    response = candidates[-1]     (the dataset's gold reply - documented as
                                   always the last candidate)
The `personality` field is dropped entirely on purpose - we want a neutral
conversational tone, not a random invented persona.

Output: data/personachat_pairs.jsonl   {"input": ..., "response": ...}
"""

from __future__ import annotations

import argparse

from datasets import load_dataset

from common import PAIRS_FILE, write_jsonl


def build(max_samples: int | None, dedupe: bool) -> list[dict]:
    try:
        ds = load_dataset("bavard/personachat_truecased", "full")
    except Exception as exc:  # noqa: BLE001 - surface a clear hint
        raise SystemExit(
            f"Could not load bavard/personachat_truecased: {exc}\n"
            "Try: pip install 'datasets<3.0'   (v3 dropped script-based datasets)"
        ) from exc

    splits = [s for s in ("train", "validation", "test") if s in ds]
    pairs: list[dict] = []
    seen: set[tuple[str, str]] = set()

    for split in splits:
        for row in ds[split]:
            history = row.get("history") or []
            candidates = row.get("candidates") or []
            if not history or not candidates:
                continue
            inp = str(history[-1]).strip()
            resp = str(candidates[-1]).strip()
            if not inp or not resp:
                continue
            if dedupe:
                key = (inp, resp)
                if key in seen:
                    continue
                seen.add(key)
            pairs.append({"input": inp, "response": resp})
            if max_samples and len(pairs) >= max_samples:
                return pairs
    return pairs


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-samples", type=int, default=None,
                    help="cap the number of pairs (useful for a local smoke run)")
    ap.add_argument("--dedupe", action="store_true",
                    help="drop exact-duplicate (input, response) pairs")
    args = ap.parse_args()

    pairs = build(args.max_samples, args.dedupe)
    write_jsonl(PAIRS_FILE, pairs)
    print(f"wrote {len(pairs):,} pairs -> {PAIRS_FILE}")
    for p in pairs[:3]:
        print("  ", p)


if __name__ == "__main__":
    main()
