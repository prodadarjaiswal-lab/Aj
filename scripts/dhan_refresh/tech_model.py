"""Technical model: candidate signals, their 6-year back-test, and today's signals.

Every signal on day i uses only data up to day i. A signal counts on the day it
first appears (not on every day it stays true). Each is judged on:
  * excess return vs the Nifty 50 after 5, 10 and 21 trading days,
  * an ATR trade: buy at the close, stop 2 x ATR(14) below, target 3 x ATR(14)
    above, exit at the close of day 21 if neither is hit; result in R (risk units),
  * the first 4 years (in-sample) and the last 2 years (out-of-sample) separately,
  * rising markets (Nifty above its 200-day average) and weak markets separately.
A signal is "tested" only if it beats the average stock in both periods in rising
markets (by 0.3% or more over 10 days out-of-sample, t >= 2, better ATR-trade R)
with at least 100 cases out-of-sample. Only tested signals feed the bot's verdict.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import os
import statistics as st
import sys
from pathlib import Path

from setups import Series, rolling_mean

NAMES = {
    "trend": "Trend template: price above rising 50, 150 and 200-day averages, near its 52-week high",
    "hi52v": "New 52-week closing high on 1.5x average volume",
    "vcp": "Volatility contraction near the high: 10-day range under 60% of the 50-day range",
    "adx": "Strong trend starting: ADX(14) crosses above 25 with buyers in control",
    "rsi2": "Short dip in an uptrend: RSI(2) under 10 while above the 200-day average",
    "st_up": "Supertrend(10, 3) turns up",
    "nr7": "Tightest range in 7 days, inside the prior bar, in an uptrend",
    "accum": "Accumulation: up-day volume 1.5x down-day volume over 50 days, above the 50-day average",
    "gap": "Gap up of 3% or more that holds into the close on 2x volume",
    "volbreak": "Volume breakout above the 20-day high (existing setup)",
    "pullback": "Pullback in an uptrend (existing setup)",
    "don55": "Donchian breakout: close above the 55-day high (turtle rule)",
    "macd0": "MACD crosses above its signal line while above zero",
    "bbsq": "Bollinger squeeze breakout: band width in its lowest 20% of 6 months, close above the upper band",
    "rsnew": "Relative strength line at a 1-year high before the price is",
    "dip3": "Three down closes in a row while above the 200-day average",
    "ibs": "Closes in the bottom 20% of its day's range while above the 200-day average",
    "reclaim200": "Closes back above the 200-day average after 20+ days below",
    "extended": "Overextended: RSI(14) over 80 and 25% above the 50-day average (warning)",
    "downtrend": "Downtrend: below a falling 200-day average and 50-day below 200-day (warning)",
}
WARN = ("extended", "downtrend")


def _ema(a, n):
    out, e, k = [None] * len(a), None, 2 / (n + 1)
    for i, x in enumerate(a):
        if x is None:
            continue
        e = x if e is None else x * k + e * (1 - k)
        if i >= n - 1:
            out[i] = e
    return out


def atr_series(h, l, c, n=14):
    tr = [h[0] - l[0]] + [max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1])) for i in range(1, len(c))]
    out, a = [None] * len(c), None
    for i, x in enumerate(tr):
        if i == n - 1:
            a = sum(tr[:n]) / n
        elif i >= n:
            a = (a * (n - 1) + x) / n
        out[i] = a
    return out, tr


def adx_series(h, l, c, n=14):
    out = [None] * len(c)
    pdm = [0.0] + [max(h[i] - h[i - 1], 0) if (h[i] - h[i - 1]) > (l[i - 1] - l[i]) else 0.0 for i in range(1, len(c))]
    ndm = [0.0] + [max(l[i - 1] - l[i], 0) if (l[i - 1] - l[i]) > (h[i] - h[i - 1]) else 0.0 for i in range(1, len(c))]
    _, tr = atr_series(h, l, c, n)
    if len(c) < 2 * n + 1:
        return out, out, out
    s_tr, s_p, s_n = sum(tr[1:n + 1]), sum(pdm[1:n + 1]), sum(ndm[1:n + 1])
    pdi, ndi, dx = [None] * len(c), [None] * len(c), [None] * len(c)
    for i in range(n, len(c)):
        if i > n:
            s_tr, s_p, s_n = s_tr - s_tr / n + tr[i], s_p - s_p / n + pdm[i], s_n - s_n / n + ndm[i]
        pdi[i], ndi[i] = 100 * s_p / s_tr if s_tr else 0, 100 * s_n / s_tr if s_tr else 0
        sm = pdi[i] + ndi[i]
        dx[i] = 100 * abs(pdi[i] - ndi[i]) / sm if sm else 0
    a = None
    for i in range(2 * n - 1, len(c)):
        a = sum(dx[n:2 * n]) / n if a is None else (a * (n - 1) + dx[i]) / n
        out[i] = a
    return out, pdi, ndi


def supertrend_dir(h, l, c, atr, mult=3.0):
    d = [None] * len(c)
    up = dn = None
    trend = 1
    for i in range(len(c)):
        if atr[i] is None:
            continue
        mid = (h[i] + l[i]) / 2
        bu, bd = mid - mult * atr[i], mid + mult * atr[i]
        up = bu if up is None or c[i - 1] < up else max(bu, up)
        dn = bd if dn is None or c[i - 1] > dn else min(bd, dn)
        if trend == -1 and c[i] > dn:
            trend = 1
        elif trend == 1 and c[i] < up:
            trend = -1
        d[i] = trend
    return d


def rsi_n(c, n):
    out = [None] * len(c)
    if len(c) <= n:
        return out
    g = [max(c[i] - c[i - 1], 0) for i in range(1, len(c))]
    lo = [max(c[i - 1] - c[i], 0) for i in range(1, len(c))]
    ag, al = sum(g[:n]) / n, sum(lo[:n]) / n
    for i in range(n, len(g) + 1):
        if i > n:
            ag, al = (ag * (n - 1) + g[i - 1]) / n, (al * (n - 1) + lo[i - 1]) / n
        out[i] = 100.0 if al == 0 else 100 - 100 / (1 + ag / al)
    return out


class Tech:
    """All indicator series for one stock, aligned with the Nifty."""

    def __init__(self, o, h, l, c, v, nc):
        self.o, self.h, self.l, self.c, self.v, self.nc = o, h, l, c, v, nc
        self.S = Series(c, h, l, nc, v)
        self.m150 = rolling_mean(c, 150)
        self.atr, _ = atr_series(h, l, c, 14)
        self.atr10, _ = atr_series(h, l, c, 10)
        self.atr50, _ = atr_series(h, l, c, 50)
        self.adx, self.pdi, self.ndi = adx_series(h, l, c, 14)
        self.st = supertrend_dir(h, l, c, self.atr10, 3.0)
        self.rsi2 = rsi_n(c, 2)
        self.v50 = rolling_mean(v, 50) if v else None
        self.m55h = [max(h[i - 55:i]) if i >= 55 else None for i in range(len(c))]
        ema = lambda a, n: _ema(a, n)
        e12, e26 = ema(c, 12), ema(c, 26)
        self.macd = [a - b if a is not None and b is not None else None for a, b in zip(e12, e26)]
        self.sig = _ema([x if x is not None else 0.0 for x in self.macd], 9)

    def flags(self, i) -> set:
        S, c, h, l, v = self.S, self.c, self.h, self.l, self.v
        if i < 252 or S.m200[i] is None or S.m200[i - 21] is None or self.m150[i] is None:
            return set()
        f, last = set(), c[i]
        m50, m150, m200 = S.m50[i], self.m150[i], S.m200[i]
        hi52, lo52 = max(h[i - 251:i + 1]), min(l[i - 251:i + 1])
        rising200 = m200 > S.m200[i - 21]
        if last > m50 > m150 > m200 and rising200 and last >= 0.75 * hi52 and last >= 1.3 * lo52:
            f.add("trend")
        vol_ok = v and self.v50 and self.v50[i - 1] and v[i]
        if vol_ok and last >= max(c[i - 251:i]) and v[i] >= 1.5 * self.v50[i - 1]:
            f.add("hi52v")
        if self.atr10[i] and self.atr50[i] and self.atr10[i] < 0.6 * self.atr50[i] and last > m50 and last >= 0.92 * hi52:
            f.add("vcp")
        if self.adx[i] and self.adx[i - 1] and self.adx[i] > 25 >= self.adx[i - 1] and self.pdi[i] > self.ndi[i] and last > m50:
            f.add("adx")
        if self.rsi2[i] is not None and self.rsi2[i] < 10 and last > m200:
            f.add("rsi2")
        if self.st[i] == 1 and self.st[i - 1] == -1:
            f.add("st_up")
        rng = [h[k] - l[k] for k in range(i - 6, i + 1)]
        if rng[-1] == min(rng) and h[i] <= h[i - 1] and l[i] >= l[i - 1] and last > m50:
            f.add("nr7")
        if v and last > m50:
            up = sum(v[k] for k in range(i - 49, i + 1) if c[k] > c[k - 1])
            dn = sum(v[k] for k in range(i - 49, i + 1) if c[k] < c[k - 1])
            if dn and up / dn >= 1.5:
                f.add("accum")
        if vol_ok and self.o[i] >= 1.03 * c[i - 1] and last > self.o[i] and v[i] >= 2 * self.v50[i - 1]:
            f.add("gap")
        if self.m55h[i] and last > self.m55h[i]:
            f.add("don55")
        if self.macd[i] is not None and self.macd[i - 1] is not None and self.macd[i] > 0 \
                and self.macd[i] > self.sig[i] and self.macd[i - 1] <= self.sig[i - 1]:
            f.add("macd0")
        bw = [x for x in S.bbw[i - 125:i] if x is not None]
        if bw and S.bbw[i - 1] is not None and sum(x < S.bbw[i - 1] for x in bw) <= 0.2 * len(bw) \
                and S.m20[i] and S.bbw[i] is not None and last > S.m20[i] * (1 + S.bbw[i] / 2):
            f.add("bbsq")
        rsl = [x for x in S.rsl[i - 251:i + 1] if x is not None]
        if rsl and S.rsl[i] >= max(rsl) and last < 0.97 * hi52:
            f.add("rsnew")
        if last > m200 and c[i] < c[i - 1] < c[i - 2] < c[i - 3]:
            f.add("dip3")
        if last > m200 and h[i] > l[i] and (last - l[i]) / (h[i] - l[i]) <= 0.2:
            f.add("ibs")
        if last > m200 and all(c[k] < S.m200[k] for k in range(i - 20, i) if S.m200[k]):
            f.add("reclaim200")
        t = S.tag(i)
        if t in ("volbreak", "pullback"):
            f.add(t)
        if S.rsi[i] and S.rsi[i] > 80 and last > 1.25 * m50:
            f.add("extended")
        if last < m200 and not rising200 and m50 < m200:
            f.add("downtrend")
        return f

    def atr_trade(self, i, horizon=21, stop=2.0, target=3.0):
        """R multiple of: buy at close i, stop/target in ATR units, exit at day `horizon` close."""
        a = self.atr[i]
        if not a:
            return None
        e, s, t = self.c[i], self.c[i] - stop * a, self.c[i] + target * a
        for k in range(i + 1, min(i + horizon, len(self.c) - 1) + 1):
            if self.l[k] <= s:
                return -1.0                      # stop first (assumed if both touched the same day)
            if self.h[k] >= t:
                return target / stop
        return (self.c[min(i + horizon, len(self.c) - 1)] - e) / (stop * a)


def stats(rows):
    if len(rows) < 20:
        return {"n": len(rows)}
    out = {"n": len(rows)}
    for j, k in ((0, "x5"), (1, "x10"), (2, "x21")):
        a = [r[j] for r in rows]
        out[k] = round(st.mean(a), 5)
        out["hit" + k[1:]] = round(sum(x > 0 for x in a) / len(a), 4)
    a10 = [r[1] for r in rows]
    sd = st.pstdev(a10) or 1e-9
    out["t10"] = round(st.mean(a10) / (sd / math.sqrt(len(a10))), 2)
    rr = [r[3] for r in rows if r[3] is not None]
    if rr:
        out["avg_r"] = round(st.mean(rr), 3)
        out["win"] = round(sum(x > 0 for x in rr) / len(rr), 4)
    return out


def backtest(data: dict, nifty: dict, oos_years: float = 2.0) -> dict:
    """data: {sym: {d,o,h,l,c,v}}; nifty: {d,c}."""
    nmap = dict(zip(nifty["d"], nifty["c"]))
    nm200 = dict(zip(nifty["d"], rolling_mean(nifty["c"], 200)))
    cut = (dt.date.fromisoformat(nifty["d"][-1]) - dt.timedelta(days=int(365 * oos_years))).isoformat()
    rows = {k: [] for k in NAMES}
    base = []
    for sym, o in data.items():
        keep = [i for i, d in enumerate(o["d"]) if d in nmap]
        if len(keep) < 300:
            continue
        d = [o["d"][i] for i in keep]
        cols = {k: [o[k][i] for i in keep] for k in ("o", "h", "l", "c")}
        v = [o["v"][i] for i in keep] if o.get("v") else None
        nc = [nmap[x] for x in d]
        T = Tech(cols["o"], cols["h"], cols["l"], cols["c"], v, nc)
        c = cols["c"]
        prev = set()
        for i in range(252, len(c) - 21):
            f = T.flags(i)
            new = f - prev
            prev = f
            ex = lambda k: (c[i + k] / c[i] - 1) - (nc[i + k] / nc[i] - 1)
            up = nm200.get(d[i]) is not None and nc[i] > nm200[d[i]]
            oos = d[i] >= cut
            if i % 5 == 0:
                base.append((ex(5), ex(10), ex(21), T.atr_trade(i), up, oos))
            for k in new:
                rows[k].append((ex(5), ex(10), ex(21), T.atr_trade(i), up, oos))
    out = {"cutoff": cut, "signals": {}}
    sel = lambda r, up, oos: [x for x in r if x[4] == up and x[5] == oos]
    out["base"] = {p: {m: stats(sel(base, up, oos)) for m, up in (("up", True), ("weak", False))}
                   for p, oos in (("in", False), ("out", True))}
    for k, r in rows.items():
        res = {p: {m: stats(sel(r, up, oos)) for m, up in (("up", True), ("weak", False))} for p, oos in (("in", False), ("out", True))}
        bi, bo = out["base"]["in"]["up"], out["base"]["out"]["up"]
        si, so = res["in"]["up"], res["out"]["up"]
        lift = lambda s, b, f: (s.get(f, 0) - b.get(f, 0)) if s.get("n", 0) >= 20 else None
        res["lift_in_x10"], res["lift_out_x10"] = lift(si, bi, "x10"), lift(so, bo, "x10")
        res["lift_in_r"], res["lift_out_r"] = lift(si, bi, "avg_r"), lift(so, bo, "avg_r")
        if k in WARN:
            res["tested"] = bool(res["lift_in_x10"] is not None and res["lift_out_x10"] is not None
                                 and res["lift_in_x10"] < 0 and res["lift_out_x10"] < 0 and so.get("n", 0) >= 100)
        else:
            # positive in both periods, at least +0.3% over 10 days out-of-sample, better R than average,
            # and the out-of-sample excess return statistically distinct from zero (t >= 2)
            res["tested"] = bool(res["lift_in_x10"] is not None and res["lift_out_x10"] is not None
                                 and res["lift_in_x10"] > 0 and res["lift_out_x10"] >= 0.003
                                 and (res["lift_out_r"] or 0) > 0 and so.get("n", 0) >= 100 and so.get("t10", 0) >= 2)
        # the same test for weak markets (Nifty below its 200-day average)
        bw_i, bw_o = out["base"]["in"]["weak"], out["base"]["out"]["weak"]
        wi, wo = res["in"]["weak"], res["out"]["weak"]
        li, lo, lr = lift(wi, bw_i, "x10"), lift(wo, bw_o, "x10"), lift(wo, bw_o, "avg_r")
        res["lift_out_x10_weak"] = lo
        if k in WARN:
            res["tested_weak"] = bool(li is not None and lo is not None and li < 0 and lo < 0 and wo.get("n", 0) >= 100)
        else:
            res["tested_weak"] = bool(li is not None and lo is not None and li > 0 and lo >= 0.003 and (lr or 0) > 0
                                      and wo.get("n", 0) >= 100 and wo.get("t10", 0) >= 2)
        out["signals"][k] = res
    return out


def today(data: dict, nifty: dict) -> dict:
    """Signals active on the last bar (or that appeared in the last 3 bars) and ATR levels, per stock."""
    nmap = dict(zip(nifty["d"], nifty["c"]))
    out = {}
    for sym, o in data.items():
        keep = [i for i, d in enumerate(o["d"]) if d in nmap]
        if len(keep) < 260:
            continue
        d = [o["d"][i] for i in keep]
        cols = {k: [o[k][i] for i in keep] for k in ("o", "h", "l", "c")}
        v = [o["v"][i] for i in keep] if o.get("v") else None
        T = Tech(cols["o"], cols["h"], cols["l"], cols["c"], v, [nmap[x] for x in d])
        i = len(d) - 1
        now = T.flags(i)
        recent = set().union(*(T.flags(k) - T.flags(k - 1) for k in range(i - 2, i + 1)))
        a = T.atr[i]
        out[sym] = {"d": d[i], "c": cols["c"][i], "atr": round(a, 2) if a else None,
                    "on": sorted(now), "new": sorted(recent & now), **readout(T, i)}
    return out


def readout(T: "Tech", i: int) -> dict:
    """Plain indicator values for the technical desk (no judgement; the back-test decides what matters)."""
    S, c, h = T.S, T.c, T.h
    r = lambda x, k=1: round(x, k) if x is not None else None
    last = c[i]
    out = {"rsi": r(S.rsi[i]), "adx": r(T.adx[i]), "di": "buyers" if (T.pdi[i] or 0) > (T.ndi[i] or 0) else "sellers",
           "st": "up" if T.st[i] == 1 else "down", "macd": "above signal" if (T.macd[i] or 0) > (T.sig[i] or 0) else "below signal",
           "atr_pct": r(T.atr[i] / last * 100, 2) if T.atr[i] else None,
           "vs50": r((last / S.m50[i] - 1) * 100) if S.m50[i] else None,
           "vs200": r((last / S.m200[i] - 1) * 100) if S.m200[i] else None,
           "hi52": r((last / max(h[max(0, i - 251):i + 1]) - 1) * 100),
           "rs3": r(((last / c[i - 63]) - (T.nc[i] / T.nc[i - 63])) * 100) if i >= 63 else None}
    if T.v and T.v50 and T.v50[i - 1]:
        out["volx"] = r(T.v[i] / T.v50[i - 1], 2)
    bw = [x for x in S.bbw[max(0, i - 125):i + 1] if x is not None]
    if bw and S.bbw[i] is not None:
        out["bbw_pct"] = round(sum(x < S.bbw[i] for x in bw) / len(bw) * 100)
    return out


def fetch(dhan, root: Path, years: float):
    import requests
    import n500
    import refresh as R
    scrip = requests.get(R.SCRIP_MASTER, timeout=60).text
    symbols = [u["s"] for u in n500.get_universe(dhan, root)]
    eq, ix = R.build_maps(scrip, symbols, ["Nifty 50"])
    end = dt.datetime.now(R.IST).date()
    start = end - dt.timedelta(days=int(365 * years) + 30)

    def series(resp):
        ts = resp.get("timestamp") or []
        return {"d": [dt.datetime.fromtimestamp(t, R.IST).date().isoformat() for t in ts],
                "o": list(resp["open"]), "c": list(resp["close"]), "h": list(resp["high"]), "l": list(resp["low"]),
                "v": list(resp["volume"]) if resp.get("volume") else None}
    nifty = series(dhan.daily(ix["Nifty 50"], "IDX_I", "INDEX", start, end))
    data = {}
    for sym, sid in eq.items():
        try:
            data[sym] = series(dhan.daily(sid, "NSE_EQ", "EQUITY", start, end))
        except Exception as e:
            print(f"  skip {sym}: {str(e)[:80]}")
    add_last_session(dhan, eq, ix["Nifty 50"], data, nifty)
    return data, nifty, end


def last_session_day(now: dt.datetime) -> dt.date | None:
    """The trading day whose bar Dhan's quote API holds now (None before today's close)."""
    d = now.date()
    if d.weekday() < 5:
        return d if now.time() >= dt.time(15, 35) else None
    return d - dt.timedelta(days=d.weekday() - 4)        # Saturday/Sunday -> Friday


def add_last_session(dhan, eq: dict, nifty_id, data: dict, nifty: dict, now: dt.datetime | None = None) -> int:
    """Dhan's daily history lags a day; add the last session's bar from the quote API.
    Skipped on holidays (the quote repeats the stored bar). Returns bars added."""
    import refresh as R
    now = now or dt.datetime.now(R.IST)
    day = last_session_day(now)
    if not day or not nifty["d"] or nifty["d"][-1] >= day.isoformat():
        return 0
    try:
        q = R.quotes(dhan, list(eq.values()), [nifty_id])
    except Exception as e:
        print(f"  last session not added: {str(e)[:80]}")
        return 0
    n = 0

    def add(o, v):
        nonlocal n
        if not v or v[0] <= 0 or not o["d"] or o["d"][-1] >= day.isoformat():
            return False
        if abs(v[0] / o["o"][-1] - 1) < 2e-4 and abs(v[1] / o["h"][-1] - 1) < 2e-4:
            return False                                   # holiday replay of the stored bar
        o["d"].append(day.isoformat())
        for k, x in zip(("o", "h", "l", "c"), v[:4]):
            o[k].append(x)
        if o.get("v") is not None:
            o["v"].append(v[4] if len(v) > 4 else 0)
        n += 1
        return True
    nv = q.get(("IDX_I", str(nifty_id)))
    if nv and nifty["c"]:
        if nv[0] > 0 and nv[3] > 0 and not (abs(nv[3] / nifty["c"][-1] - 1) < 2e-5):
            nifty["d"].append(day.isoformat())
            nifty["c"].append(nv[3])
    for sym, sid in eq.items():
        if sym in data:
            add(data[sym], q.get(("NSE_EQ", str(sid))))
    print(f"  added {day} from quotes to {n} stocks")
    return n


def desk(res: dict, td: dict) -> str:
    """Markdown reference for the pinned chat: what passed the back-test, and every stock's readout."""
    sig = res["signals"]
    L = [f"# Technical desk · data to {res['asof']}", "",
         f"Back-test: {res['stocks']} Nifty 500 stocks from {res['from']}; first years in-sample, from {res['cutoff']} out-of-sample. "
         "A signal is used only if it beat the average stock in both periods (t >= 2, 100+ cases, better ATR-trade result). "
         "Excess = return minus Nifty 50 over 10 trading days after the signal first appears. Re-tested daily.", "",
         "## Signals that passed", "", "| Signal | Market | Cases (last 2y) | Beat Nifty | Avg excess 10d | Typical stock |", "|---|---|---|---|---|---|"]
    for side, flag, name in (("up", "tested", "rising"), ("weak", "tested_weak", "weak")):
        b = res["base"]["out"][side]
        for k, r in sig.items():
            if r.get(flag) and k not in WARN:
                s_ = r["out"][side]
                L.append(f"| {NAMES[k]} | {name} | {s_['n']:,} | {s_['hit10'] * 100:.0f}% | {s_['x10'] * 100:+.2f}% | {b.get('x10', 0) * 100:+.2f}% |")
    L += ["", "## Signals that failed (do not use for a verdict)", ""]
    L += [f"- {NAMES[k]}" for k, r in sig.items() if not r.get("tested") and not r.get("tested_weak")]
    L += ["", "## Stocks", "", "Columns: close, new signals (last 3 days), RSI, ADX and who controls, Supertrend, MACD, % vs 50/200-day, "
          "% from 52-week high, 3-month return vs Nifty, volume vs 50-day, ATR %.", ""]
    for sym in sorted(td):
        t = td[sym]
        L.append(f"{sym}: {t['c']:.1f} | new {','.join(t['new']) or '-'} | RSI {t.get('rsi')} | ADX {t.get('adx')} {t.get('di')} | "
                 f"ST {t.get('st')} | MACD {t.get('macd')} | {t.get('vs50')}/{t.get('vs200')} | hi {t.get('hi52')} | RS {t.get('rs3')} | "
                 f"vol {t.get('volx')}x | ATR {t.get('atr_pct')}%")
    return "\n".join(L) + "\n"


