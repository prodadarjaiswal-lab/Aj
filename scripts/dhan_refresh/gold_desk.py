"""Gold Desk: one page for gold only, rebuilt from Dhan daily closes once a day.

Research software, not advice. Never places orders.

Data
  history   docs/gold/history.json: weekly gold in $/oz and Rs/10 g from 2000 (Rs from Dec 2003), silver, Nifty,
            plus the drawdown, Nifty-fall and portfolio studies, all copied from the Gold Desk artifact of 7 Nov 2026.
  daily     docs/gold/daily.json, from Dhan, kept and extended every run:
            GOLDBEES (NSE gold ETF) daily closes back to 2009, the nearest MCX GOLD future's daily closes,
            and the Nifty 50's daily closes.
Level check (before joining the two)
  GOLDBEES is in rupees per unit, not per 10 g, so it is scaled by k = median of (MCX GOLD close / GOLDBEES close)
  over the last 60 days both have. The typical daily gap from k must be 1.5% or less, else the page says the check
  failed. The old weekly Rs history is the international price in rupees (no import duty), so for the long chart it
  is multiplied by the domestic premium on the last week it shares with the daily series.
Metrics (same rules as the Trading Terminal's Analyze tab, gold has no earnings so the 1-year view is trend only)
  50/200-day averages, RSI 14, MACD 12/26/9, Bollinger 20/2, returns, distance from the 52-week high and from the
  all-time high, yearly volatility.
  3 months : above 50-day, MACD above signal, up over 3 months, beating the Nifty over 3 months, RSI 40-70
  6 months : above 200-day, 50-day above 200-day, up over 6 months, within 20% of the 52-week high
  1 year   : above 200-day, 50-day above 200-day, up over 1 year, within 15% of the 52-week high
  Good to buy when 75% or more of the checks pass, Avoid at 40% or less, else Wait.
Proof
  The same verdicts are worked out for every past day of the daily series and compared with gold's return over the
  next 63 / 126 / 252 trading days. Days overlap, so the count of independent periods is about n / horizon.

Outputs docs/gold/gold.json and docs/gold-desk.html.
Usage: python gold_desk.py            (logs in to Dhan, fetches, builds)
       python gold_desk.py --offline  (builds from the saved files only)
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
HORIZONS = (("3 months", 63), ("6 months", 126), ("1 year", 252))


# ---------------------------------------------------------------- fetch and keep
def fetch(dhan, scrip_csv: str, today: dt.date) -> dict:
    """{'bees': {date: close}, 'mcx': {date: close}, 'mcx_contract': str, 'nifty': {date: close}}"""
    import markets as MK
    import refresh as R
    import terminal_bt as T

    def closes(sid, seg, inst, start):
        out, s = {}, start
        while s <= today:
            e = min(s + dt.timedelta(days=1000), today)
            try:
                r = T.series(dhan.daily(sid, seg, inst, s, e), R.IST)
                out.update({d: c for d, c in zip(r["d"], r["c"]) if c})
            except Exception as ex:  # an early window can be empty; later windows still count
                print(f"  {sid} {s}..{e}: {str(ex)[:80]}")
            s = e + dt.timedelta(days=1)
        return out
    ids = T.find_ids(scrip_csv, ["GOLDBEES"])
    if "GOLDBEES" not in ids:
        raise RuntimeError("GOLDBEES not in Dhan's instrument list")
    out = {"bees": closes(ids["GOLDBEES"], "NSE_EQ", "EQUITY", dt.date(2009, 1, 1)),
           "nifty": closes(13, "IDX_I", "INDEX", dt.date(2009, 1, 1))}
    fut = MK.pick_futures(scrip_csv, today)
    if "GOLD" in fut:
        seg, sid, sym, _ = fut["GOLD"]
        out["mcx"] = closes(sid, seg, "FUTCOM", today - dt.timedelta(days=400))
        out["mcx_contract"] = sym
    if "SILVER" in fut:  # for the gold/silver ratio
        sseg, ssid, _, _ = fut["SILVER"]
        out["silver"] = closes(ssid, sseg, "FUTCOM", today - dt.timedelta(days=400))
    # today's price while the market is open: Dhan's last traded price, saved under today's date until the
    # next run replaces it with the real close
    body = {"NSE_EQ": [int(ids["GOLDBEES"])], "IDX_I": [13]}
    if "mcx" in out:
        body[seg] = [int(sid)]
    if "silver" in out:
        body[sseg] = body.get(sseg, []) + [int(ssid)]
    try:
        q = dhan.post("/marketfeed/ohlc", body).get("data") or {}
        now = dt.datetime.now(R.IST)
        got = {}
        for key, sg, i in (("bees", "NSE_EQ", ids["GOLDBEES"]), ("nifty", "IDX_I", 13)) + ((("mcx", seg, sid),) if "mcx" in out else ()) + ((("silver", sseg, ssid),) if "silver" in out else ()):
            v = (q.get(sg) or {}).get(str(i)) or {}
            if float(v.get("last_price") or 0) > 0:
                got[key] = float(v["last_price"])
        if today.weekday() < 5 and "bees" in got and today.isoformat() not in out["bees"]:
            for key, px in got.items():
                out[key][today.isoformat()] = px
            out["live"] = {"d": today.isoformat(), "t": now.strftime("%H:%M"), **got}
            print(f"  today so far ({now:%H:%M} IST): {got}")
    except Exception as ex:
        print(f"  today's quote failed: {str(ex)[:80]}")
    return out


def merge(old: dict, new: dict) -> dict:
    """Keep every close ever saved; new values win. MCX closes keep the contract they came from."""
    m = {k: dict(old.get(k) or {}) for k in ("bees", "nifty", "silver", "mcx", "mcx_contract")}
    for k in ("bees", "nifty", "silver"):
        m[k].update(new.get(k) or {})
    sym = new.get("mcx_contract")
    for d, c in (new.get("mcx") or {}).items():
        m["mcx"][d] = c
        m["mcx_contract"][d] = sym
    m = {k: dict(sorted(v.items())) for k, v in m.items()}
    m["live"] = new.get("live")  # only today's run can say a price is live
    return m


# ---------------------------------------------------------------- indicators (whole-series arrays)
def sma(a: np.ndarray, n: int) -> np.ndarray:
    out = np.full(len(a), np.nan)
    if len(a) >= n:
        cs = np.cumsum(np.insert(a, 0, 0.0))
        out[n - 1:] = (cs[n:] - cs[:-n]) / n
    return out


def ema(a: np.ndarray, n: int) -> np.ndarray:
    out = np.full(len(a), np.nan)
    if len(a) < n:
        return out
    k, e = 2 / (n + 1), a[:n].mean()
    out[n - 1] = e
    for i in range(n, len(a)):
        e = a[i] * k + e * (1 - k)
        out[i] = e
    return out


def rsi(a: np.ndarray, n: int = 14) -> np.ndarray:
    out = np.full(len(a), np.nan)
    if len(a) <= n:
        return out
    d = np.diff(a)
    g, l = np.maximum(d[:n], 0).mean(), np.maximum(-d[:n], 0).mean()
    out[n] = 100 if l == 0 else 100 - 100 / (1 + g / l)
    for i in range(n + 1, len(a)):
        x = d[i - 1]
        g, l = (g * (n - 1) + max(x, 0)) / n, (l * (n - 1) + max(-x, 0)) / n
        out[i] = 100 if l == 0 else 100 - 100 / (1 + g / l)
    return out


def ret(a: np.ndarray, n: int) -> np.ndarray:
    out = np.full(len(a), np.nan)
    out[n:] = a[n:] / a[:-n] - 1
    return out


def rolling_max(a: np.ndarray, n: int) -> np.ndarray:
    from numpy.lib.stride_tricks import sliding_window_view
    out = np.full(len(a), np.nan)
    if len(a) >= n:
        out[n - 1:] = sliding_window_view(a, n).max(axis=1)
    return out


def indicators(c: np.ndarray, nifty: np.ndarray | None) -> dict:
    m20, m50, m200 = sma(c, 20), sma(c, 50), sma(c, 200)
    macd = ema(c, 12) - ema(c, 26)
    sig = np.full(len(c), np.nan)
    ok = ~np.isnan(macd)
    if ok.sum() >= 9:
        sig[ok] = ema(macd[ok], 9)
    sd = np.full(len(c), np.nan)
    if len(c) >= 20:
        from numpy.lib.stride_tricks import sliding_window_view
        sd[19:] = sliding_window_view(c, 20).std(axis=1)
    lr = np.insert(np.diff(np.log(c)), 0, np.nan)
    vol = np.full(len(c), np.nan)
    if len(c) > 64:
        from numpy.lib.stride_tricks import sliding_window_view
        vol[64:] = sliding_window_view(lr[1:], 64).std(axis=1)[:len(c) - 64] * np.sqrt(252)
    return {"m50": m50, "m200": m200, "vs50": c / m50 - 1, "vs200": c / m200 - 1, "cross": m50 / m200 - 1, "rsi": rsi(c),
            "macd": macd, "sig": sig, "bb": (c - (m20 - 2 * sd)) / (4 * sd), "bbw": 4 * sd / m20,
            "r1m": ret(c, 21), "r3m": ret(c, 63), "r6m": ret(c, 126), "r1y": ret(c, 252),
            "hi52": c / rolling_max(c, 252) - 1, "vol": vol,
            "rs3": ret(c, 63) - ret(nifty, 63) if nifty is not None else np.full(len(c), np.nan)}


def checks(I: dict, i: int) -> list:
    """[(horizon, [(label, True/False/None)])] on day i, the Terminal's rules for a non-stock."""
    def v(k):
        x = I[k][i]
        return None if x is None or np.isnan(x) else float(x)

    def ck(label, x, f):
        return (label, None if x is None else bool(f(x)))
    macd_up = None if np.isnan(I["macd"][i]) or np.isnan(I["sig"][i]) else bool(I["macd"][i] > I["sig"][i])
    return [("3 months", [ck("Above its 50-day average", v("vs50"), lambda x: x > 0), ("MACD above its signal line", macd_up),
                          ck("Up over 3 months", v("r3m"), lambda x: x > 0), ck("Beating the Nifty over 3 months", v("rs3"), lambda x: x > 0),
                          ck("RSI between 40 and 70 (not stretched)", v("rsi"), lambda x: 40 <= x <= 70)]),
            ("6 months", [ck("Above its 200-day average", v("vs200"), lambda x: x > 0), ck("50-day average above 200-day", v("cross"), lambda x: x > 0),
                          ck("Up over 6 months", v("r6m"), lambda x: x > 0), ck("Within 20% of its 52-week high", v("hi52"), lambda x: x > -0.20)]),
            ("1 year", [ck("Above its 200-day average", v("vs200"), lambda x: x > 0), ck("50-day average above 200-day", v("cross"), lambda x: x > 0),
                        ck("Up over 1 year", v("r1y"), lambda x: x > 0), ck("Within 15% of its 52-week high", v("hi52"), lambda x: x > -0.15)])]


