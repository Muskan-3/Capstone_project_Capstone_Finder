"""How the small-talk layer plugs in front of the real recommendation engine.

This is a reference, not wired into the running app yet. The rule it enforces:

    router says "smalltalk"  ->  fine-tuned DialoGPT reply (greet / identity / redirect)
    router says "task"       ->  the existing TF-IDF + KMeans engine, untouched

The generative model is never asked to produce a project suggestion.
"""

from __future__ import annotations

from intent_router import classify

# Lazy import + single instance - loading the model is ~1s, do it once.
_bot = None


def _smalltalker():
    global _bot
    if _bot is None:
        from generate import SmallTalker

        _bot = SmallTalker()
    return _bot


def handle_message(message: str, student_id: int) -> dict:
    """Return a uniform response envelope the frontend can render either way."""
    route = classify(message)

    if route.destination == "smalltalk":
        return {
            "kind": "smalltalk",
            "intent": route.intent,
            "text": _smalltalker().reply(message),
        }

    # route.destination == "task": hand straight to the grounded engine.
    # In the real backend this is the existing call:
    #   res = api.recommend / refine(student_id, message)
    return {
        "kind": "recommendation",
        "intent": route.intent,
        "text": "(routes to backend /api/recommendations/refine - real statements, real scores)",
    }


if __name__ == "__main__":
    for m in ["hey", "who are you", "what's the weather", "I want a machine learning project"]:
        print(f"{m!r:45} -> {handle_message(m, student_id=1)}")
