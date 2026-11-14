"""Live track record: did the bot's picks work after they were made?

Every trading night, after the back-test:
  1. record today's picks: 'rising' (tested breakout signals on leading stocks) and
     'dips' (tested dip signals), with the close and the Nifty close;
  2. score every open pick 10 and 21 trading days later: return minus the Nifty's,
     and whether the 2-ATR stop or 3-ATR target was hit first (using daily closes);
  3. write docs/track-record.json and a summary the bot and desk show.
Unlike the back-test this is out-of-sample by construction: picks are logged before the outcome exists.
"""
from __future__ import annotations

import json
import statistics as st
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def todays_picks(tech: dict, board: dict, model: dict, regime_up: bool | None) -> list:
    flag = "tested_weak" if regime_up is False else "tested"
    sigs = model.get("signals", {})
    dips = {"qdrop10", "qdrop", "qdrop25", "qdd", "qdd_hold"}
    warn = {"extended", "downtrend"}
    tested = {k for k, v in sigs.items() if v.get(flag) and k not in warn}
    status = {r["s"]: r.get("status") for r in board.get("rows", [])}
    out = []
    for sym, t in tech.get("stocks", {}).items():
        new = [k for k in t.get("new", []) if k in tested and k not in dips]
        if new and status.get(sym) in ("lead", "improve"):
            out.append({"kind": "rising", "sym": sym, "sig": new[0]})
        dn = [k for k in t.get("new", []) if k in tested and k in dips]
        if dn:
            out.append({"kind": "dips", "sym": sym, "sig": dn[0]})
    return out


def update(log: dict, day: str, picks: list, closes: dict, atr: dict, nifty: float) -> dict:
    """log: {"picks": [...]}. closes: {sym: close today}. Returns the updated log."""
    have = {(p["d"], p["sym"], p["kind"]) for p in log.get("picks", [])}
    for p in picks:
        if (day, p["sym"], p["kind"]) not in have and p["sym"] in closes:
            log.setdefault("picks", []).append({"d": day, **p, "c0": closes[p["sym"]], "n0": nifty, "atr": atr.get(p["sym"]),
                                                "path": [], "npath": []})
    for p in log.get("picks", []):
        if p["d"] == day or len(p["path"]) >= 21 or p["sym"] not in closes:
            continue
        p["path"].append(closes[p["sym"]])
        p["npath"].append(nifty)
        for h in (10, 21):
            if len(p["path"]) == h:
                p[f"x{h}"] = round((p["path"][-1] / p["c0"] - 1) - (nifty / p["n0"] - 1), 5)
        if p.get("atr") and "exit" not in p:
            if p["path"][-1] <= p["c0"] - 2 * p["atr"]:
                p["exit"] = "stop"
            elif p["path"][-1] >= p["c0"] + 3 * p["atr"]:
                p["exit"] = "target"
    return log


def summary(log: dict) -> dict:
    out = {}
    for kind in ("rising", "dips"):
        ps = [p for p in log.get("picks", []) if p["kind"] == kind]
        row = {"picks": len(ps), "open": sum(1 for p in ps if "x21" not in p)}
        for h in (10, 21):
            xs = [p[f"x{h}"] for p in ps if f"x{h}" in p]
            if xs:
                row[f"n{h}"] = len(xs)
                row[f"avg{h}"] = round(st.mean(xs), 5)
                row[f"beat{h}"] = round(sum(x > 0 for x in xs) / len(xs), 3)
        done = [p for p in ps if p.get("exit")]
        if done:
            row["target_first"] = round(sum(p["exit"] == "target" for p in done) / len(done), 3)
        out[kind] = row
    return out


def run(root: Path | None = None) -> str:
    import refresh as R
    root = Path(root or ROOT)
    tech = json.loads((root / "docs/tech-today.json").read_text(encoding="utf-8"))
    board = json.loads((root / "docs/n500.json").read_text(encoding="utf-8"))
    model = json.loads((root / "docs/tech-model.json").read_text(encoding="utf-8"))
    nset = R.read_nset((root / "docs/nse-terminal.html").read_text(encoding="utf-8"))
    nc = nset.get("idx", {}).get("Nifty 50", {}).get("c", [])
    up = nc[-1] > sum(nc[-200:]) / 200 if len(nc) >= 200 else None
    p = root / "docs/track-record.json"
    log = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"picks": []}
    day = tech.get("asof")
    if not day or log.get("last_day") == day:
        return "track record: already updated for " + str(day)
    closes = {s: t["c"] for s, t in tech.get("stocks", {}).items() if t.get("c")}
    atr = {s: t.get("atr") for s, t in tech.get("stocks", {}).items()}
    log = update(log, day, todays_picks(tech, board, model, up), closes, atr, nc[-1] if nc else 0)
    log["last_day"] = day
    log["summary"] = summary(log)
    p.write_text(json.dumps(log, separators=(",", ":")), encoding="utf-8")
    return f"track record: {len(log['picks'])} picks, summary {log['summary']}"


if __name__ == "__main__":
    print(run())