def verdict(cks: list) -> str:
    known = [ok for _, ok in cks if ok is not None]
    if len(known) < 3:
        return "Not enough data"
    s = sum(known) / len(known)
    return "Good to buy" if s >= 0.75 else "Avoid" if s <= 0.4 else "Wait"


def proof(c: np.ndarray, I: dict, start: int = 252) -> dict:
    """For each horizon: how gold did over the next h days after each past verdict."""
    out = {}
    verdicts = [None] * len(c)
    for i in range(start, len(c)):
        verdicts[i] = {h: verdict(cks) for h, cks in checks(I, i)}
    for lab, h in HORIZONS:
        rows, fwd_all = {}, []
        for i in range(start, len(c) - h):
            f = c[i + h] / c[i] - 1
            fwd_all.append(f)
            rows.setdefault(verdicts[i][lab], []).append(f)

        def st(xs):
            a = np.array(xs)
            return {"n": len(a), "periods": round(len(a) / h, 1), "avg": round(float(a.mean()), 4), "med": round(float(np.median(a)), 4),
                    "up": round(float((a > 0).mean()), 3), "worst": round(float(a.min()), 4)} if len(a) else None
        out[lab] = {"h": h, "all": st(fwd_all), "by": {k: st(v) for k, v in rows.items()}}
    return out


