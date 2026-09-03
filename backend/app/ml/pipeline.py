"""Vectorize -> cluster (with a silhouette sweep) -> package a versioned artifact.

Step 2 and Step 3 of Section 5. The clustering is the mechanism that stops the
~98% quantum majority from drowning out every other domain: routing happens at the
cluster level *before* ranking, so a non-quantum profile can be sent to a small
non-quantum cluster (or to the honest low-confidence state) instead of being
force-ranked against 185 quantum statements.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import numpy as np
from scipy import sparse
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import normalize


@dataclass
class DocMeta:
    id: int
    project_id: str
    title: str
    statement: str
    source_batch: str


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

    # ---- convenience --------------------------------------------------- #
    def cluster_label(self, cluster_id: int) -> str:
        terms = self.cluster_terms.get(cluster_id, [])
        return " · ".join(terms[:3]) if terms else f"cluster {cluster_id}"

    def meta_by_row(self, row: int) -> DocMeta:
        return self.docs_meta[row]

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
) -> ModelArtifacts:
    """Fit the TF-IDF + KMeans pipeline over the *active* (non-flagged) corpus."""
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
        },
    )
