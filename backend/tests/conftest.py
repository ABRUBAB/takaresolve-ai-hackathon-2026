"""Shared test setup: never load the world on import, never touch the real decision database, no visitor rate limit
(the dedicated rate-limit test lowers it on purpose). The full AI engines are loaded once, only by tests that need them,
and only when the synthetic world is already on disk (otherwise those tests are skipped, e.g. in CI)."""
import os
import tempfile
from pathlib import Path

os.environ["WARM_ON_START"] = "false"
os.environ["DB_PATH"] = str(Path(tempfile.mkdtemp(prefix="uvera_tests_")) / "tests.db")
os.environ["RATE_LIMIT_PER_MINUTE"] = "100000"

import pytest  # noqa: E402


@pytest.fixture(scope="session")
def full_state():
    """The real startup path (artifact SHA-256 check + world + every AI engine), run once per test session."""
    from app.core.config import settings
    from app.state import state

    if not Path(settings.world_dir).exists():
        pytest.skip("needs the synthetic world in _outputs/world_full (start the API once to build it)")
    if not state.ready or state.integrity is None:
        state.load()
    assert state.ready, state.error
    return state


@pytest.fixture
def live(full_state):
    """Function-level guard: other tests flip state.ready to check the warming-up path; put it back."""
    full_state.ready, full_state.error = True, None
    yield full_state