# ---------------------------------------------------------------- build
def level_check(mcx: dict, bees: dict, hist_w: list) -> dict:
    """Scale GOLDBEES (Rs per unit) to Rs per 10 g using Dhan's own MCX GOLD closes on the same days.

    NSE closes at 15:30 and MCX at 23:30, so the daily ratio wobbles with gold's evening move; the check is the
    typical (median) gap of each day's ratio from k over the last 60 shared days, which must be 1.5% or less.
    The old weekly Rs history is $ x USDINR without import duty, so it is only joined for the long chart, by the ratio
    on the last week both have (reported as the domestic premium)."""
    import bisect
    com = [d for d in sorted(mcx) if d in bees][-60:]
    if len(com) >= 20:
        r = np.array([mcx[d] / bees[d] for d in com])
        k = float(np.median(r))
        L = {"basis": "MCX GOLD future", "k": round(k, 2), "days": len(com), "from": com[0], "to": com[-1],
             "lo": round(float(r.min()), 1), "hi": round(float(r.max()), 1), "typical": round(float(np.median(np.abs(r / k - 1))), 4)}
        L["ok"] = L["typical"] <= 0.015
    else:  # no MCX history yet: fall back to the old weekly history (international price, no duty)
        bd, pairs = sorted(bees), []
        for row in hist_w[-60:]:
            j = bisect.bisect_right(bd, row[0]) - 1
            if row[2] and j >= 0:
                pairs.append(row[2] / bees[bd[j]])
        if len(pairs) < 20:
            raise RuntimeError("no MCX closes and too little overlap with the history to scale GOLDBEES")
        r = np.array(pairs)
        k = float(np.median(r))
        L = {"basis": "old weekly history (no MCX yet)", "k": round(k, 2), "days": len(pairs), "from": hist_w[-60][0], "to": hist_w[-1][0],
             "lo": round(float(r.min()), 1), "hi": round(float(r.max()), 1), "typical": round(float(np.median(np.abs(r / k - 1))), 4), "ok": False}
    return L


