"""Setup definitions ("what can move next") and their back-test.

The same rules run live in the terminal (JavaScript). Keep the two in step.
A setup is tagged on day i using only data up to day i.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import os
import statistics as st
import sys
from pathlib import Path

TAGS = ("volbreak", "breakout", "coiled", "pullback", "turn")
W = (("sl200", .20), ("mom", .20), ("rs6", .20), ("vs200", .15), ("rs3", .15), ("hi52", .10))


def rolling_mean(a, k):
    out, s = [None] * len(a), 0.0
    for i, x in enumerate(a):
        s += x
        if i >= k:
            s -= a[i - k]
        if i >= k - 1:
            out[i] = s / k
    return out


def rolling_std(a, k):
    out = [None] * len(a)
    for i in range(k - 1, len(a)):
        w = a[i - k + 1:i + 1]
        m = sum(w) / k
        out[i] = math.sqrt(sum((x - m) ** 2 for x in w) / k)
    return out


def rsi_series(c, n=14):
    out = [None] * len(c)
    if len(c) <= n:
        return out
    g = [max(c[i] - c[i - 1], 0) for i in range(1, len(c))]
    l_ = [max(c[i - 1] - c[i], 0) for i in range(1, len(c))]
    ag, al = sum(g[:n]) / n, sum(l_[:n]) / n
    out[n] = 100.0 if al == 0 else 100 - 100 / (1 + ag / al)
    for i in range(n, len(g)):
        ag, al = (ag * (n - 1) + g[i]) / n, (al * (n - 1) + l_[i]) / n
        out[i + 1] = 100.0 if al == 0 else 100 - 100 / (1 + ag / al)
    return out


class Series:
    """Pre-computed rolling values for one stock aligned with the Nifty."""

    def __init__(self, c, h, l, nc, v=None):
        self.c, self.h, self.l, self.nc, self.v = c, h, l, nc, v
        self.m20, self.m50, self.m200 = rolling_mean(c, 20), rolling_mean(c, 50), rolling_mean(c, 200)
        sd = rolling_std(c, 20)
        self.bbw = [4 * sd[i] / self.m20[i] if sd[i] is not None and self.m20[i] else None for i in range(len(c))]
        self.rsi = rsi_series(c)
        self.rsl = [c[i] / nc[i] if nc[i] else None for i in range(len(c))]

    def tag(self, i):
        c, h, m20, m50, m200 = self.c, self.h, self.m20, self.m50, self.m200
        if i < 200 or m200[i] is None or m200[i - 21] is None:
            return None
        last = c[i]
        a20, a50, a200 = last > m20[i], last > m50[i], last > m200[i]
        sl200 = m200[i] / m200[i - 21] - 1
        hi52 = last / max(h[max(0, i - 249):i + 1]) - 1
        prev_hi20 = max(h[i - 20:i])
        if last > prev_hi20 and a50:
            v = self.v
            if v and i >= 50 and v[i] and sum(v[i - 50:i]) > 0 and v[i] >= 1.5 * (sum(v[i - 50:i]) / 50):
                return "volbreak"
            return "breakout"
        bw = [x for x in self.bbw[i - 119:i + 1] if x is not None]
        bbp = sum(1 for x in bw if x < self.bbw[i]) / len(bw) if bw and self.bbw[i] is not None else 1
        if a50 and (a200 or sl200 > 0) and hi52 > -0.10 and bbp <= 0.25 and last >= prev_hi20 * 0.96:
            return "coiled"
        rs = lambda k: (last / c[i - k] - 1) - (self.nc[i] / self.nc[i - k] - 1)
        pull = last / max(c[i - 19:i + 1]) - 1
        vs20 = last / m20[i] - 1
        r = self.rsi[i]
        if a50 and a200 and sl200 > 0 and rs(63) > 0 and -0.10 <= pull <= -0.03 and -0.04 <= vs20 <= 0.01 and r is not None and 38 <= r <= 58:
            return "pullback"
        rsl = [x for x in self.rsl[i - 62:i + 1] if x is not None]
        if (last / m200[i] - 1) <= 0.03 and a50 and a20 and m50[i] > m50[i - 10] and rs(21) > 0.02 and rsl and self.rsl[i] >= 0.995 * max(rsl):
            return "turn"
        return None


def metrics(S: "Series", i: int) -> dict | None:
    """Same fields and rules as the terminal's live model (lmCalc)."""
    c, h, l, nc = S.c, S.h, S.l, S.nc
    if i < 60:
        return None
    last = c[i]
    ret = lambda k: last / c[i - k] - 1 if i >= k else None
    nr = lambda k: nc[i] / nc[i - k] - 1 if i >= k else None
    rs = lambda k: ret(k) - nr(k) if ret(k) is not None else None
    m20, m50, m200 = S.m20[i], S.m50[i], S.m200[i]
    m200p = S.m200[i - 21] if i >= 21 else None
    m = {"last": last, "r1": ret(1), "r5": ret(5), "r21": ret(21), "r63": ret(63), "r126": ret(126),
         "rs1": rs(21), "rs3": rs(63), "rs6": rs(126),
         "mom": (c[i - 21] / c[i - 252] - 1) if i >= 252 else (c[i - 21] / c[0] - 1),
         "vs20": last / m20 - 1 if m20 else None, "vs50": last / m50 - 1 if m50 else None,
         "vs200": last / m200 - 1 if m200 else None, "sl200": m200 / m200p - 1 if m200 and m200p else None,
         "hi52": last / max(h[max(0, i - 249):i + 1]) - 1, "rsi": S.rsi[i]}
    k = S.tag(i)
    if k:
        prev_hi, lo10 = max(h[i - 20:i]), min(l[i - 9:i + 1])
        m["setup"] = k
        m["trig"] = h[i - 1] if k == "pullback" else prev_hi
        m["fail"] = m50 if k == "turn" else min(lo10, m50) if k == "pullback" else lo10
    return m


