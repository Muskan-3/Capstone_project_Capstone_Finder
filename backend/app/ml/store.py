"""Versioned on-disk model artifacts (joblib).

Layout:  artifacts/v{n}/model.joblib  +  artifacts/v{n}/meta.json

The DB table ``model_versions`` is the source of truth for which version is
*active*; this module just persists and loads the fitted objects. Old versions
are never deleted, so a retrain is always reversible.
"""

from __future__ import annotations

import json
from pathlib import Path

import joblib

from ..config import settings
from .pipeline import ModelArtifacts

_CACHE: dict[int, ModelArtifacts] = {}


def _version_dir(version: int) -> Path:
    return settings.artifacts_dir / f"v{version}"


def next_version() -> int:
    existing = [
        int(p.name[1:])
        for p in settings.artifacts_dir.glob("v*")
        if p.is_dir() and p.name[1:].isdigit()
    ]
    return (max(existing) + 1) if existing else 1


def save(artifacts: ModelArtifacts) -> int:
    vdir = _version_dir(artifacts.version)
    vdir.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifacts, vdir / "model.joblib", compress=3)
    (vdir / "meta.json").write_text(json.dumps(artifacts.status_summary(), indent=2))
    _CACHE[artifacts.version] = artifacts
    return artifacts.version


def load(version: int) -> ModelArtifacts:
    if version in _CACHE:
        return _CACHE[version]
    path = _version_dir(version) / "model.joblib"
    if not path.exists():
        raise FileNotFoundError(f"No saved artifact for model version {version} ({path})")
    art: ModelArtifacts = joblib.load(path)
    _CACHE[version] = art
    return art


def has(version: int) -> bool:
    return version in _CACHE or (_version_dir(version) / "model.joblib").exists()


def evict(version: int | None = None) -> None:
    if version is None:
        _CACHE.clear()
    else:
        _CACHE.pop(version, None)
