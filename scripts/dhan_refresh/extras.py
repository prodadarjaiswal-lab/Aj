"""Run the add-on Dhan jobs on demand (weekends included), with the shared Dhan session:
options snapshot (with gamma), auction levels from 1-minute bars, and the markets snapshot."""
from __future__ import annotations

import datetime as dt
import os
import sys
from pathlib import Path

import requests

import refresh as R


def all_symbols(root: Path) -> list:
    import json
    syms = list(R.read_nset((root / "docs/nse-terminal.html").read_text(encoding="utf-8"))["stocks"])
    syms += [r["s"] for r in json.loads((root / "docs/n500.json").read_text(encoding="utf-8")).get("rows", []) if r["s"] not in syms]
    return syms


def main() -> int:
    root = Path(sys.argv[sys.argv.index("--root") + 1]) if "--root" in sys.argv else Path("../..")
    cid, pin, sec = (os.environ[k] for k in ("DHAN_CLIENT_ID", "DHAN_PIN", "DHAN_TOTP_SECRET"))
    d = R.Dhan(cid, R.login(cid, pin, sec))
    scrip = requests.get(R.SCRIP_MASTER, timeout=60).text
    now = dt.datetime.now(R.IST)
    for name, fn in (("options", lambda: __import__("options_snapshot").save_snapshot(d, scrip, root)),
                     ("auction", lambda: __import__("auction").run(d, scrip, root, all_symbols(root))),
                     ("markets", lambda: __import__("markets").run(d, scrip, root, now))):
        try:
            print(name, fn())
        except Exception as e:
            print(f"{name} failed: {str(e)[:200]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
