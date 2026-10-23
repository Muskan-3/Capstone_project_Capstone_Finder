"""Vectorize -> fit the domain router -> cluster -> package a versioned artifact.

Routing is by *domain*: every statement carries a domain label (stored, or
inferred by ``domains.infer_domain``), and a TF-IDF + logistic-regression
classifier over those labels is the fallback for queries no keyword rule
catches. Ranking then happens only inside the routed domain(s).

KMeans no longer takes part in routing, gating or ranking. It is kept as a
descriptive topic map for the admin views (corpus cluster column / filter,
model status page) and as the "row is in the trained model" marker
(``problem_statements.cluster_id`` is set only for trained rows).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import numpy as np
from scipy import sparse
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import normalize

from .domains import infer_domain


@dataclass
class DocMeta:
    id: int
    project_id: str
    title: str
    statement: str
    source_batch: str
    domain: str | None = None


@dataclass
class ModelArtifacts:
    version: int
    vectorizer: TfidfVectorizer
    kmeans: KMeans
    doc_ids: list[int]
    doc_matrix: sparse.csr_matrix           # row-normalized tf-idf, aligned with doc_ids
    doc_clusters: np.ndarray
    centroids_unit: np.ndarray               # (k, vocab) L2-normalized, for cosine routing
    cluster_terms: dict[int, list[str]]
    cluster_sizes: dict[int, int]
    docs_meta: list[DocMeta]                  # aligned with doc_ids; snapshot at train time
    k: int
    silhouette: float
    silhouette_by_k: dict[int, float]
    params: dict[str, Any]
    corpus_size: int
    trained_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    # domain routing (absent on artifacts trained before it existed - see has_domain_router)
    doc_domains: list[str | None] = field(default_factory=list)   # aligned with doc_ids
    domain_clf: LogisticRegression | None = None
    domain_sizes: dict[str, int] = field(default_factory=dict)

    # ---- convenience --------------------------------------------------- #
    def cluster_label(self, cluster_id: int) -> str:
        terms = self.cluster_terms.get(cluster_id, [])
        return " · ".join(terms[:3]) if terms else f"cluster {cluster_id}"

    def has_domain_router(self) -> bool:
        # getattr: artifacts pickled before domain routing have no such attribute
        return bool(getattr(self, "doc_domains", None))

    def meta_by_row(self, row: int) -> DocMeta:
        return self.docs_meta[row]

    def unigram_vocab(self) -> set[str]:
        """Single words drawn from the fitted TF-IDF vocabulary (which also
        contains 2-word phrases) - used for grounded, offline typo-tolerance:
        a chat word gets fuzzy-matched only against words that actually
        appear in this corpus, never an external dictionary. Computed on
        demand (not cached on the dataclass) so older pickled artifacts
        loaded from disk don't need a matching stored field."""
        vocab: set[str] = set()
        for feat in self.vectorizer.get_feature_names_out():
            vocab.update(feat.split())
        return vocab

    def status_summary(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "corpus_size": self.corpus_size,
            "cluster_count": self.k,
            "silhouette": round(self.silhouette, 4),
            "silhouette_by_k": {k: round(v, 4) for k, v in self.silhouette_by_k.items()},
            "trained_at": self.trained_at,
            "clusters": [
                {
                    "cluster_id": cid,
                    "label": self.cluster_label(cid),
                    "terms": self.cluster_terms.get(cid, []),
                    "size": self.cluster_sizes.get(cid, 0),
                }
                for cid in sorted(self.cluster_sizes)
            ],
        }


def _build_text(title: str, statement: str) -> str:
    return f"{title or ''} {statement or ''}".strip()


