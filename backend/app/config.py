"""Runtime configuration.

Every value has a safe default so the app runs with zero environment setup.
Nothing here points at an external service - there are none.
"""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="COMPASS_", env_file=".env", extra="ignore")

    # --- storage ---
    database_url: str = f"sqlite:///{BACKEND_DIR / 'compass.db'}"
    artifacts_dir: Path = BACKEND_DIR / "artifacts"
    source_workbook: Path = BACKEND_DIR / "data" / "source.xlsx"

    # --- server ---
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    # optional regex for origins that can't be listed exactly (e.g. every Vercel
    # preview deployment: https://capstone-compass-<hash>-<team>.vercel.app)
    cors_origin_regex: str | None = None
    auto_seed: bool = True  # build corpus + first model on startup if the DB is empty

    # --- ML pipeline ---
    tfidf_max_features: int = 5000
    tfidf_min_df: int = 2
    kmeans_k_min: int = 4
    kmeans_k_max: int = 10
    random_state: int = 42

    # --- routing / ranking (calibrated against the seed corpus; see scripts/pipeline_demo.py) ---
    route_confidence_threshold: float = 0.06
    serendipity_cross_cluster: int = 6
    weight_relevance: float = 0.80
    weight_feasibility: float = 0.20
    weight_faculty: float = 0.00  # faculty matching is inactive until real preference data exists
    mmr_lambda: float = 0.70
    top_k: int = 5
    # cosine similarity bands for the honest per-item confidence label
    band_strong: float = 0.17
    band_moderate: float = 0.09

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
settings.artifacts_dir.mkdir(parents=True, exist_ok=True)
