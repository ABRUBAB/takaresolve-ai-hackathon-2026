"""Copy the homepage world sample and the notebook figures into the website as static files.

    python scripts/export_web_assets.py

Reads artifacts/web/world_sample.json (official NB00 run; falls back to the local dev build) and writes
frontend/public/data/world-sample.json in a compact form.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    src = next((p for p in (ROOT / "artifacts/web/world_sample.json", ROOT / "_outputs/dev/artifacts/web/world_sample.json") if p.exists()), None)
    if src is None:
        raise SystemExit("No world sample found. Run NB00 (or scripts/build_dev_artifacts.py) first.")
    d = json.loads(src.read_text(encoding="utf-8"))
    # Compact: ids are not needed for the visual, so nodes and edges are arrays that refer to each other by index.
    node_types = ["customer", "agent", "merchant", "case", "external"]
    flags = [None, "mule", "disguised_qr", "case"]
    edge_types = ["p2p", "qr_pay", "cash_out", "case_link"]
    index = {n["id"]: i for i, n in enumerate(d["nodes"])}
    out = {"note": d["note"], "source": "official" if "_outputs" not in str(src) else "dev",
           "format": {"node": ["type", "flag"], "edge": ["source", "target", "type", "amount", "scam", "case"],
                      "node_types": node_types, "flags": flags, "edge_types": edge_types},
           "nodes": [[node_types.index(n["type"]), flags.index(n["flag"])] for n in d["nodes"]],
           "edges": [[index[e["source"]], index[e["target"]], edge_types.index(e["type"]), round(float(e["amount"])),
                      int(bool(e["scam"])), e["case"] if e["case"] is not None else -1]
                     for e in d["edges"] if e["source"] in index and e["target"] in index]}
    dest = ROOT / "frontend/public/data/world-sample.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
    print(f"{src.relative_to(ROOT)} -> {dest.relative_to(ROOT)} ({dest.stat().st_size // 1024} KB, {len(out['nodes'])} nodes, {len(out['edges'])} edges)")

    # notebook figures for the Trust Center: official Kaggle figures first, local build only where a notebook has not run
    figs = ROOT / "frontend/public/figures"
    figs.mkdir(parents=True, exist_ok=True)
    manifest = []
    names = {f.name for d in (ROOT / "reports/figures", ROOT / "_outputs/dev/reports/figures") if d.exists() for f in d.glob("*.png")}
    for name in sorted(names):
        official = ROOT / "reports/figures" / name
        f = official if official.exists() else ROOT / "_outputs/dev/reports/figures" / name
        (figs / name).write_bytes(f.read_bytes())
        manifest.append({"file": name, "source": "official" if f == official else "dev"})
    for stale in figs.glob("*.png"):
        if stale.name not in names:
            stale.unlink()
    (figs / "manifest.json").write_text(json.dumps({"figures": manifest}, indent=1), encoding="utf-8")
    print(f"{len(manifest)} figures -> frontend/public/figures ({sum(m['source'] == 'official' for m in manifest)} official)")


if __name__ == "__main__":
    main()
