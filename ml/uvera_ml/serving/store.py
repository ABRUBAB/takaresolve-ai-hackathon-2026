"""Find artifacts and remember where each one came from (official Kaggle run vs local dev build)."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from uvera_ml.common import repo_root


class ArtifactStore:
    def __init__(self, dirs: list[str | Path] | None = None):
        root = repo_root()
        self.dirs = [Path(d) for d in (dirs or [root, root / "_outputs" / "dev"])]
        self.sources: dict[str, str] = {}

    def path(self, rel: str) -> Path | None:
        for d in self.dirs:
            p = d / rel
            if p.exists():
                self.sources[rel.split("/")[1] if rel.startswith("artifacts/") else rel] = (
                    "official" if d == self.dirs[0] else "dev")
                return p
        return None

    def json(self, rel: str, default=None):
        p = self.path(rel)
        return json.loads(p.read_text(encoding="utf-8")) if p else default

    def parquet(self, rel: str) -> pd.DataFrame | None:
        p = self.path(rel)
        return pd.read_parquet(p) if p else None

    def source_of(self, ai: str) -> str:
        """'official' (Kaggle results in artifacts/), 'dev' (local quick build) or 'missing'."""
        for d, label in zip(self.dirs, ["official", "dev"]):
            if (d / "artifacts" / ai).exists():
                return label
        return "missing"
