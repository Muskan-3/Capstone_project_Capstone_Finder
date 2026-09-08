"""Intent router + canned small-talk replies.

The guardrail from the chatbot spec, living in the backend so the live chat
actually uses it: a message that is just a greeting / identity question /
thanks / farewell / off-topic aside gets a short fixed reply and never
touches the recommendation engine; anything that looks like a real request -
or anything ambiguous - falls through to the TF-IDF + KMeans engine.

Pure standard library (regex only) - no torch, no model download. The
fine-tuned DialoGPT model in ../../chatbot is an optional nicer-tone upgrade
that would run as a separate service; it is not required for this.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass

ASSISTANT_NAME = "Capstone Compass"

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
_IDENTITY = re.compile(
    r"\b(who\s*(are|r)\s*(you|u)|what\s*(are|r)\s*(you|u)|what\s*can\s*you\s*do|"
    r"what\s*do\s*you\s*do|tell\s*me\s*about\s*(yourself|you)|what\s*are\s*you\s*for|"
    r"are\s*you\s*(a\s*)?(bot|ai|human|chatgpt|gpt|robot|real|person)|"
    r"your\s*name|do\s*you\s*have\s*a\s*name|how\s*do\s*you\s*work|what'?s\s*your\s*purpose|"
    r"what\s*(kind\s*of\s*)?(assistant|model)\s*(are\s*you)?|what\s*are\s*your\s*capabilities|"
    r"what\s*is\s*(this|projectlens|capstone\s*compass))\b",
    re.IGNORECASE,
)
# polite "how are you" pleasantries - a warm one-liner, not a "not my domain" brush-off.
# the negative lookahead keeps out "how are you going to build this" etc.
_WELLBEING = re.compile(
    r"\b(how\s*(are|'?s|is)\s*(you|u|it|things|everything|your\s*day)"
    r"(?!\s+(going|gonna|able|supposed|planning|meant))|"
    r"how\s*(are\s*)?(you|u)\s*doing|how'?s\s*it\s*going|how\s*have\s*you\s*been|"
    r"how\s*do\s*you\s*do|you\s*(doing\s*)?(ok|okay|good|alright|well)\??$|"
    r"hope\s*you'?re\s*(well|good|doing\s*well))\b",
    re.IGNORECASE,
)
_OFFTOPIC = re.compile(
    r"\b(weather|tell\s*me\s*a\s*joke|a\s*joke|say\s*something\s*funny|favou?rite\s|"
    r"do\s*you\s*(like|love|eat|sleep|dream|watch)|how\s*old\s*are\s*you|"
    r"where\s*(are|do)\s*you\s*(live|from)|are\s*you\s*single|sing\s*(a\s*)?song|"
    r"play\s*a\s*game|the\s*news|sports?|movie|football|cricket|who\s*won|"
    r"meaning\s*of\s*life|relationship\s*advice|my\s*(math|physics|chemistry)\s*homework|"
    r"what\s*time\s*is\s*it|just\s*chat|entertain\s*me|i'?m\s*bored)\b",
    re.IGNORECASE,
)
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


@dataclass
class Route:
    destination: str  # "smalltalk" | "task"
    intent: str       # greeting | identity | wellbeing | thanks | farewell | offtopic | recommend


def classify(message: str) -> Route:
    text = (message or "").strip()
    if not text:
        return Route("task", "recommend")

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

    return Route("task", "recommend")


def _first_name(name: str | None) -> str:
    return (name or "").strip().split(" ")[0] if name else ""


def respond(intent: str, name: str | None = None) -> str:
    fn = _first_name(name)
    hello = f"Hi{' ' + fn if fn else ''}! " if intent == "greeting" else ""

    pools = {
        "greeting": [
            f"{hello}I'm {ASSISTANT_NAME}. Tell me a skill or a topic you'd like to "
            "work on and I'll pull up matching capstone problem statements.",
            f"{hello}I match you to real capstone problem statements from your "
            "department's catalogue. What are you interested in?",
        ],
        "identity": [
            f"I'm {ASSISTANT_NAME}, a project-matching assistant. I search your "
            "department's real catalogue of capstone problem statements and rank the "
            "ones that fit your skills and interests - each with a real similarity "
            "score. I don't do general chat or generate project ideas myself.",
            f"I'm {ASSISTANT_NAME}. My only job is helping you find a capstone problem "
            "statement: you tell me what you know and what you're into, I retrieve the "
            "closest real matches from the catalogue. That's the whole scope.",
        ],
        "wellbeing": [
            f"Doing well, thanks for asking{', ' + fn if fn else ''}! What kind of "
            "capstone project can I help you find?",
            "All good here and ready to help. Tell me a skill or a topic and I'll pull "
            "up some matching problem statements.",
            "I'm good - thanks! Give me a domain or an interest and I'll chart the "
            "closest projects.",
        ],
        "offtopic": [
            "That's a bit outside what I do - I'm just here to help you find a capstone "
            "project. Tell me a skill or a topic you're interested in and I'll pull up "
            "some matches.",
            "Not my area - I only do capstone project matching. What kind of project "
            "are you looking for?",
        ],
        "thanks": [
            "Anytime! Ask again whenever you want more options.",
            "Happy to help - let me know if you want to refine the matches or try a "
            "different direction.",
        ],
        "farewell": [
            "Good luck with the project - come back if you want to explore other "
            "directions.",
            "See you. Ping me whenever you're ready to look again.",
        ],
    }
    return random.choice(pools.get(intent, pools["greeting"]))
