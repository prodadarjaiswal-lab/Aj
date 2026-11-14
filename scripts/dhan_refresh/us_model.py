"""US stocks for the desk.

Prices: Dhan's US feed (us-watch branch: live quotes and the daily closes it records).
History: Dhan has no US history API. The base is Alpha Vantage's split-adjusted WEEKLY series (free; 10 years,
data/us-weekly.json, refreshed on Saturdays), extended week by week with Dhan's recorded daily closes.
Trend, Monte Carlo and VaR for US stocks are therefore computed on weekly data and labelled that way.
Options: neither Dhan nor a free source has US option chains (Alpha Vantage's are premium), so none are shown.
Fundamentals: docs/us-value.json (FMP).
"""
from __future__ import annotations

import datetime as dt
import json
import math
import os
import subprocess
from pathlib import Path

FOREIGN_CAP = 0.25          # ASSUMED cap on foreign equity (owner's notes give no number; FX risk applies)


def _show(root: Path, branch: str, path: str):
    try:
        subprocess.run(["git", "-C", str(root), "fetch", "-q", "origin", branch], check=True, capture_output=True, timeout=60)
        return json.loads(subprocess.run(["git", "-C", str(root), "show", f"FETCH_HEAD:{path}"], check=True,
                                         capture_output=True, text=True).stdout)
    except Exception:
        return None


def _rsi(c, n=14):
    if len(c) <= n:
        return None
    g = l = 0.0
    for k in range(1, n + 1):
        ch = c[k] - c[k - 1]
        g, l = g + max(ch, 0), l + max(-ch, 0)
    g, l = g / n, l / n
    for k in range(n + 1, len(c)):
        ch = c[k] - c[k - 1]
        g, l = (g * (n - 1) + max(ch, 0)) / n, (l * (n - 1) + max(-ch, 0)) / n
    return 100.0 if l == 0 else 100 - 100 / (1 + g / l)


def readout(c: list, bench: list | None) -> dict:
    out = {"n": len(c)}
    if len(c) >= 50:
        out["vs50"] = round((c[-1] / (sum(c[-50:]) / 50) - 1) * 100, 1)
    if len(c) >= 200:
        out["vs200"] = round((c[-1] / (sum(c[-200:]) / 200) - 1) * 100, 1)
    if len(c) >= 15:
        out["rsi"] = round(_rsi(c[-200:]), 1)
    if len(c) >= 252:
        out["hi52"] = round((c[-1] / max(c[-252:]) - 1) * 100, 1)
    if bench and len(c) >= 64 and len(bench) >= 64:
        out["rs3"] = round(((c[-1] / c[-64]) - (bench[-1] / bench[-64])) * 100, 1)
    return out


def extend_weekly(w: dict | None, dhan_days: dict | None) -> dict:
    """Weekly closes (Friday dates) plus Dhan's daily closes for later days, folded into their week."""
    d, c = list((w or {}).get("d", [])), list((w or {}).get("c", []))
    last = d[-1] if d else ""
    wk = lambda x: dt.date.fromisoformat(x).isocalendar()[:2]
    for day in sorted(dhan_days or {}):
        if day <= last:
            continue
        px = dhan_days[day][2]
        if d and wk(d[-1]) == wk(day):
            d[-1], c[-1] = day, px
        else:
            d.append(day)
            c.append(px)
    return {"d": d, "c": c}


def weekly_readout(c: list, bench: list | None) -> dict:
    out = {"n": len(c), "basis": "weekly"}
    if len(c) >= 10:
        out["vs50"] = round((c[-1] / (sum(c[-10:]) / 10) - 1) * 100, 1)          # 10 weeks ~ 50 days
    if len(c) >= 40:
        out["vs200"] = round((c[-1] / (sum(c[-40:]) / 40) - 1) * 100, 1)         # 40 weeks ~ 200 days
    if len(c) >= 30:
        out["rsi"] = round(_rsi(c[-120:]), 1)                                     # RSI(14) on weeks
    if len(c) >= 52:
        out["hi52"] = round((c[-1] / max(c[-52:]) - 1) * 100, 1)
    if bench and len(c) >= 14 and len(bench) >= 14:
        out["rs3"] = round(((c[-1] / c[-14]) - (bench[-1] / bench[-14])) * 100, 1)
    return out


