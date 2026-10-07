"""Rotate the API's JWT signing key: make a new key, put it first in the keyring, keep the previous key(s) for verifying.

    python scripts/rotate_jwt_key.py                              # reads the current keyring from $JWT_KEYS (if any)
    python scripts/rotate_jwt_key.py --current-file D:/secrets/uvera_jwt_keys --write D:/secrets/uvera_jwt_keys
    python scripts/rotate_jwt_key.py --keep 0                     # drop every old key (logs everybody out)

Prints the new keyring as one line, `JWT_KEYS=kid:secret,kid:secret`, for your secret store (platform secret, an
environment variable, or a file outside the repository named by JWT_KEYS_FILE). It never writes inside this repository.

Rotation in production (docs/security.md):
 1. run this, store the new line, restart the API: new tokens are signed with the new key, old tokens still verify;
 2. after the longest token lifetime (12 h), run it again with --keep 0 (or delete the old entry): tokens signed with the
    retired key now get 401.
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import secrets
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def parse(spec: str) -> list[tuple[str, str]]:
    out = []
    for line in spec.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.upper().startswith("JWT_KEYS="):
            line = line[len("JWT_KEYS="):]
        for part in line.split(","):
            kid, sep, secret = part.strip().partition(":")
            if sep and kid and secret:
                out.append((kid.strip(), secret.strip()))
    return out


def inside_repo(path: Path) -> bool:
    try:
        path.resolve().relative_to(ROOT.resolve())
        return True
    except ValueError:
        return False


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--current-file", help="file with the current keyring (default: the JWT_KEYS environment variable)")
    ap.add_argument("--keep", type=int, default=1, help="how many previous keys stay valid for verification (default 1)")
    ap.add_argument("--write", help="also write the new keyring to this file (must be outside the repository)")
    ap.add_argument("--kid", help="key id for the new key (default: k<UTC date>-<random>)")
    args = ap.parse_args(argv)

    if args.current_file and Path(args.current_file).exists():
        current = parse(Path(args.current_file).read_text(encoding="utf-8"))
    else:
        current = parse(os.environ.get("JWT_KEYS", ""))
    kid = args.kid or f"k{dt.datetime.now(dt.UTC):%Y%m%d}-{secrets.token_hex(2)}"
    if any(k == kid for k, _ in current):
        print(f"ERROR: key id {kid} already exists", file=sys.stderr)
        return 2
    new = [(kid, secrets.token_urlsafe(48))] + current[: max(0, args.keep)]
    line = "JWT_KEYS=" + ",".join(f"{k}:{s}" for k, s in new)

    if args.write:
        target = Path(args.write).expanduser()
        if inside_repo(target):
            print("ERROR: refusing to write signing keys inside the repository; choose a path outside it", file=sys.stderr)
            return 2
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_suffix(target.suffix + ".tmp")
        tmp.write_text(line + "\n", encoding="utf-8")
        try:
            os.chmod(tmp, 0o600)  # owner-only where the file system supports it
        except OSError:
            pass
        os.replace(tmp, target)
        print(f"wrote the keyring to {target} (set JWT_KEYS_FILE={target})", file=sys.stderr)
    print(f"new signing key: {kid}; still verifying: {', '.join(k for k, _ in new[1:]) or 'none'}", file=sys.stderr)
    print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
