"""In-process cache + (de)serialization for trained model artifacts.

The database (``model_versions.artifact_blob``) is the durable copy - see
``app/training.py``, which owns the DB session. This module deliberately has
no filesystem or DB access of its own: a serverless host (Vercel functions
included) gives the process no persistent disk, so the database has to be the
only source of truth, and every environment (local dev, Render, Vercel) loads
the active model the same way. This module just avoids re-deserializing the
same version's ~MB-sized blob on every request within one warm process.
"""

from __future__ import annotations

import io

import joblib

from .pipeline import ModelArtifacts

_CACHE: dict[int, ModelArtifacts] = {}


def serialize(artifacts: ModelArtifacts) -> bytes:
    buf = io.BytesIO()
    joblib.dump(artifacts, buf, compress=3)
    _CACHE[artifacts.version] = artifacts
    return buf.getvalue()


def deserialize(version: int, blob: bytes) -> ModelArtifacts:
    if version in _CACHE:
        return _CACHE[version]
    art: ModelArtifacts = joblib.load(io.BytesIO(blob))
    _CACHE[version] = art
    return art


def cached(version: int) -> ModelArtifacts | None:
    return _CACHE.get(version)


def evict(version: int | None = None) -> None:
    if version is None:
        _CACHE.clear()
    else:
        _CACHE.pop(version, None)