def weekly_mc(c: list, weeks: int = 4, n: int = 10000, block: int = 4, lookback: int = 260, seed: int = 7) -> dict | None:
    """Block bootstrap of the last 5 years of weekly log returns, 4 weeks ahead (about 21 trading days)."""
    import numpy as np
    if len(c) < 60:
        return None
    r = np.diff(np.log(np.asarray(c[-(lookback + 1):], float)))
    rng = np.random.default_rng(seed)
    nb = -(-weeks // block)
    starts = rng.integers(0, len(r) - block + 1, size=(n, nb))
    paths = np.concatenate([r[starts[:, k:k + 1] + np.arange(block)] for k in range(nb)], axis=1)[:, :weeks]
    cum = c[-1] * np.exp(np.cumsum(paths, axis=1))
    end = cum[:, -1]
    q = lambda a, p: float(np.percentile(a, p))
    fan = [[c[-1]] * 5] + [[round(q(cum[:, k], p), 2) for p in (5, 25, 50, 75, 95)] for k in range(weeks)]
    return {"last": c[-1], "p5": q(end, 5), "p25": q(end, 25), "p50": q(end, 50), "p75": q(end, 75), "p95": q(end, 95),
            "p_up": float((end > c[-1]).mean()), "fan": fan, "basis": f"weekly, {len(r)} weeks resampled in {block}-week blocks"}


def weekly_var(c: list, value: float = 100000.0) -> dict | None:
    import statistics as stt
    if len(c) < 60:
        return None
    r = [c[k] / c[k - 1] - 1 for k in range(max(1, len(c) - 260), len(c))]
    srt = sorted(r)
    out = {}
    for lvl, z in (("95", 1.645), ("99", 2.326)):
        k = int((1 - int(lvl) / 100) * len(srt))
        hist = -srt[k]
        tail = srt[:max(1, k)]
        out[lvl] = {"hist_1w": round(hist * value), "param_1w": round((z * stt.pstdev(r) - stt.mean(r)) * value),
                    "es_1w": round(-sum(tail) / len(tail) * value)}
    out["weeks"] = len(r)
    return out


def run(root: Path) -> str:
    rows = (json.loads((root / "docs/us-value.json").read_text(encoding="utf-8")) if (root / "docs/us-value.json").exists() else {}).get("rows", [])
    st = _show(root, "us-watch", "state.json") or {}
    q, dh = st.get("quotes") or {}, st.get("hist") or {}
    syms = list(dict.fromkeys([r["s"] for r in rows if r.get("s")] + list(q)))
    try:
        weekly = json.loads((root / "data/us-weekly.json").read_text(encoding="utf-8"))
    except Exception:
        weekly = {}
    notes = []
    missing = [x for x in syms if x not in weekly]
    if missing:
        notes.append(f"No weekly history yet for {', '.join(missing)} (Alpha Vantage, 25 calls a day: added over the next days).")
    bench = extend_weekly(weekly.get("SPY"), dh.get("SPY"))["c"]
    try:
        pf = json.loads((root / "docs/portfolio.json").read_text(encoding="utf-8"))
    except Exception:
        pf = {}
    us_share = (pf.get("summary") or {}).get("us_share") or 0
    out = {}
    for s in syms:
        h = extend_weekly(weekly.get(s), dh.get(s))
        c = h["c"]
        x = {"weeks": len(c), "from": h["d"][0] if h["d"] else None, "to": h["d"][-1] if h["d"] else None,
             "src": ("Alpha Vantage weekly + Dhan closes" if s in weekly else "Dhan closes") if c else None,
             "tech": weekly_readout(c, bench)}
        try:
            m = weekly_mc(c)
            if m:
                x["mc"] = m
            v = weekly_var(c)
            if v:
                x["var_w"] = v
        except Exception as e:
            notes.append(f"{s} risk: {str(e)[:60]}")
        held = s in (pf.get("weights") or {})
        x["fit"] = {"held": held, "us_share": us_share, "cap": FOREIGN_CAP,
                    "v": "no" if us_share >= FOREIGN_CAP and not held else "partly" if us_share >= FOREIGN_CAP * 0.8 else "suits",
                    "why": [f"US stocks are {us_share * 100:.0f}% of your portfolio (cap {FOREIGN_CAP * 100:.0f}%, ASSUMED); "
                            "returns also move with USD/INR"]}
        out[s] = x
    res = {"asof": dt.date.today().isoformat(), "stocks": out, "notes": notes,
           "sources": "Prices: Dhan US feed. History: Alpha Vantage weekly (split-adjusted) + Dhan's recorded closes. No US options source."}
    (root / "docs/us-desk.json").write_text(json.dumps(res, separators=(",", ":")), encoding="utf-8")
    return f"us model: {len(out)} stocks, {sum(1 for v in out.values() if v.get('mc'))} with risk models; {'; '.join(notes)[:300]}"


if __name__ == "__main__":
    print(run(Path(__file__).resolve().parents[2]))
