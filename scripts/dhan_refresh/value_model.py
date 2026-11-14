"""Investor (value) back-test on Dhan daily prices, by market condition.

The question it answers: "is this a good time to invest in this stock for 6-12 months?"
Every candidate rule is tested on 6 years of Dhan history for today's Nifty 500, sampled once a month,
separately for rising markets (Nifty above its 200-day average) and weak markets (below it).
A rule counts only if it beat the average stock over the next 12 months in BOTH halves of the history
and the overall lift is statistically distinct from zero after allowing for overlapping windows.

It also carries the NSE terminal's fundamental factor test (book/price, residual income, earnings quality ...),
which uses quarterly results and covers the Nifty 50 from 2023.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

H = {"6m": 126, "12m": 252}
STEP = 21                       # one sample a month
NAMES = {
    "dd30": "30%+ below its 52-week high",
    "fallen_leader": "30%+ below its high after beating the Nifty the year before",
    "near_lo52": "Within 10% of its 52-week low",
    "lt_loser": "Worst 20% over 2 years (long-term reversal)",
    "lowvol": "Calmest 20% (lowest 1-year volatility)",
    "mom12": "Strongest 20% over 12 months, skipping the last month",
    "recovered": "Back above its 200-day after a 30% fall (last 6 months)",
    "rs6": "Strongest 20% against the Nifty over 6 months, skipping the last month",
    "accum": "Top 20% by accumulation: up-day volume vs down-day volume, 50 days",
    "near_hi": "Within 5% of its 52-week high (the 52-week-high effect)",
    "stack": "Trend stack: above a rising 200-day, 50-day above 200-day",
    "lt_winner": "Best 20% over 2 years (control)",
}
FUND_PASS_T = 2.0               # terminal's fundamental factors: |t| >= 2 at 12 months, positive information coefficient


def _ma(c, n, i):
    return sum(c[i - n + 1:i + 1]) / n if i >= n - 1 else None


def _sd(r):
    if len(r) < 2:
        return 0.0
    m = sum(r) / len(r)
    return math.sqrt(sum((x - m) ** 2 for x in r) / (len(r) - 1))


def features(c: list, i: int, v: list | None = None, nc: list | None = None) -> dict | None:
    """Raw per-stock measures at bar i (needs 504 bars of history)."""
    if i < 504 or not c[i]:
        return None
    hi = max(c[i - 251:i + 1])
    lo = min(c[i - 251:i + 1])
    rets = [c[k] / c[k - 1] - 1 for k in range(i - 251, i + 1) if c[k - 1]]
    m200 = _ma(c, 200, i)
    m200p = _ma(c, 200, i - 21)
    m50 = _ma(c, 50, i)
    acc = None
    if v and len(v) > i and all(v[k] is not None for k in range(i - 50, i + 1)):
        up = sum(v[k] for k in range(i - 49, i + 1) if c[k] > c[k - 1])
        dn = sum(v[k] for k in range(i - 49, i + 1) if c[k] < c[k - 1])
        acc = up / dn if dn else None
    rs6 = (c[i - 21] / c[i - 147] - 1) - ((nc[i - 21] / nc[i - 147] - 1) if nc else 0)
    return {"acc": acc, "rs6": rs6, "stack": bool(m200 and m200p and m50 and c[i] > m200 > m200p and m50 > m200),
            "dd": c[i] / hi - 1, "lo": c[i] / lo - 1, "r2y": c[i] / c[i - 504] - 1, "r1y_prev": c[i - 252] / c[i - 504] - 1,
            "vol": _sd(rets) * math.sqrt(252), "mom": c[i - 21] / c[i - 252] - 1,
            "fell6": min(c[i - 125:i + 1]) / max(c[i - 377:i + 1]) - 1, "above200": bool(m200 and c[i] > m200)}


def flags(f: dict, nifty_r1y_prev: float, q: dict) -> set:
    """Rules active for one stock at one date. q holds the cross-section quintile cut-offs for that date."""
    s = set()
    if f["dd"] <= -0.30:
        s.add("dd30")
        if f["r1y_prev"] > nifty_r1y_prev:
            s.add("fallen_leader")
    if f["lo"] <= 0.10:
        s.add("near_lo52")
    if f["r2y"] <= q["r2y_lo"]:
        s.add("lt_loser")
    if f["r2y"] >= q["r2y_hi"]:
        s.add("lt_winner")
    if f["vol"] <= q["vol_lo"]:
        s.add("lowvol")
    if f["mom"] >= q["mom_hi"]:
        s.add("mom12")
    if f.get("rs6") is not None and f["rs6"] >= q.get("rs6_hi", 9):
        s.add("rs6")
    if f.get("acc") is not None and f["acc"] >= q.get("acc_hi", 9):
        s.add("accum")
    if f["dd"] >= -0.05:
        s.add("near_hi")
    if f.get("stack"):
        s.add("stack")
    if f["above200"] and f["fell6"] <= -0.30:
        s.add("recovered")
    return s


def _q(vals, p):
    v = sorted(vals)
    return v[min(len(v) - 1, max(0, int(p * len(v))))] if v else 0.0


def cross_cuts(feats: list) -> dict:
    return {"r2y_lo": _q([f["r2y"] for f in feats], 0.2), "r2y_hi": _q([f["r2y"] for f in feats], 0.8),
            "vol_lo": _q([f["vol"] for f in feats], 0.2), "mom_hi": _q([f["mom"] for f in feats], 0.8),
            "rs6_hi": _q([f["rs6"] for f in feats], 0.8),
            "acc_hi": _q([f["acc"] for f in feats if f.get("acc") is not None], 0.8) if any(f.get("acc") is not None for f in feats) else 9}


def _bad_moves(c):
    return [k for k in range(1, len(c)) if c[k - 1] and abs(c[k] / c[k - 1] - 1) > 0.40]


def backtest(data: dict, nifty: dict) -> dict:
    """data: {sym: {d, c}}; nifty: {d, c}. Monthly samples; lift = rule's average excess return minus the
    average stock's on the same dates."""
    nd, nc = nifty["d"], nifty["c"]
    npos = {d: k for k, d in enumerate(nd)}
    n200 = [_ma(nc, 200, k) for k in range(len(nc))]
    aligned = {}
    for s, o in data.items():
        m = dict(zip(o["d"], o["c"]))
        c = [m.get(d) for d in nd]
        if sum(x is not None for x in c) < 600:
            continue
        for k in range(1, len(c)):                     # carry forward a missing day (holiday / suspension)
            if c[k] is None:
                c[k] = c[k - 1]
        mv = dict(zip(o["d"], o.get("v") or [])) if o.get("v") else {}
        vv = [mv.get(d) for d in nd] if mv else None
        aligned[s] = (c, _bad_moves([x or 0 for x in c]), vv)
    dates = list(range(504, len(nd) - 1, STEP))
    half = dates[len(dates) // 2] if dates else 0
    # per (rule, horizon, regime): list of (date_index, lift)
    per = {(k, h, r): [] for k in NAMES for h in H for r in ("up", "weak")}
    cases = {(k, h, r): 0 for k in NAMES for h in H for r in ("up", "weak")}
    for i in dates:
        feats = {}
        for s, (c, bad, vv) in aligned.items():
            if c[i - 504] is None:
                continue
            f = features(c, i, vv, nc)
            if f:
                feats[s] = f
        if len(feats) < 50:
            continue
        cuts = cross_cuts(list(feats.values()))
        nprev = nc[i - 252] / nc[i - 504] - 1
        regime = "up" if n200[i] and nc[i] > n200[i] else "weak"
        for h, hd in H.items():
            if i + hd >= len(nd):
                continue
            nret = nc[i + hd] / nc[i] - 1
            ex, by = {}, {k: [] for k in NAMES}
            for s, f in feats.items():
                c, bad, _ = aligned[s]
                if bad and any(i - 252 <= b <= i + hd for b in bad):
                    continue
                ex[s] = c[i + hd] / c[i] - 1 - nret
                for k in flags(f, nprev, cuts):
                    by[k].append(ex[s])
            if not ex:
                continue
            base = sum(ex.values()) / len(ex)
            for k, xs in by.items():
                if xs:
                    per[(k, h, regime)].append((i, sum(xs) / len(xs) - base))
                    cases[(k, h, regime)] += len(xs)
    out = {"asof": nd[-1], "from": nd[0], "stocks": len(aligned), "split": nd[half] if dates else None, "names": NAMES,
           "rules": {}}
    for k in NAMES:
        res = {}
        for h, hd in H.items():
            for r in ("up", "weak"):
                xs = per[(k, h, r)]
                lifts = [x for _, x in xs]
                a = [x for i, x in xs if i < half]
                b = [x for i, x in xs if i >= half]
                m = sum(lifts) / len(lifts) if lifts else None
                overlap = max(1, hd // STEP)
                t = (m / (_sd(lifts) / math.sqrt(len(lifts))) / math.sqrt(overlap)) if len(lifts) > 2 and _sd(lifts) > 0 else 0.0
                res[f"{h}_{r}"] = {"lift": None if m is None else round(m, 4), "t": round(t, 2), "dates": len(lifts),
                                   "cases": cases[(k, h, r)],
                                   "first": round(sum(a) / len(a), 4) if a else None, "second": round(sum(b) / len(b), 4) if b else None,
                                   "hit": round(sum(x > 0 for x in lifts) / len(lifts), 2) if lifts else None}
        out["rules"][k] = res
    return score(out)


def score(out: dict) -> dict:
    """Pass rule, per market condition: at the 6- or 12-month horizon, positive lift in both halves of the history,
    t >= 2 after the overlap adjustment, 100+ cases. The horizon that passed is recorded (6 months first)."""
    for k, res in out.get("rules", {}).items():
        for r in ("up", "weak"):
            res[f"tested_{r}"], res[f"h_{r}"] = False, None
            for h in ("6m", "12m"):
                x = res.get(f"{h}_{r}") or {}
                if (k != "lt_winner" and x.get("lift") is not None and x["lift"] > 0 and x.get("t", 0) >= 2
                        and (x.get("first") or 0) > 0 and (x.get("second") or 0) > 0 and x.get("cases", 0) >= 100):
                    res[f"tested_{r}"], res[f"h_{r}"] = True, h
                    break
    out["method"] = ("Monthly samples on today's Nifty 500 (survivorship bias), Dhan daily closes. Lift = the rule's average "
                     "excess return over the Nifty minus the average stock's, same dates. Passes at the 6- or 12-month horizon "
                     "only if the lift is positive in both halves of the history and t >= 2 after allowing for overlapping "
                     "windows; needs 100+ cases. Weak-market samples are few (the Nifty was rarely below its 200-day).")
    return out


def today(data: dict, nifty: dict) -> dict:
    """Rules active on the last bar, per stock."""
    nc = nifty["c"]
    i = len(nc) - 1
    feats = {}
    for s, o in data.items():
        m = dict(zip(o["d"], o["c"]))
        c = [m.get(d) for d in nifty["d"]]
        for k in range(1, len(c)):
            if c[k] is None:
                c[k] = c[k - 1]
        if None in c[i - 504:i + 1] or len(c) <= 504:
            continue
        mv = dict(zip(o["d"], o.get("v") or [])) if o.get("v") else {}
        f = features(c, i, [mv.get(d) for d in nifty["d"]] if mv else None, nc)
        if f:
            feats[s] = f
    if not feats:
        return {}
    cuts = cross_cuts(list(feats.values()))
    nprev = nc[i - 252] / nc[i - 504] - 1
    return {s: {"on": sorted(flags(f, nprev, cuts)), "dd": round(f["dd"], 3), "r2y": round(f["r2y"], 3),
                "vol": round(f["vol"], 3)} for s, f in feats.items()}


def fundamentals(nset: dict) -> dict:
    """The NSE terminal's fundamental factor back-test (quarterly results), and today's quintiles for the factors
    that passed. Higher quintile = cheaper / better on that factor (5 = best 20%)."""
    fund = nset.get("fund") or {}
    bt = fund.get("bt_stk") or {}
    keymap = {"B/P": lambda x: 1 / x["pb"] if x.get("pb") else None,
              "Residual-income V/P": lambda x: x.get("rim_vp"),
              "E/P (trailing)": lambda x: x["eps"] / x["P"] if x.get("eps") and x.get("P") else None,
              "Warranted P/B gap (ROE-g)/(ke-g)": lambda x: x.get("wpb_gap")}
    tests, passed = [], []
    for name, h in bt.items():
        r = (h or {}).get("12") or {}
        ok = bool(r.get("ic") is not None and r["ic"] > 0 and (r.get("t") or 0) >= FUND_PASS_T)
        tests.append({"name": name, "ic": r.get("ic"), "t": r.get("t"), "hit": r.get("hit"), "n": r.get("n"),
                      "from": r.get("start"), "to": r.get("end"), "passed": ok})
        if ok and name in keymap:
            passed.append(name)
    stk = fund.get("stk") or {}
    quint = {}
    for name in passed:
        vals = {s: keymap[name](x) for s, x in stk.items()}
        vals = {s: v for s, v in vals.items() if v is not None}
        order = sorted(vals, key=vals.get)
        for j, s in enumerate(order):
            quint.setdefault(s, {})[name] = 1 + int(5 * j / len(order))
    return {"asof": fund.get("asof"), "tests": tests, "passed": passed, "quintiles": quint,
            "note": "Nifty 50, monthly, 12-month forward returns, from the NSE terminal's quarterly-results history (2023 on)."}


def run(data: dict, nifty: dict, root: Path, nset: dict) -> str:
    res = backtest(data, nifty)
    res["today"] = today(data, nifty)
    res["fundamental"] = fundamentals(nset)
    (root / "docs/value-model.json").write_text(json.dumps(res, separators=(",", ":")), encoding="utf-8")
    up = [k for k, r in res["rules"].items() if r["tested_up"]]
    wk = [k for k, r in res["rules"].items() if r["tested_weak"]]
    return (f"value model: {res['stocks']} stocks; passes rising {up or 'none'}, weak {wk or 'none'}; "
            f"fundamental factors passed {res['fundamental']['passed'] or 'none'}")
