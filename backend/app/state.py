"""Loads the synthetic world and every AI engine once, in a background thread (the API answers 'warming up' meanwhile)."""
from __future__ import annotations

import threading
import time
import traceback
from pathlib import Path

from app.core.config import settings


class AppState:
    def __init__(self):
        self.ready = False
        self.error: str | None = None
        self.progress: list[str] = []
        self.started = time.time()
        self.lock = threading.Lock()
        self.integrity: dict | None = None  # result of the artifact SHA-256 + approval check (uvera_ml.registry.verify)

    def _step(self, msg: str) -> None:
        self.progress.append(f"{time.time() - self.started:5.1f}s {msg}")
        print("[startup]", self.progress[-1], flush=True)

    def verify_artifacts(self) -> bool:
        """Every served model file must match its SHA-256 in artifacts/registry.json and its active version must be
        approved. Fails closed: with ARTIFACT_VERIFY=strict (default) no model is served after a failure."""
        from uvera_ml.common import repo_root
        from uvera_ml.registry import verify

        model_dir = Path(settings.model_dir) if settings.model_dir else repo_root() / "artifacts"
        self.integrity = verify(model_dir)
        if self.integrity["ok"]:
            self._step(f"artifacts verified: {sum(m['files'] for m in self.integrity['models'].values())} files, "
                       f"{len(self.integrity['models'])} approved model versions")
            return True
        bad = [f"{b['path']} ({b['problem']})" for b in self.integrity["bad_files"]] + self.integrity["problems"]
        self._step("ARTIFACT INTEGRITY CHECK FAILED: " + "; ".join(dict.fromkeys(bad))[:600])
        return settings.artifact_verify.lower() != "strict"

    def load(self) -> None:
        self.ready, self.error = False, None
        try:
            if not self.verify_artifacts():
                self.error = ("Model artifact integrity check failed, models are not served: "
                              + ", ".join(dict.fromkeys(b["path"] for b in self.integrity["bad_files"]))
                              + (" | " + "; ".join(self.integrity["problems"]) if self.integrity["problems"] else ""))[:1500]
                return
            self._load_engines()
        except Exception:  # noqa: BLE001 - surfaced through /v1/health/ready
            self.error = traceback.format_exc()[-1500:]
            print(self.error, flush=True)

    def _load_engines(self) -> None:
        from uvera_ml.common import repo_root
        from uvera_ml.serving import scenarios
        from uvera_ml.serving.briefs import BriefEngine
        from uvera_ml.serving.cases import CaseEngine
        from uvera_ml.serving.forecasts import ForecastEngine
        from uvera_ml.serving.pause import PauseCheckEngine
        from uvera_ml.serving.qr import QREngine
        from uvera_ml.serving.store import ArtifactStore
        from uvera_ml.serving.text import TextEngine
        from uvera_ml.sim.world import load_or_generate

        root = repo_root()
        model_root = Path(settings.model_dir).resolve().parent if settings.model_dir else root
        self.store = ArtifactStore([model_root, root / "_outputs" / "dev"])
        self._step("loading synthetic world")
        self.world = load_or_generate(settings.world_dir, scale=settings.world_scale)
        self.data_version = self.world.meta.get("hashes", {}).get("events", "unknown")[:12]
        self._step("AI-1 pause check")
        self.pause = PauseCheckEngine(self.world, self.store)
        self._step("AI-2 text check")
        self.text = TextEngine(self.store)
        self._step("AI-3/4 forecasts")
        self.forecasts = ForecastEngine(self.world, self.store, n_fit_customers=1500)
        self._step("AI-5 QR shield")
        self.qr = QREngine(self.world, self.store)
        self._step("AI-6 cases")
        self.cases = CaseEngine(self.store, self.qr.state_of)
        self._step("AI-7 briefs")
        self.briefs = BriefEngine(self.store, settings.llm_mode)
        self._step("demo scenarios")
        self.demo = scenarios.build(self.world, self.pause, self.forecasts, self.qr, self.cases)
        self.ready = True
        self._step("ready")
        # warm the slow QR merchant features after "ready", so the first merchant drawer opens instantly
        try:
            self.qr.features()
            self._step("QR features warmed")
        except Exception:  # noqa: BLE001 - optional warm-up; the drawer builds them on first use instead
            self._step("QR features will be built on first use")

    def start(self) -> None:
        threading.Thread(target=self.load, daemon=True).start()


state = AppState()
