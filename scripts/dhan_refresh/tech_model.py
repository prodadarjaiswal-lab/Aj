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
    "extended": "Overextended: RSI(14) over 80 and 25% above the 50-day average (warning)",
    "downtrend": "Downtrend: below a falling 200-day average and 50-day below 200-day (warning)",
}
WARN = ("extended", "downtrend")


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
                    "on": sorted(now), "new": sorted(recent & now),
                    "adx": round(T.adx[i], 1) if T.adx[i] else None, "st": T.st[i]}
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
                "o": resp["open"], "c": resp["close"], "h": resp["high"], "l": resp["low"], "v": resp.get("volume")}
    nifty = series(dhan.daily(ix["Nifty 50"], "IDX_I", "INDEX", start, end))
    data = {}
    for sym, sid in eq.items():
        try:
            data[sym] = series(dhan.daily(sid, "NSE_EQ", "EQUITY", start, end))
        except Exception as e:
            print(f"  skip {sym}: {str(e)[:80]}")
    return data, nifty, end


def run_today(dhan, root: Path) -> None:
    data, nifty, end = fetch(dhan, root, 1.6)
    res = {"asof": end.isoformat(), "stocks": today(data, nifty)}
    (root / "docs/tech-today.json").write_text(json.dumps(res, separators=(",", ":")), encoding="utf-8")
    print(f"tech-today: {len(res['stocks'])} stocks")


def main() -> int:
    import refresh as R
    root = Path(sys.argv[sys.argv.index("--root") + 1]) if "--root" in sys.argv else Path("../..")
    cid, pin, sec = (os.environ[k] for k in ("DHAN_CLIENT_ID", "DHAN_PIN", "DHAN_TOTP_SECRET"))
    dhan = R.Dhan(cid, R.login(cid, pin, sec))
    data, nifty, end = fetch(dhan, root, 6)
    res = backtest(data, nifty)
    res.update({"asof": end.isoformat(), "from": nifty["d"][0], "stocks": len(data), "names": NAMES,
                "note": "Excess return vs Nifty 50 from the close of the first day a signal appears. ATR trade: stop 2 ATR, "
                        "target 3 ATR, exit day 21. Today's Nifty 500 members (survivorship bias)."})
    (root / "docs/tech-model.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    (root / "docs/tech-today.json").write_text(json.dumps({"asof": end.isoformat(), "stocks": today(data, nifty)},
                                                           separators=(",", ":")), encoding="utf-8")
    for k, r in res["signals"].items():
        so = r["out"]["up"]
        print(f"{k:10s} tested={r['tested']!s:5s} n_out={so.get('n')} lift10 in={r['lift_in_x10']} out={r['lift_out_x10']} "
              f"R out={so.get('avg_r')} liftR={r['lift_out_r']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