def rank_universe(M: dict) -> dict:
    """Add base score, status, final score and rank to {sym: metrics}."""
    def pct(f):
        v = sorted((m[f], s) for s, m in M.items() if m.get(f) is not None)
        return {s: (i / (len(v) - 1) if len(v) > 1 else .5) for i, (_, s) in enumerate(v)}
    R = {f: pct(f) for f, _ in W}
    for s, m in M.items():
        sc = w = 0.0
        for f, wt in W:
            if s in R[f]:
                sc += R[f][s] * wt
                w += wt
        base = 100 * sc / w if w else 50
        a20, a50, a200 = (m.get("vs20") or 0) > 0, (m.get("vs50") or 0) > 0, (m.get("vs200") or 0) > 0
        r1, r3 = m.get("rs1") or 0, m.get("rs3") or 0
        if not a50 and not a200:
            st_ = "weak"
        elif (r1 < -.02 or (not a20 and r1 < 0)) and (base >= 50 or (m.get("rs6") or 0) > 0):
            st_ = "fade"
        elif a20 and a50 and a200 and r3 > 0 and r1 > -.02 and m["hi52"] > -.15 and base >= 60:
            st_ = "lead"
        elif a20 and a50 and r1 > 0:
            st_ = "improve"
        else:
            st_ = "neutral"
        m["base"], m["status"] = base, st_
        m["score"] = round(max(0, base - 20 if st_ == "fade" else min(base, 35) if st_ == "weak" else base))
    for i, s in enumerate(sorted(M, key=lambda k: (-M[k]["score"], -M[k]["base"]))):
        M[s]["rank"] = i + 1
    return M