def levels(c: np.ndarray, d: list, I: dict, extra: list, look: int = 500, k: int = 5, tol: float = 0.015) -> dict:
    """Support and resistance from daily closes, the same method as the Terminal's Analyze tab: a swing low/high is
    the lowest/highest close within k bars each side; swings within 1.5% merge into one level (touches counted).
    The 50/200-day averages and any extra levels (value channel) are added; the 52-week high is resistance when no
    swing high is above the price."""
    n, px = len(c), float(c[-1])
    s0 = max(0, n - look)
    sw = []
    for j in range(s0 + k, n - k):
        w = c[j - k:j + k + 1]
        if c[j] == w.min():
            sw.append((float(c[j]), d[j], "low"))
        elif c[j] == w.max():
            sw.append((float(c[j]), d[j], "high"))
    groups = []
    for v, day, kind in sorted(sw):
        if groups and v <= groups[-1]["mean"] * (1 + tol):
            g = groups[-1]
            g["vals"].append(v)
            g["mean"] = sum(g["vals"]) / len(g["vals"])
            g["last"] = max(g["last"], day)
        else:
            groups.append({"vals": [v], "mean": v, "last": day})
    lv = [{"px": round(g["mean"], 0), "what": "Swing level", "touches": len(g["vals"]), "last": g["last"]} for g in groups]
    for lab, key in (("50-day average", "m50"), ("200-day average", "m200")):
        if not np.isnan(I[key][-1]):
            lv.append({"px": round(float(I[key][-1]), 0), "what": lab, "touches": None, "last": None})
    lv += extra
    for x in lv:
        x["dist"] = round(x["px"] / px - 1, 4)
    sup = sorted([x for x in lv if x["px"] < px], key=lambda x: -x["px"])[:5]
    res = sorted([x for x in lv if x["px"] > px], key=lambda x: x["px"])[:4]
    if not any(x["what"] == "Swing level" for x in res):
        hi = float(c[-252:].max())
        if hi > px:
            res.append({"px": round(hi, 0), "what": "52-week high", "touches": None, "last": None, "dist": round(hi / px - 1, 4)})
    return {"support": sup, "resistance": res}


