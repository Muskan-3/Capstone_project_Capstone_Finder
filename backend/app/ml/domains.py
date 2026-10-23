"""Domain vocabulary shared by query routing, training and the domain backfill.

Two rule sets live here, both plain keyword matching (no model, no network):

* ``keyword_domains(text)`` - the first stage of query routing. It maps a
  student's words to corpus domains ("react" -> Web/Mobile, "arduino" -> IoT).
* ``infer_domain(...)`` - labels a stored problem statement that arrived with
  no ``domain`` (the original quantum workbook, the generated batch). Used by
  ``scripts/assign_domains.py`` to backfill the column, and by training as a
  fallback so an un-backfilled database still gets a working router.
"""

from __future__ import annotations

import re

QUANTUM = "Quantum Computing"

# the 13 domains of the v2 corpus plus the original quantum workbook
DOMAINS: tuple[str, ...] = (
    "AI/ML",
    "Web/Mobile",
    "IoT",
    "Cybersecurity",
    "Blockchain",
    "Cloud Computing",
    "NLP",
    "Computer Vision",
    "Data Analytics",
    "Civil Engineering",
    "Mechanical Engineering",
    "Electrical & Electronics",
    "Computer Science & IT",
    QUANTUM,
)

# query keyword -> domain. Plurals match automatically ("sensors", "apps").
# Computer Science & IT has no keywords on purpose: its statements are generic
# software projects, so it is reached through the classifier fallback only.
QUERY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "Web/Mobile": ("website", "web", "react", "frontend", "app", "android", "ios",
                   "flutter", "mobile"),
    "AI/ML": ("ml", "ai", "machine learning", "deep learning", "prediction", "predict"),
    "IoT": ("iot", "sensor", "arduino"),
    "Cybersecurity": ("security", "cybersecurity", "cyber", "hacking", "malware",
                      "encryption"),
    "Blockchain": ("blockchain", "smart contract"),
    "Cloud Computing": ("cloud", "aws", "azure", "docker"),
    "NLP": ("nlp", "chatbot", "text"),
    "Computer Vision": ("vision", "image", "opencv"),
    "Data Analytics": ("dashboard", "analytics"),
    "Civil Engineering": ("civil", "structural", "bridge", "soil"),
    "Mechanical Engineering": ("mechanical", "thermal", "cfd"),
    "Electrical & Electronics": ("electrical", "power", "circuit", "battery"),
    QUANTUM: ("quantum", "qubit", "qiskit"),
}

_KW_PATTERNS: dict[str, list[re.Pattern[str]]] = {
    domain: [re.compile(rf"(?<![a-z0-9]){re.escape(kw)}(?:s|es)?(?![a-z0-9])") for kw in kws]
    for domain, kws in QUERY_KEYWORDS.items()
}

# includes the algorithm acronyms the workbook titles use on their own ("... using QSVM")
_QUANTUM_RE = re.compile(r"quantum|qubit|qiskit|\b(?:qkd|qsvm|qaoa|vqe|qml|qnn)\b", re.IGNORECASE)

# the generated batch encodes its domain in the Project ID (scripts/import_generated.py)
_GEN_CODES = {
    "AIML": "AI/ML",
    "CYB": "Cybersecurity",
    "CIV": "Civil Engineering",
    "EEE": "Electrical & Electronics",
    "MECH": "Mechanical Engineering",
}
_GEN_ID = re.compile(r"^GEN-([A-Z]+)-\d+")


def keyword_hits(text: str) -> dict[str, list[str]]:
    """Domain -> the distinct keywords from ``QUERY_KEYWORDS`` found in ``text``."""
    low = (text or "").lower()
    hits: dict[str, list[str]] = {}
    for domain, patterns in _KW_PATTERNS.items():
        found = [kw for kw, pat in zip(QUERY_KEYWORDS[domain], patterns) if pat.search(low)]
        if found:
            hits[domain] = found
    return hits


def keyword_domains(text: str) -> list[tuple[str, int]]:
    """Domains whose keywords appear in ``text``, most hits first."""
    hits = keyword_hits(text)
    return sorted(((d, len(kws)) for d, kws in hits.items()), key=lambda x: -x[1])


def infer_domain(project_id: str, title: str | None, statement: str | None) -> tuple[str | None, str]:
    """Best-effort domain for a stored statement with none. Returns (domain, rule).

    Rules, first match wins:
      1. generated rows carry a domain code in their Project ID (GEN-CYB-012)
      2. quantum content: a quantum term in the title, or 2+ in the statement
      3. keyword vote over title (x2) + statement, if one domain clearly leads
    ``domain`` is None when nothing applies; the row is then left unlabelled.
    """
    m = _GEN_ID.match(project_id or "")
    if m and m.group(1) in _GEN_CODES:
        return _GEN_CODES[m.group(1)], f"project_id code {m.group(1)}"

    title, statement = title or "", statement or ""
    if _QUANTUM_RE.search(title):
        return QUANTUM, "quantum term in title"
    n_quantum = len(_QUANTUM_RE.findall(statement))
    if n_quantum >= 2:
        return QUANTUM, f"{n_quantum} quantum terms in statement"

    votes: dict[str, int] = {}
    for domain, kws in keyword_hits(title).items():
        votes[domain] = votes.get(domain, 0) + 2 * len(kws)
    for domain, kws in keyword_hits(statement).items():
        votes[domain] = votes.get(domain, 0) + len(kws)
    ranked = sorted(votes.items(), key=lambda x: -x[1])
    if ranked and (len(ranked) == 1 or ranked[0][1] > ranked[1][1]):
        hits = keyword_hits(f"{title} {statement}").get(ranked[0][0], [])
        return ranked[0][0], f"keywords {hits}"
    if ranked:
        return None, f"keyword tie {ranked[:2]}"
    return None, "no rule matched"
