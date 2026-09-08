"""The guardrail. Decides whether a message goes to the small-talk model or
the real recommendation engine - and the generative model NEVER handles the
second case, so it can't invent a project that doesn't exist.

    route("hi there")                      -> "smalltalk"  (intent: greeting)
    route("who are you?")                  -> "smalltalk"  (intent: identity)
    route("what's the weather like")       -> "smalltalk"  (intent: offtopic)
    route("thanks a lot!")                 -> "smalltalk"  (intent: thanks)
    route("suggest me a web dev project")  -> "task"       (intent: recommend)

Rule-based on purpose: transparent and testable. An explicit ask for a
project always wins; a short message that is clearly nothing but chit-chat
goes to the generative layer (trained to greet, disclose scope, or gently
redirect); everything genuinely ambiguous falls through to the grounded
engine, since surfacing real statements is this product's actual job.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# an optional throwaway lead-in ("ok", "well", "cool, ...") before a marker word
_LEAD = r"(?:ok(?:ay)?|alright|cool|great|well|so|hmm+|yeah|yep|oh|hi|hey)?[\s,]*"

_GREETING_START = re.compile(
    rf"^\s*{_LEAD}(hi+|hey+|hello+|yo|hiya|howdy|good\s+(morning|afternoon|evening)|"
    r"greetings|namaste|sup|what'?s\s+up)\b",
    re.IGNORECASE,
)
_THANKS_START = re.compile(
    rf"^\s*{_LEAD}(thanks?|thank\s*(you|u)|thx|ty|cheers|much\s+appreciated|"
    r"appreciate\s+(it|that|this))\b",
    re.IGNORECASE,
)
_FAREWELL_START = re.compile(
    rf"^\s*{_LEAD}(bye+|goodbye|see\s+(you|ya|u)|later|cya|good\s*night|gn|"
    r"take\s+care|catch\s+you\s+later|i'?m\s+done|that'?s\s+all|gotta\s+go|talk\s+later)\b",
    re.IGNORECASE,
)
# identity questions - can appear anywhere in the sentence
_IDENTITY = re.compile(
    r"\b(who\s*(are|r)\s*(you|u)|what\s*(are|r)\s*(you|u)|what\s*can\s*you\s*do|"
    r"what\s*do\s*you\s*do|tell\s*me\s*about\s*(yourself|you)|what\s*are\s*you\s*for|"
    r"are\s*you\s*(a\s*)?(bot|ai|human|chatgpt|gpt|robot|real|person)|"
    r"your\s*name|do\s*you\s*have\s*a\s*name|how\s*do\s*you\s*work|what'?s\s*your\s*purpose|"
    r"what\s*(kind\s*of\s*)?(assistant|model)\s*(are\s*you)?|what\s*are\s*your\s*capabilities|"
    r"what\s*is\s*(this|projectlens|capstone\s*compass))\b",
    re.IGNORECASE,
)
# polite "how are you" pleasantries - a warm one-liner, not a redirect
_WELLBEING = re.compile(
    r"\b(how\s*(are|'?s|is)\s*(you|u|it|things|everything|your\s*day)"
    r"(?!\s+(going|gonna|able|supposed|planning|meant))|"
    r"how\s*(are\s*)?(you|u)\s*doing|how'?s\s*it\s*going|how\s*have\s*you\s*been|"
    r"how\s*do\s*you\s*do|hope\s*you'?re\s*(well|good|doing\s*well))\b",
    re.IGNORECASE,
)
# off-topic small talk - brief reply then steer back to recommendations
_OFFTOPIC = re.compile(
    r"\b(weather|"
    r"tell\s*me\s*a\s*joke|a\s*joke|say\s*something\s*funny|favou?rite\s|"
    r"do\s*you\s*(like|love|eat|sleep|dream|watch)|how\s*old\s*are\s*you|"
    r"where\s*(are|do)\s*you\s*(live|from)|are\s*you\s*single|sing\s*(a\s*)?song|"
    r"play\s*a\s*game|the\s*news|sports?|movie|football|cricket|who\s*won|"
    r"meaning\s*of\s*life|relationship\s*advice|my\s*(math|physics|chemistry)\s*homework|"
    r"what\s*time\s*is\s*it|just\s*chat|entertain\s*me|i'?m\s*bored)\b",
    re.IGNORECASE,
)
# strong signal the user wants an actual recommendation - always "task"
_TASK_HINT = re.compile(
    r"\b(suggest|recommend|idea|ideas|project|projects|topic|topics|capstone|"
    r"problem\s*statement|thesis|dissertation|domain|field|interested\s*in|"
    r"interest|looking\s*for|show\s*me|find\s*me|give\s*me\s*(a|some|an)|options?|"
    r"i\s*(know|like|want|use|prefer|studied|learned|have\s*done)|my\s*skills?|"
    r"work(ing)?\s*(with|on|in)|experience\s*(with|in)|something\s*(with|about|in|on)|"
    r"web\s*dev|machine\s*learning|quantum|cyber\s*security|data\s*science|"
    r"app\s*(idea|to\s*build)|build\s*(a|an|something))\b",
    re.IGNORECASE,
)

SMALLTALK_INTENTS = ("greeting", "identity", "wellbeing", "thanks", "farewell", "offtopic")


@dataclass
class Route:
    destination: str  # "smalltalk" | "task"
    intent: str       # greeting | identity | wellbeing | thanks | farewell | offtopic | recommend


def classify(message: str) -> Route:
    text = (message or "").strip()
    if not text:
        return Route("smalltalk", "greeting")

    if _TASK_HINT.search(text):
        return Route("task", "recommend")
    if _IDENTITY.search(text):
        return Route("smalltalk", "identity")

    short = len(text.split()) <= 8
    if short and _WELLBEING.search(text):
        return Route("smalltalk", "wellbeing")
    if short and _GREETING_START.match(text):
        return Route("smalltalk", "greeting")
    if short and _THANKS_START.match(text):
        return Route("smalltalk", "thanks")
    if short and _FAREWELL_START.match(text):
        return Route("smalltalk", "farewell")
    if _OFFTOPIC.search(text):
        return Route("smalltalk", "offtopic")

    return Route("task", "recommend")  # ambiguous -> the grounded engine


def route(message: str) -> str:
    return classify(message).destination


if __name__ == "__main__":
    for m in [
        "hi", "hello there!", "hey there", "who are you", "what can you do",
        "are you chatgpt?", "thanks!", "thank you so much", "thanks a lot", "ok bye",
        "bye", "see ya", "what's the weather like", "tell me a joke", "how are you?",
        "suggest me a web dev project", "hey, any quantum ideas?",
        "I'm interested in medical imaging", "I know Python and some React",
        "asdf qwer", "can you help me with my project",
    ]:
        r = classify(m)
        print(f"  {m!r:42} -> {r.destination:10} ({r.intent})")
