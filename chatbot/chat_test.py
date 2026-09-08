"""Sanity check for the two-stage fine-tune.

    python chat_test.py [--greedy]

Loads models/projectlens-final/, runs the four prompts from the brief plus a
few router checks, and flags each reply as on-script or drifted.
"""

from __future__ import annotations

import argparse

import torch

from generate import SmallTalker
from intent_router import classify

# prompt -> what a correct reply should look like (lo's checks, not exact match)
CHECKS = [
    ("hi", "smalltalk", ["capstone", "help", "find", "project", "compass", "hi", "hey", "hello"]),
    ("who are you", "smalltalk", ["capstone compass", "project", "catalogue", "match", "assistant", "retriev"]),
    ("what's the weather like", "smalltalk", ["outside what i do", "not", "capstone", "project", "lane", "area"]),
    ("suggest me a web dev project", "task", []),  # must route AWAY from the generative model
]


def looks_on_script(reply: str, keywords: list[str]) -> bool:
    low = reply.lower()
    return any(k in low for k in keywords)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--greedy", action="store_true")
    args = ap.parse_args()

    torch.manual_seed(0)
    bot = SmallTalker()

    print(f"{'PROMPT':<34} {'ROUTE':<10} VERDICT / REPLY")
    print("-" * 100)
    for prompt, expect_dest, keywords in CHECKS:
        r = classify(prompt)
        routed_ok = r.destination == expect_dest

        if r.destination == "task":
            verdict = "OK (routed to recommendation engine, generative model not used)" if routed_ok else "!! MIS-ROUTED"
            print(f"{prompt!r:<34} {r.destination:<10} {verdict}")
            continue

        reply = bot.reply(prompt, greedy=args.greedy)
        on_script = looks_on_script(reply, keywords)
        tag = "OK  " if (routed_ok and on_script) else "DRIFT"
        print(f"{prompt!r:<34} {r.destination + '/' + r.intent:<10} [{tag}] {reply}")

    print("\nNote: with a full-data Stage 1 run the tone is fluent; a small --max-samples")
    print("smoke run will read rough - the identity/scope keywords are what matter here.")


if __name__ == "__main__":
    main()