def falls(c: np.ndarray, d: list, cut: float = 0.10) -> dict:
    """Falls of 10% or more from a closing peak (5% if none): trading days peak to trough and trough back to the peak."""
    def scan(cut):
        out, pk, pi, i = [], c[0], 0, 1
        while i < len(c):
            if c[i] >= pk:
                pk, pi = c[i], i
                i += 1
                continue
            if c[i] / pk - 1 <= -cut:
                j, ti = i, i
                while j < len(c) and c[j] < pk:
                    if c[j] < c[ti]:
                        ti = j
                    j += 1
                rec = j if j < len(c) else None
                out.append({"peak": d[pi], "peak_px": round(float(pk), 0), "depth": round(float(c[ti] / pk - 1), 4), "trough": d[ti],
                            "down_days": ti - pi, "up_days": (rec - ti) if rec else None, "back": d[rec] if rec else None})
                if rec is None:
                    break
                pk, pi, i = c[rec], rec, rec + 1
                continue
            i += 1
        return out
    rows = scan(cut) or scan(0.05)
    done = [r for r in rows if r["up_days"] is not None]
    cur = rows[-1] if rows and rows[-1]["up_days"] is None else None
    like = [r for r in done if cur and r["depth"] <= cur["depth"] * 0.7]
    med = lambda xs: int(np.median(xs)) if xs else None
    return {"rows": rows, "cut": cut if rows and rows[0]["depth"] <= -cut else 0.05,
            "med_up": med([r["up_days"] for r in done]), "med_down": med([r["down_days"] for r in done]),
            "med_total": med([r["down_days"] + r["up_days"] for r in done]),
            "like_n": len(like), "like_med_total": med([r["down_days"] + r["up_days"] for r in like]), "current": cur}


def value(long: list, hist: dict, gold_last: float, mcx: dict, silver: dict) -> dict:
    """Value channel (log trend of the weekly rupee price since 2003, bands at 1 and 2 standard deviations), price vs
    its 200-week average, gold/silver ratio, and the old desk's real-price and real-yield figures."""
    t0 = dt.date.fromisoformat(long[0][0])
    t = np.array([(dt.date.fromisoformat(x) - t0).days / 365.25 for x, _ in long])
    y = np.log(np.array([v for _, v in long]))
    b, a = np.polyfit(t, y, 1)
    res = y - (a + b * t)
    sd = float(res.std())
    z = res / sd
    fair_now = float(np.exp(a + b * t[-1]))
    # what happened next (52 weeks) from each zone of the channel
    zones = {}
    for lab, lo, hi in (("Below −1σ (cheap)", -9, -1), ("−1σ to trend", -1, 0), ("Trend to +1σ", 0, 1), ("Above +1σ (dear)", 1, 9)):
        f = [float(np.exp(y[i + 52] - y[i]) - 1) for i in range(len(y) - 52) if lo <= z[i] < hi]
        zones[lab] = {"n": len(f), "avg": round(float(np.mean(f)), 4) if f else None, "up": round(float(np.mean(np.array(f) > 0)), 3) if f else None}
    w = np.array([v for _, v in long])
    ma200 = sma(w, 200)
    vs = w / ma200 - 1
    ok = ~np.isnan(vs)
    V = {"t0": long[0][0], "a": round(float(a), 6), "b": round(float(b), 6), "sd": round(sd, 6), "growth": round(float(np.exp(b) - 1), 4),
         "fair": round(fair_now, 0), "z": round(float(z[-1]), 2), "vs_fair": round(gold_last / fair_now - 1, 4),
         "bands": {k: round(fair_now * float(np.exp(m * sd)), 0) for k, m in (("-2", -2), ("-1", -1), ("0", 0), ("1", 1), ("2", 2))},
         "zones": zones, "vs200w": round(float(vs[-1]), 4), "vs200w_pct": round(float((vs[ok] < vs[-1]).mean()), 3),
         "ma200w": round(float(ma200[-1]), 0)}
    hv = hist.get("value") or {}
    gs = hv.get("gsr_series") or []
    com = [x for x in sorted(mcx) if x in silver]
    if com:
        g = mcx[com[-1]] * 100 / silver[com[-1]]
        V["gsr"] = {"now": round(g, 1), "d": com[-1], "src": "MCX gold ÷ MCX silver (Dhan)"}
    elif gs:
        V["gsr"] = {"now": gs[-1][1], "d": gs[-1][0], "src": "old desk"}
    if gs and "gsr" in V:
        arr = np.array([r[1] for r in gs])
        V["gsr"].update({"avg": round(float(arr.mean()), 1), "pct": round(float((arr < V["gsr"]["now"]).mean()), 3), "series": gs})
    rs = hv.get("real_series") or []
    if rs:
        arr = np.array([r[1] for r in rs])
        V["real"] = {"now": rs[-1][1], "d": rs[-1][0], "ath": hv.get("real_ath"), "ath_d": hv.get("real_ath_date"),
                     "avg": round(float(arr.mean()), 0), "pct": round(float((arr < rs[-1][1]).mean()), 3), "series": rs}
    if hv.get("ry_model"):
        V["ry"] = {**hv["ry_model"], "real_yield": hv.get("real_yield_now"), "infl": hv.get("infl_now")}
    return V