def backtest(stocks: dict, nifty: dict) -> dict:
    """stocks: {sym: {"d","c","h","l"}}; nifty: {"d","c"}."""
    nmap = dict(zip(nifty["d"], nifty["c"]))
    nd = nifty["d"]
    nm200 = dict(zip(nd, rolling_mean(nifty["c"], 200)))
    rows = {t: [] for t in TAGS}
    base = []
    for sym, o in stocks.items():
        keep = [i for i, d in enumerate(o["d"]) if d in nmap]
        d = [o["d"][i] for i in keep]
        c, h, l = ([o[k][i] for i in keep] for k in ("c", "h", "l"))
        v = [o["v"][i] for i in keep] if o.get("v") else None
        nc = [nmap[x] for x in d]
        if len(c) < 260:
            continue
        S = Series(c, h, l, nc, v)
        prev = None
        for i in range(200, len(c) - 21):
            t = S.tag(i)
            f10 = (c[i + 10] / c[i] - 1) - (nc[i + 10] / nc[i] - 1)
            f21 = (c[i + 21] / c[i] - 1) - (nc[i + 21] / nc[i] - 1)
            up = nm200.get(d[i]) is not None and nc[i] > nm200[d[i]]
            if i % 5 == 0:
                base.append((f10, f21, up))
            if t and t != prev:
                rows[t].append((f10, f21, up))
            prev = t

    def stats(r):
        if len(r) < 5:
            return {"n": len(r)}
        a10, a21 = [x[0] for x in r], [x[1] for x in r]
        sd = st.pstdev(a21) or 1e-9
        return {"n": len(r), "m10": round(st.mean(a10), 5), "m21": round(st.mean(a21), 5),
                "hit10": round(sum(x > 0 for x in a10) / len(r), 4), "hit21": round(sum(x > 0 for x in a21) / len(r), 4),
                "t21": round(st.mean(a21) / (sd / math.sqrt(len(r))), 2)}

    out = {"setups": {}, "base": {**stats(base), "up": stats([x for x in base if x[2]]), "weak": stats([x for x in base if not x[2]])}}
    for t in TAGS:
        out["setups"][t] = {**stats(rows[t]), "up": stats([x for x in rows[t] if x[2]]), "weak": stats([x for x in rows[t] if not x[2]])}
    return out


def main() -> int:
    import requests
    import refresh as R
    root = Path(sys.argv[sys.argv.index("--root") + 1]) if "--root" in sys.argv else Path(".")
    years = 6
    nset = R.read_nset((root / "docs/ra-desk.html").read_text(encoding="utf-8"))
    cid, pin, sec = (os.environ[k] for k in ("DHAN_CLIENT_ID", "DHAN_PIN", "DHAN_TOTP_SECRET"))
    dhan = R.Dhan(cid, R.login(cid, pin, sec))
    scrip = requests.get(R.SCRIP_MASTER, timeout=60).text
    big = "--n500" in sys.argv
    symbols = list(nset["stocks"])
    if big:
        import n500
        symbols = [u["s"] for u in n500.get_universe(dhan, root)]
    eq, ix = R.build_maps(scrip, symbols, ["Nifty 50"])
    end = dt.datetime.now(R.IST).date()
    start = end - dt.timedelta(days=365 * years + 30)

    def series(resp):
        ts = resp.get("timestamp") or []
        return {"d": [dt.datetime.fromtimestamp(t, R.IST).date().isoformat() for t in ts],
                "c": resp["close"], "h": resp["high"], "l": resp["low"], "v": resp.get("volume")}
    nifty = series(dhan.daily(ix["Nifty 50"], "IDX_I", "INDEX", start, end))
    stocks = {}
    for sym, sid in eq.items():
        try:
            stocks[sym] = series(dhan.daily(sid, "NSE_EQ", "EQUITY", start, end))
        except Exception as e:
            print(f"  skip {sym}: {e}")
    res = backtest(stocks, nifty)
    res.update({"asof": end.isoformat(), "from": nifty["d"][0] if nifty["d"] else None, "stocks": len(stocks),
                "universe": "Nifty 500" if big else "Nifty 50",
                "note": "Excess return vs Nifty after the first day a setup appears. Today's index members (survivorship bias). t is naive."})
    (root / ("docs/setup-backtest-n500.json" if big else "docs/setup-backtest.json")).write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
