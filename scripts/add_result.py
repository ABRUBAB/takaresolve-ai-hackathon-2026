"""Add a Kaggle notebook result zip (NBxx_outputs.zip) to the repo and commit it.

Usage (from the repo folder):
    python scripts/add_result.py "D:\\path\\to\\NB05_outputs.zip"
Then publish it with:
    git push
"""
from __future__ import annotations

import re
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALLOWED = ("artifacts/", "reports/")


def add_notebook(nb_path: Path) -> None:
    """Executed notebook downloaded from a Kaggle version (has outputs) -> notebooks/executed/."""
    dest = ROOT / "notebooks" / "executed" / nb_path.name
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(nb_path.read_bytes())
    subprocess.run(["git", "-C", str(ROOT), "add", str(dest)], check=True)
    subprocess.run(["git", "-C", str(ROOT), "commit", "-q", "-m", f"docs(notebooks): executed {nb_path.stem} from Kaggle"], check=True)
    print(f"Committed executed notebook {nb_path.name}")


def add(zip_path: Path) -> str:
    if not zip_path.exists():
        sys.exit(f"File not found: {zip_path}")
    if zip_path.suffix == ".ipynb":
        add_notebook(zip_path)
        return zip_path.stem
    nb = re.search(r"(NB\d\d)", zip_path.name, re.I)
    nb = nb.group(1).upper() if nb else zip_path.stem
    with zipfile.ZipFile(zip_path) as z:
        names = [n for n in z.namelist() if not n.endswith("/")]
        bad = [n for n in names if not n.startswith(ALLOWED) or ".." in n]
        if bad:
            sys.exit(f"Refusing: unexpected files in the zip: {bad[:5]}")
        z.extractall(ROOT, members=names)
    print(f"{nb}: added {len(names)} files")
    for n in names:
        print("  ", n)
    subprocess.run(["git", "-C", str(ROOT), "add", "artifacts", "reports"], check=True)
    staged = subprocess.run(["git", "-C", str(ROOT), "diff", "--cached", "--quiet"], stdout=subprocess.DEVNULL)
    if staged.returncode == 0:
        print("Nothing new to commit (these results are already in the repo).")
        return nb
    subprocess.run(["git", "-C", str(ROOT), "commit", "-q", "-m", f"results({nb.lower()}): add Kaggle outputs from {nb}"], check=True)
    print(f"Committed {nb} results.")
    return nb


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    for arg in sys.argv[1:]:
        add(Path(arg))
    print("\nNow publish to GitHub with:  git push")