def build(hist: dict, daily: dict, asof: str) -> dict:
    bees = daily.get("bees") or {}
    if len(bees) < 300:
        raise RuntimeError(f"only {len(bees)} GOLDBEES closes; need 300+")
    mcx = daily.get("mcx") or {}
    L = level_check(mcx, bees, hist["w"])
    d = sorted(bees)
    c = np.array([bees[x] for x in d]) * L["k"]
    nf = daily.get("nifty") or {}
    nifty = None
    if nf:
        nd, last, arr = sorted(nf), None, []
        import bisect
        for x in d:
            j = bisect.bisect_right(nd, x) - 1
            arr.append(nf[nd[j]] if j >= 0 else np.nan)
        nifty = np.array(arr, dtype=float)
    I = indicators(c, nifty)
    i = len(c) - 1
    H = [{"lab": h, "checks": [[lab, ok] for lab, ok in cks], "v": verdict(cks),
          "pass": sum(1 for _, ok in cks if ok), "n": sum(1 for _, ok in cks if ok is not None)} for h, cks in checks(I, i)]
    P = proof(c, I)
    # all-time high: weekly history and the scaled daily series together
    hw = [(r[0], r[2]) for r in hist["w"] if r[2]]
    ath_d, ath = max(zip(d, c.tolist()), key=lambda z: z[1])
    import bisect
    j = bisect.bisect_right(d, hw[-1][0]) - 1
    prem = float(c[j]) / hw[-1][1]  # domestic price over the old $ x USDINR price, on the join week
    L["prem"] = round(prem - 1, 4)
    hw = [(x, v * prem) for x, v in hw]
    md = sorted(mcx)
    mx = None
    if md:
        m_last = md[-1]
        mx = {"d": m_last, "c": mcx[m_last], "prev": mcx[md[-2]] if len(md) > 1 else None,
              "contract": (daily.get("mcx_contract") or {}).get(m_last),
              "gap": round(mcx[m_last] / (bees[m_last] * L["k"]) - 1, 4) if m_last in bees else None,
              "spark": [[x, mcx[x]] for x in md[-60:]]}
    f = {k: (None if np.isnan(v[i]) else round(float(v[i]), 4)) for k, v in I.items() if k not in ("m50", "m200", "macd", "sig")}
    f["macd_up"] = None if np.isnan(I["sig"][i]) else bool(I["macd"][i] > I["sig"][i])
    f.update({"last": round(float(c[i]), 0), "prev": round(float(c[i - 1]), 0), "date": d[i], "bees": bees[d[i]],
              "ath": round(ath, 0), "ath_d": ath_d, "from_ath": round(float(c[i] / ath - 1), 4),
              "lo52": round(float(c[i] / c[-252:].min() - 1), 4), "hi52_px": round(float(c[-252:].max()), 0), "lo52_px": round(float(c[-252:].min()), 0)})
    n = 520
    chart = {"d": d[-n:], "c": [round(x, 0) for x in c[-n:].tolist()],
             "m50": [None if np.isnan(x) else round(x, 0) for x in I["m50"][-n:].tolist()],
             "m200": [None if np.isnan(x) else round(x, 0) for x in I["m200"][-n:].tolist()]}
    # long view: weekly history, then the scaled daily series sampled on Fridays after it ends
    end = hw[-1][0]
    tail = [(x, round(float(v), 0)) for x, v in zip(d, c) if x > end and dt.date.fromisoformat(x).weekday() == 4]
    if d[-1] > end and (not tail or tail[-1][0] != d[-1]):
        tail.append((d[-1], round(float(c[-1]), 0)))
    long = [[x, v] for x, v in hw] + [[x, v] for x, v in tail]
    rets = {}
    for lab, yrs in (("1 year", 1), ("3 years", 3), ("5 years", 5), ("10 years", 10), ("20 years", 20)):
        tgt = (dt.date.fromisoformat(long[-1][0]) - dt.timedelta(days=round(365.25 * yrs))).isoformat()
        past = [v for x, v in long if x <= tgt]
        if past:
            tot = long[-1][1] / past[-1] - 1
            rets[lab] = {"total": round(tot, 4), "cagr": round((1 + tot) ** (1 / yrs) - 1, 4)}
    V = value(long, hist, float(c[i]), mcx, daily.get("silver") or {})
    extra = [{"px": V["bands"][k], "what": lab, "touches": None, "last": None}
             for k, lab in (("0", "Value channel trend"), ("-1", "Value channel −1σ"), ("-2", "Value channel −2σ"))]
    extra.append({"px": V["ma200w"], "what": "200-week average", "touches": None, "last": None})
    LV = levels(c, d, I, extra)
    if mx and mx["d"] == d[i]:
        LV["mcx_k"] = round(mx["c"] / float(c[i]), 5)
    FL = falls(c, d)
    return {"asof": asof, "date": d[i], "f": f, "value": V, "levels": LV, "falls": FL, "horizons": H, "proof": P, "level": L, "mcx": mx, "chart": chart,
            "long": long, "rets": rets, "daily_from": d[0], "daily_n": len(d),
            "studies": {k: hist.get(k) for k in ("gold_dd", "falls_nifty", "falls_nifty_big", "trend_strategy", "hedge")},
            "hist_source": hist.get("source"), "hist_asof": hist.get("asof"),
            "live": daily.get("live") if (daily.get("live") or {}).get("d") == d[i] else None}


