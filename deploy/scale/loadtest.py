"""Host entry point for the load generator (same code as `python -m uvscale.loadtest` inside the stack).

  .venv\\Scripts\\python deploy/scale/loadtest.py --url http://127.0.0.1:8080 --scenario transfer -c 1 8 32 -d 30
  .venv\\Scripts\\python deploy/scale/loadtest.py --url http://127.0.0.1:8020 --scenario monolith --token <jwt> -c 1 8 32
"""
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
os.environ.setdefault("LOADGEN_DATA", str(HERE.parents[1] / "_outputs" / "scale"))

from uvscale.loadtest import main  # noqa: E402

if __name__ == "__main__":
    main()
