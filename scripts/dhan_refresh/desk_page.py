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


def _chunk(key: str) -> str:
    c = next((ch for ch in key.upper() if ch.isalnum()), "_")
    return c if c.isalpha() else "0"


def _last_fii(f) -> str | None:
    import datetime as dt
    try:
        return max(dt.datetime.strptime(k, "%d-%b-%Y").date() for k in (f or {})).isoformat()
    except Exception:
        return None


def _index_charts(ch: dict, nset: dict) -> dict:
    """NIFTY and BANKNIFTY daily closes from the NSE terminal (Dhan), aligned to the chart's dates when possible."""
    s = ch.setdefault("s", {})
    for sym, name in (("NIFTY", "Nifty 50"), ("BANKNIFTY", "Nifty Bank")):
        ix = (nset.get("idx") or {}).get(name) or {}
        c = ix.get("c") or []
        if len(c) >= 60 and (sym not in s or len(s[sym].get("c", [])) < 60):
            s[sym] = {"c": [round(x, 1) for x in c[-250:]]}
    return ch


def _chart(ch: dict) -> dict:
    """1-year daily closes, sent as whole-rupee deltas from the first close to keep the page small (exact to 1 paisa
    is not needed for a chart); moving averages and volume are already sampled weekly."""
    out = {"d": ch.get("d", []), "s": {}}
    for sym, x in (ch.get("s") or {}).items():
        c = x.get("c") or []
        if not c:
            continue
        sc = 10 if c[-1] < 500 else 1
        out["s"][sym] = {"b": c[0], "k": sc, "x": [round((v - c[0]) * sc) for v in c],
                         **{k: x[k] for k in ("m50", "m200", "v") if x.get(k)}}
    return out


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
            "rs": _j(ROOT / "docs/research.json", {}),
            "jr": _j(ROOT / "docs/journal-review.json", {}),
            "nf": _j(ROOT / "docs/nse-feeds.json", {}),
            "qr": _j(ROOT / "docs/results.json", {}),
            "usmain": ["SPY", "QQQ"] + [k for k in _j(ROOT / "config/us_watch.json", {}) if not k.startswith("_")],
            "chart": _chart(_index_charts(_j(ROOT / "docs/chart-data.json", {}), nset)),
            "usw": {k: {"d": v["d"][-104:], "c": v["c"][-104:]} for k, v in _j(ROOT / "data/us-weekly.json", {}).items()},
            "nval": {s: {"sector": v.get("sector"), "val": v.get("val"),
                         "fund": {k: (nset.get("fund", {}).get("stk", {}).get(s) or {}).get(k) for k in ("pb", "rim_vp", "roe", "roe_n", "g_sus", "ke", "v_perm", "verdict")}}
                     for s, v in nset.get("stocks", {}).items()}}
    session = str(data["today"].get("asof") or board.get("asof") or "")[:10]
    oq = data["opts"]
    usw_last = max((v["d"][-1] for v in data["usw"].values() if v.get("d")), default=None)
    data["fresh"] = {"session": session, "rows": [
        ["Technical signals (Nifty 500)", data["today"].get("asof"), f"{len(data['today'].get('stocks', {}))} stocks", "daily"],
        ["Signal back-test", model.get("asof"), f"{model.get('stocks')} stocks, 6 years", "daily"],
        ["Nifty 500 ranking", board.get("asof"), f"{len(board.get('rows', []))} stocks", "daily"],
        ["Order flow and auction (1-minute bars)", data["auction"].get("asof"), f"{len(data['auction'].get('symbols', {}))} symbols", "daily"],
        ["Order-flow swing test", (data["abt"] or {}).get("asof"), "Nifty 50, 12 months", "weekly"],
        ["Option chains and gamma", oq.get("asof") or oq.get("date") or (Path(files[-1]).stem if files else None), f"{len(oq.get('rows', {}))} underlyings", "daily"],
        ["Monte Carlo and VaR", data["quant"].get("asof"), f"{len(data['quant'].get('mc', {}))} stocks", "daily"],
        ["Investor-rule back-test", data["vm"].get("asof"), f"{data['vm'].get('stocks')} stocks", "daily"],
        ["Portfolio fit", data["pf"].get("asof"), f"{len(data['pf'].get('fit', {}))} stocks", "daily"],
        ["Markets (MCX, movers)", str(data["markets"].get("asof") or "")[:16], "commodities and movers", "daily"],
        ["Price charts", (data["chart"].get("d") or [None])[-1], f"{len(data['chart'].get('s', {}))} stocks", "daily"],
        ["Prices in the NSE terminal", str(nset.get("asof", ""))[:16], f"{len(nset.get('stocks', {}))} Nifty 50 stocks", "daily"],
        ["Fundamentals model (NSE terminal)", (nset.get("fund") or {}).get("asof"), "valuation factors", "monthly"],
        ["US fundamentals (FMP)", data["us"].get("asof"), f"{len(data['us'].get('rows', []))} stocks", "weekly"],
        ["US weekly history", usw_last, f"{len(data['usw'])} of {len(data['us'].get('rows', [])) + 1} symbols", "weekly"],
        ["Filings (NSE, all Nifty 500)", data["nf"].get("filings_asof"), f"{len(data['nf'].get('filings', {}))} stocks with filings in 5 days", "daily"],
        ["Results and board-meeting calendar (NSE)", data["nf"].get("events_asof"), f"{len(data['nf'].get('events', {}))} stocks in the next 21 days", "daily"],
        ["Quarterly results (NSE XBRL)", str(data["qr"].get("asof") or "")[:10] or None, f"{len(data['qr'].get('stocks', {}))} stocks", "weekly"],
        ["FII / DII flows (NSE)", max(data["nf"].get("fiidii") or {"": 0}) or None, "daily cash-market flows", "daily"],
        ["Global markets (NSE terminal)", str((nset.get("glob") or {}).get("made") or "")[:10], "old Yahoo series; not refreshed", "weekly"],
        ["Macro (NSE terminal)", ((nset.get("macro") or {}).get("usdinr") or [[None]])[-1][0], "monthly series", "monthly"],
        ["Research profiles and Dhan fundamentals (Nifty 500)", data["rs"].get("fund_asof"), f"{len(data['rs'].get('stocks', {}))} stocks", "daily"],
        ["Live order flow", flow.get("t") if flow.get("d") == today_ist else "market closed", "market hours only", "live"]]}
    html = (ROOT / "docs/technical-desk.html").read_text(encoding="utf-8")
    blob = json.dumps(data, separators=(",", ":"), default=str).replace("</", "<\\/")
    html = re.sub(r"/\*DATA\*/.*?/\*DATA\*/", lambda m: "/*DATA*/" + blob + "/*DATA*/", html, count=1, flags=re.S)
    # per-stock detail goes to small files the page loads when a stock is opened (keeps the page light on a phone)
    chunks = {}
    for key, a in (data["auction"].get("symbols") or {}).items():
        chunks.setdefault(_chunk(key), {}).setdefault(key, {})["a"] = a
    for sym, x in (data["chart"].get("s") or {}).items():
        chunks.setdefault(_chunk(sym), {}).setdefault(sym, {})["ch"] = x
    for sym, f in (data["pf"].get("fit") or {}).items():
        if f.get("c"):
            chunks.setdefault(_chunk(sym), {}).setdefault(sym, {})["fc"] = f["c"]
    keep = ("date", "close", "swing", "note")
    data["auction"] = {"asof": data["auction"].get("asof"),
                       "symbols": {k: {f: a[f] for f in keep if f in a} for k, a in (data["auction"].get("symbols") or {}).items()}}
    data["chart"] = {"d": data["chart"].get("d", [])}
    data["pf"] = {**data["pf"], "fit": {k: {f: v for f, v in x.items() if f != "c"} for k, x in (data["pf"].get("fit") or {}).items()}}
    data["chunks"] = sorted(chunks)
    blob = json.dumps(data, separators=(",", ":"), default=str).replace("</", "<\\/")
    html = re.sub(r"/\*DATA\*/.*?/\*DATA\*/", lambda m: "/*DATA*/" + blob + "/*DATA*/", html, count=1, flags=re.S)
    ddir = out.parent / "d"
    ddir.mkdir(parents=True, exist_ok=True)
    for old_f in ddir.glob("*.json"):
        old_f.unlink()
    for k, v in chunks.items():
        (ddir / f"{k}.json").write_text(json.dumps(v, separators=(",", ":"), default=str), encoding="utf-8")
    out.write_text(html, encoding="utf-8")
    return {"bytes": len(html), "detail_files": len(chunks), "stocks": len(data["today"].get("stocks", {})), "auction": len(data["auction"].get("symbols", {})),
            "live_flow": len(fs), "markets": bool(data["markets"])}


if __name__ == "__main__":
    out = Path(sys.argv[1])
    print(build(out))
    # publish: the page plus every detail file, with root = the page's folder
    print("PUBLISH root=" + str(out.parent) + " files=" + json.dumps({f"d/{f.name}": f"d/{f.name}" for f in sorted((out.parent / "d").glob("*.json"))}))