def render(data: dict, out: Path) -> None:
    tpl = (HERE / "gold_template.html").read_text(encoding="utf-8")
    js = json.dumps(data, separators=(",", ":"), allow_nan=False).replace("</", "<\\/")
    out.write_text(tpl.replace("/*GOLD_DATA*/null", js), encoding="utf-8")


def main() -> int:
    root = Path(sys.argv[sys.argv.index("--root") + 1]) if "--root" in sys.argv else ROOT
    gdir = root / "docs/gold"
    hist = json.loads((gdir / "history.json").read_text(encoding="utf-8"))
    dpath = gdir / "daily.json"
    daily = json.loads(dpath.read_text(encoding="utf-8")) if dpath.exists() else {}
    import refresh as R
    now = dt.datetime.now(R.IST)
    if "--offline" not in sys.argv:
        import requests
        cid, pin, sec = (os.environ[k] for k in ("DHAN_CLIENT_ID", "DHAN_PIN", "DHAN_TOTP_SECRET"))
        dhan = R.Dhan(cid, R.login(cid, pin, sec))
        scrip = requests.get(R.SCRIP_MASTER, timeout=60).text
        new = fetch(dhan, scrip, now.date())
        print(f"Dhan: GOLDBEES {len(new['bees'])} closes, Nifty {len(new['nifty'])}, MCX {len(new.get('mcx') or {})} "
              f"({new.get('mcx_contract')})", flush=True)
        daily = merge(daily, new)
        dpath.write_text(json.dumps(daily, separators=(",", ":")), encoding="utf-8")
    data = build(hist, daily, now.strftime("%Y-%m-%d %H:%M"))
    (gdir / "gold.json").write_text(json.dumps({k: v for k, v in data.items() if k not in ("long", "chart", "studies")},
                                               indent=1, allow_nan=False), encoding="utf-8")
    render(data, root / "docs/gold-desk.html")
    L, f = data["level"], data["f"]
    print(f"Gold desk {data['date']}: Rs {f['last']:,.0f}/10 g; " + "; ".join(f"{h['lab']} {h['v']}" for h in data["horizons"]))
    print(f"level check vs {L['basis']}: k={L['k']} over {L['days']} days, typical gap {L['typical']:.2%} "
          f"({'OK' if L['ok'] else 'FAILED'}); domestic premium over old history {L['prem']:.2%}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
