"""Build docs/terminal.html (the Aj Trading Terminal artifact) from docs/terminal/*.json.

Separate from the Evidence Desk. Usage: python terminal_page.py [--out PATH]
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))


def _load(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def build(root: Path = ROOT) -> str:
    t = (Path(__file__).parent / "terminal_template.html").read_text(encoding="utf-8")
    d = root / "docs/terminal"
    bt = _load(d / "backtest.json")
    if bt:
        bt["trades"] = bt.get("trades", [])[-80:]
    meta = {"built": dt.datetime.now(IST).strftime("%Y-%m-%d %H:%M")}
    js = lambda o: json.dumps(o, separators=(",", ":")).replace("</", "<\\/")
    for k, v in (("BT", bt), ("MK", _load(d / "markets.json")), ("WL", _load(d / "watch.json")), ("META", meta)):
        t = t.replace(f"/*{k}*/null", js(v), 1)
    return t


if __name__ == "__main__":
    out = Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv else ROOT / "docs/terminal.html"
    out.write_text(build(), encoding="utf-8")
    print(f"wrote {out} ({out.stat().st_size // 1024} KB)")
