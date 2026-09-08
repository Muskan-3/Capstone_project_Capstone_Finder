"""Shared helpers - device detection, paths, model I/O.

Written to run unmodified on:
  * a CUDA GPU (Colab free T4, etc.)   -> fp16, fastest
  * Apple Silicon (MPS)                -> fp32
  * plain CPU                          -> fp32, slow but works for smoke tests
"""

from __future__ import annotations

import json
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
MODELS = ROOT / "models"

BASE_MODEL = "microsoft/DialoGPT-small"
STAGE1_DIR = MODELS / "projectlens-stage1"
FINAL_DIR = MODELS / "projectlens-final"

PAIRS_FILE = DATA / "personachat_pairs.jsonl"
IDENTITY_FILE = DATA / "identity_examples.jsonl"


def device() -> str:
    if torch.cuda.is_available():
        return "cuda"
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def use_fp16() -> bool:
    # fp16 mixed precision is only reliable on CUDA; MPS/CPU stay fp32
    return torch.cuda.is_available()


def read_jsonl(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