def train(
    docs: list[DocMeta],
    *,
    version: int,
    max_features: int = 5000,
    min_df: int = 2,
    k_min: int = 4,
    k_max: int = 10,
    random_state: int = 42,
    domain_c: float = 4.0,
) -> ModelArtifacts:
    """Fit TF-IDF, the domain classifier and KMeans over the *active* (non-flagged) corpus."""
    if len(docs) < k_min + 2:
        raise ValueError(
            f"Need at least {k_min + 2} active problem statements to train; got {len(docs)}."
        )

    corpus = [_build_text(d.title, d.statement) for d in docs]

    # sklearn's TfidfVectorizer needs no downloads: the English stop-word list ships
    # with the package and the vocabulary is learned from this corpus alone.
    effective_min_df = min_df if len(docs) >= 40 else 1
    vectorizer = TfidfVectorizer(
        max_features=max_features,
        ngram_range=(1, 2),
        stop_words="english",
        min_df=effective_min_df,
        sublinear_tf=True,
    )
    doc_matrix = normalize(vectorizer.fit_transform(corpus))  # rows already l2, be explicit
    feature_names = vectorizer.get_feature_names_out()

    # --- domain router ------------------------------------------------------ #
    # stored label first; rows that never got one are labelled by the same rules
    # as scripts/assign_domains.py, and rows no rule fits stay unlabelled (they
    # are never routed to and never used to train the classifier)
    doc_domains = [
        d.domain or infer_domain(d.project_id, d.title, d.statement)[0] for d in docs
    ]
    labelled = [i for i, dom in enumerate(doc_domains) if dom]
    y = [doc_domains[i] for i in labelled]
    domain_clf: LogisticRegression | None = None
    if len(set(y)) >= 2:
        # balanced: Quantum Computing has ~190 rows next to ~1000 for most domains
        domain_clf = LogisticRegression(C=domain_c, max_iter=2000, class_weight="balanced")
        domain_clf.fit(doc_matrix[labelled], y)
    domain_sizes: dict[str, int] = {}
    for dom in y:
        domain_sizes[dom] = domain_sizes.get(dom, 0) + 1

    # --- silhouette sweep to choose k -------------------------------------- #
    upper = max(k_min + 1, min(k_max, len(docs) - 1))
    silhouette_by_k: dict[int, float] = {}
    best_k, best_score, best_labels, best_model = k_min, -1.0, None, None
    for k in range(k_min, upper + 1):
        model = KMeans(n_clusters=k, random_state=random_state, n_init=10)
        labels = model.fit_predict(doc_matrix)
        if len(set(labels)) < 2:
            continue
        score = float(silhouette_score(doc_matrix, labels, metric="cosine"))
        silhouette_by_k[k] = score
        if score > best_score:
            best_k, best_score, best_labels, best_model = k, score, labels, model

    if best_model is None:  # degenerate corpus - fall back to a single cluster
        best_k = 1
        best_labels = np.zeros(len(docs), dtype=int)
        best_model = KMeans(n_clusters=1, random_state=random_state, n_init=1).fit(doc_matrix)
        best_score = 0.0

    labels = np.asarray(best_labels)
    centroids_unit = normalize(np.asarray(best_model.cluster_centers_))

    cluster_terms: dict[int, list[str]] = {}
    cluster_sizes: dict[int, int] = {}
    for cid in range(best_k):
        cluster_sizes[cid] = int((labels == cid).sum())
        top_idx = np.argsort(centroids_unit[cid])[::-1][:8]
        cluster_terms[cid] = [feature_names[i] for i in top_idx if centroids_unit[cid][i] > 0]

    return ModelArtifacts(
        version=version,
        vectorizer=vectorizer,
        kmeans=best_model,
        doc_ids=[d.id for d in docs],
        doc_matrix=sparse.csr_matrix(doc_matrix),
        doc_clusters=labels,
        centroids_unit=centroids_unit,
        cluster_terms=cluster_terms,
        cluster_sizes=cluster_sizes,
        docs_meta=list(docs),
        k=best_k,
        silhouette=best_score,
        silhouette_by_k=silhouette_by_k,
        corpus_size=len(docs),
        doc_domains=doc_domains,
        domain_clf=domain_clf,
        domain_sizes=domain_sizes,
        params={
            "max_features": max_features,
            "ngram_range": [1, 2],
            "stop_words": "english",
            "min_df": effective_min_df,
            "sublinear_tf": True,
            "k_min": k_min,
            "k_max": k_max,
            "chosen_k": best_k,
            "cluster_selection": "best cosine silhouette over k in [k_min, k_max]",
            "domain_router": {
                "keywords": "app.ml.domains.QUERY_KEYWORDS",
                "classifier": "LogisticRegression" if domain_clf is not None else None,
                "C": domain_c,
                "class_weight": "balanced",
                "labelled_docs": len(labelled),
                "inferred_labels": sum(1 for d in docs if not d.domain) - (len(docs) - len(labelled)),
                "unlabelled_docs": len(docs) - len(labelled),
            },
        },
    )
