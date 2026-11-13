"""Build the Technical Desk page: docs/technical-desk.html with today's data embedded.

  python desk_page.py OUT.html        (reads docs/*.json from the repo)
"""
from __future__ import annotations

import glob
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _j(p, default):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return default


def build(out: Path) -> dict:
    import refresh as R
    model = _j(ROOT / "docs/tech-model.json", {})
    nset = R.read_nset((ROOT / "docs/nse-terminal.html").read_text(encoding="utf-8"))
    c = nset.get("idx", {}).get("Nifty 50", {}).get("c", [])
    up = (c[-1] > sum(c[-200:]) / 200) if len(c) >= 200 else None
    board = _j(ROOT / "docs/n500.json", {"rows": []})
    files = sorted(glob.glob(str(ROOT / "data/options/*.json")))
    data = {"model": {k: model.get(k) for k in ("signals", "base", "names", "cutoff", "stocks", "asof")},
            "today": _j(ROOT / "docs/tech-today.json", {"stocks": {}}),
            "board": {"rows": [{k: r.get(k) for k in ("s", "status", "rank", "last")} for r in board.get("rows", [])]},
            "auction": _j(ROOT / "docs/auction.json", {"symbols": {}}),
            "opts": _j(files[-1], {"rows": {}}) if files else {"rows": {}},
            "abt": _j(ROOT / "docs/auction-backtest.json", None), "regimeUp": up}
    for v in data["auction"].get("symbols", {}).values():
        v.pop("hist", None)
    html = (ROOT / "docs/technical-desk.html").read_text(encoding="utf-8")
    blob = json.dumps(data, separators=(",", ":")).replace("</", "<\\/")
    html = re.sub(r"/\*DATA\*/.*?/\*DATA\*/", lambda m: "/*DATA*/" + blob + "/*DATA*/", html, count=1, flags=re.S)
    out.write_text(html, encoding="utf-8")
    return {"bytes": len(html), "stocks": len(data["today"].get("stocks", {}))}


if __name__ == "__main__":
    print(build(Path(sys.argv[1])))
