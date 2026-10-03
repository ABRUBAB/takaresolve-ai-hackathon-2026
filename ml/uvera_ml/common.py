"""Shared helpers: repo paths, config loading, output folders, hashing, timing."""
from __future__ import annotations

import hashlib
import json
import os
import platform
import random
import shutil
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import numpy as np
import yaml


def repo_root() -> Path:
    """Find the repository root (the folder that contains `configs/`).

    Order: $UVERA_ROOT, then walk up from the current directory, then from this file.
    """
    env = os.environ.get("UVERA_ROOT")
    if env and (Path(env) / "configs").is_dir():
        return Path(env)
    for start in (Path.cwd(), Path(__file__).resolve()):
        for p in [start, *start.parents]:
            if (p / "configs").is_dir() and (p / "ml").is_dir():
                return p
    raise FileNotFoundError("Could not find the repo root (set UVERA_ROOT).")


def load_config(name: str) -> dict:
    """Load a YAML file from configs/, e.g. load_config('assumptions') or load_config('rules/dispute')."""
    path = repo_root() / "configs" / (name if name.endswith(".yaml") else f"{name}.yaml")
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)


def out_dir(nb: str, base: str | Path | None = None) -> Path:
    """Output folder that mirrors the repo layout (artifacts/, reports/) so it can be unzipped at the repo root."""
    if base is None:
        base = "/kaggle/working/outputs" if Path("/kaggle/working").exists() else repo_root() / "_outputs"
    d = Path(base) / nb
    (d / "artifacts").mkdir(parents=True, exist_ok=True)
    (d / "reports" / "figures").mkdir(parents=True, exist_ok=True)
    return d


def write_json(path: str | Path, obj: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False, default=_json_default), encoding="utf-8")


def read_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _json_default(o: Any) -> Any:
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return None if np.isnan(o) else round(float(o), 6)
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, Path):
        return str(o)
    raise TypeError(f"not JSON serialisable: {type(o)}")


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_frame(df) -> str:
    """Stable content hash of a DataFrame (order-sensitive).

    Datetimes are hashed at nanosecond resolution: pandas 3 stores them in microseconds, which would otherwise change
    the hash of identical data."""
    import pandas as pd

    dt = [c for c in df.columns if pd.api.types.is_datetime64_any_dtype(df[c])]
    if dt:
        df = df.astype({c: "datetime64[ns]" for c in dt})
    return hashlib.sha256(pd.util.hash_pandas_object(df, index=False).values.tobytes()).hexdigest()


def env_info() -> dict:
    info = {"python": platform.python_version(), "platform": platform.platform()}
    for mod in ["numpy", "pandas", "sklearn", "lightgbm", "xgboost", "catboost", "torch",
                "sentence_transformers", "chronos", "networkx", "google.genai"]:
        try:
            m = __import__(mod, fromlist=["__version__"])
            info[mod] = getattr(m, "__version__", "installed")
        except Exception:
            info[mod] = None
    try:
        import torch

        info["cuda"] = torch.cuda.is_available()
        info["gpu"] = torch.cuda.get_device_name(0) if torch.cuda.is_available() else None
    except Exception:
        info["cuda"] = False
    return info


class Budget:
    """Expected run time per notebook, logged at the end of each stage.

    Over budget only prints a warning: every check sits right before the cell that zips the results, so raising there
    would throw away finished work. Kaggle's own 12-hour cap still applies."""

    def __init__(self, minutes: float):
        self.t0 = time.time()
        self.minutes = minutes

    def elapsed(self) -> float:
        return (time.time() - self.t0) / 60

    def check(self, stage: str) -> None:
        print(f"[{stage}] elapsed {self.elapsed():.1f} min")
        if self.elapsed() > self.minutes:
            print(f"WARNING: over the expected {self.minutes} min at stage '{stage}' (results are still saved)")


@contextmanager
def timer(label: str):
    t = time.time()
    yield
    print(f"{label}: {time.time() - t:.1f}s")


def zip_outputs(nb_dir: str | Path) -> Path:
    """Zip an output folder; the zip unpacks into artifacts/ and reports/ at the repo root."""
    nb_dir = Path(nb_dir)
    archive = shutil.make_archive(str(nb_dir.parent / f"{nb_dir.name}_outputs"), "zip", root_dir=nb_dir)
    print("Download this file from the notebook's Output tab:", archive)
    return Path(archive)
