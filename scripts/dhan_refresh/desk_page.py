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


def _branch(branch: str, path: str):
    import subprocess
    try:
        subprocess.run(["git", "-C", str(ROOT), "fetch", "-q", "origin", branch], check=True, capture_output=True, timeout=60)
        return json.loads(subprocess.run(["git", "-C", str(ROOT), "show", f"FETCH_HEAD:{path}"], check=True, capture_output=True, text=True).stdout)
    except Exception:
        return None


def _vm(v: dict) -> dict:
    """Value model, trimmed for the page: rules and today's active rules (non-empty only)."""
    if not v:
        return {}
    return {k: v.get(k) for k in ("asof", "from", "stocks", "split", "names", "method", "rules", "fundamental")} | \
        {"today": {s: x for s, x in (v.get("today") or {}).items() if x.get("on")}, "dd": {s: x.get("dd") for s, x in (v.get("today") or {}).items()}}


def build(out: Path) -> dict:
    import datetime as dt
    import refresh as R
    model = _j(ROOT / "docs/tech-model.json", {})
    nset = R.read_nset((ROOT / "docs/nse-terminal.html").read_text(encoding="utf-8"))
    c = nset.get("idx", {}).get("Nifty 50", {}).get("c", [])
    up = (c[-1] > sum(c[-200:]) / 200) if len(c) >= 200 else None
    board = _j(ROOT / "docs/n500.json", {"rows": []})
    files = sorted(glob.glob(str(ROOT / "data/options/*.json")))
    idx = {}
    for name in ("Nifty 50", "Nifty Bank", "India VIX"):
        cc = nset.get("idx", {}).get(name, {}).get("c", [])
        if len(cc) >= 2:
            idx[name] = {"c": cc[-1], "chg": cc[-1] / cc[-2] - 1}
    today_ist = dt.datetime.now(R.IST).date().isoformat()
    flow = _branch("live", "flow.json") or {}
    fstate = _branch("live", "flow-state.json") or {}
    sym_of = {str(r["sid"]): r["s"] for r in board.get("rows", []) if r.get("sid")}
    fs = {}
    if fstate.get("d") == today_ist:
        for sid, st_ in fstate.get("s", {}).items():
            if st_.get("tape"):
                fs[sym_of.get(sid, sid)] = {"tape": st_["tape"][-40:], "fp": st_.get("fp", {}), "path": st_.get("path", [])[-390:]}
    us_state = _branch("us-watch", "state.json") or {}
    n50 = {s: {"val": v.get("val"), "news": [{"time": x.get("time"), "title": x.get("title")} for x in (v.get("news") or [])[:3]],
               "filings": [{"time": x.get("time"), "title": x.get("title")} for x in (v.get("filings") or [])[:2]]}
           for s, v in nset.get("stocks", {}).items()}
    track = _j(ROOT / "docs/track-record.json", {})
    data = {"model": {k: model.get(k) for k in ("signals", "base", "names", "cutoff", "stocks", "asof")},
            "today": _j(ROOT / "docs/tech-today.json", {"stocks": {}}),
            "board": {"rows": [{k: r.get(k) for k in ("s", "status", "rank", "last", "score", "r1", "r5", "r21", "hi52", "ind")}
                               for r in board.get("rows", [])]},
            "auction": _j(ROOT / "docs/auction.json", {"symbols": {}}),
            "opts": _j(files[-1], {"rows": {}}) if files else {"rows": {}},
            "abt": _j(ROOT / "docs/auction-backtest.json", None), "regimeUp": up,
            "markets": _j(ROOT / "docs/markets.json", {}),
            "flow": flow if flow.get("d") == today_ist else {}, "flowState": {"s": fs},
            "track": {"summary": track.get("summary", {})}, "us": _j(ROOT / "docs/us-value.json", {"rows": []}),
            "usq": us_state.get("quotes", {}), "n50": n50, "idx": idx,
            "quant": _j(ROOT / "docs/quant.json", {}),
            "vm": _vm(_j(ROOT / "docs/value-model.json", {})), "pf": _j(ROOT / "docs/portfolio.json", {}),
            "usd": _j(ROOT / "docs/us-desk.json", {}),
            "nval": {s: {"sector": v.get("sector"), "val": v.get("val"),
                         "fund": {k: (nset.get("fund", {}).get("stk", {}).get(s) or {}).get(k) for k in ("pb", "rim_vp", "roe", "roe_n", "g_sus", "ke", "v_perm", "verdict")}}
                     for s, v in nset.get("stocks", {}).items()}}
    html = (ROOT / "docs/technical-desk.html").read_text(encoding="utf-8")
    blob = json.dumps(data, separators=(",", ":"), default=str).replace("</", "<\\/")
    html = re.sub(r"/\*DATA\*/.*?/\*DATA\*/", lambda m: "/*DATA*/" + blob + "/*DATA*/", html, count=1, flags=re.S)
    out.write_text(html, encoding="utf-8")
    return {"bytes": len(html), "stocks": len(data["today"].get("stocks", {})), "auction": len(data["auction"].get("symbols", {})),
            "live_flow": len(fs), "markets": bool(data["markets"])}


if __name__ == "__main__":
    print(build(Path(sys.argv[1])))
