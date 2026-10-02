"""Config sanity checks: every YAML parses and the core assumptions are consistent."""
from pathlib import Path

import yaml

CONFIGS = Path(__file__).resolve().parents[2] / "configs"


def load(name: str) -> dict:
    return yaml.safe_load((CONFIGS / name).read_text(encoding="utf-8"))


def test_all_yaml_files_parse() -> None:
    files = list(CONFIGS.rglob("*.yaml"))
    assert files, "no config files found"
    for f in files:
        assert yaml.safe_load(f.read_text(encoding="utf-8")) is not None, f


def test_split_fractions_sum_to_one() -> None:
    splits = load("assumptions.yaml")["splits"]
    total = sum(splits[k] for k in ("train", "calibration", "validation", "test"))
    assert abs(total - 1.0) < 0.01


def test_scam_family_shares_sum_to_one() -> None:
    families = load("patterns.yaml")["scam_families"]
    assert abs(sum(f["share"] for f in families.values()) - 1.0) < 1e-9


def test_dispute_rules_are_flagged_until_verified() -> None:
    rules = load("rules/dispute.yaml")
    assert "verified" in rules
    assert rules["reason_codes"] == [] or rules["verified"] is True


def test_heldout_qr_family_exists() -> None:
    heldout = load("assumptions.yaml")["splits"]["qr_heldout_family"]
    families = load("patterns.yaml")["qr_disguise_families"]
    assert any(name.startswith(heldout + "_") for name in families)