def run_full(dhan, root: Path) -> dict:
    """Daily: re-run the 6-year back-test, promote or drop signals, write today's signals and the desk file."""
    data, nifty, end = fetch(dhan, root, 6)
    res = backtest(data, nifty)
    res.update({"asof": nifty["d"][-1], "from": nifty["d"][0], "stocks": len(data), "names": NAMES,
                "note": "Excess return vs Nifty 50 from the close of the first day a signal appears. ATR trade: stop 2 ATR, "
                        "target 3 ATR, exit day 21. Today's Nifty 500 members (survivorship bias)."})
    prev = {}
    try:
        prev = json.loads((root / "docs/tech-model.json").read_text(encoding="utf-8")).get("signals", {})
    except Exception:
        pass
    changes = []
    for k, r in res["signals"].items():
        for flag, regime in (("tested", "rising"), ("tested_weak", "weak")):
            was, now = prev.get(k, {}).get(flag), r.get(flag)
            if k in prev and was is not None and bool(was) != bool(now):
                changes.append(f"{'now passes' if now else 'no longer passes'} in {regime} markets: {NAMES[k]}")
            elif prev and (k not in prev or was is None) and now:
                changes.append(f"new, passes in {regime} markets: {NAMES[k]}")
    hist_p = root / "docs/tech-model-history.json"
    try:
        hist = json.loads(hist_p.read_text(encoding="utf-8"))
    except Exception:
        hist = []
    hist = [h for h in hist if h.get("asof") != res["asof"]]
    hist.append({"asof": res["asof"], "rising": [k for k, r in res["signals"].items() if r["tested"]],
                 "weak": [k for k, r in res["signals"].items() if r.get("tested_weak")], "changes": changes})
    hist_p.write_text(json.dumps(hist[-260:], indent=1), encoding="utf-8")
    td = today(data, nifty)
    (root / "docs/tech-model.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    (root / "docs/tech-today.json").write_text(json.dumps({"asof": res["asof"], "stocks": td}, separators=(",", ":")), encoding="utf-8")
    (root / "docs/technical-desk.md").write_text(desk(res, td), encoding="utf-8")
    if changes:
        try:
            import telegram as T
            T.send("<b>Technical model re-test</b>\n" + "\n".join("• " + T.esc(x) for x in changes))
        except Exception as e:
            print(f"  telegram notice failed: {e}")
    for k, r in res["signals"].items():
        so = r["out"]["up"]
        print(f"{k:10s} up={r['tested']!s:5s} weak={r.get('tested_weak')!s:5s} n_out={so.get('n')} "
              f"lift10 in={r['lift_in_x10']} out={r['lift_out_x10']} weak_out={r.get('lift_out_x10_weak')} liftR={r['lift_out_r']}")
    return res


def main() -> int:
    import refresh as R
    root = Path(sys.argv[sys.argv.index("--root") + 1]) if "--root" in sys.argv else Path("../..")
    cid, pin, sec = (os.environ[k] for k in ("DHAN_CLIENT_ID", "DHAN_PIN", "DHAN_TOTP_SECRET"))
    run_full(R.Dhan(cid, R.login(cid, pin, sec)), root)
    return 0


if __name__ == "__main__":
    sys.exit(main())
