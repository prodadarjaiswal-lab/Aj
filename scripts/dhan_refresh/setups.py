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

TAGS = ("breakout", "coiled", "pullback", "turn")


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

    def __init__(self, c, h, l, nc):
        self.c, self.h, self.l, self.nc = c, h, l, nc
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
        nc = [nmap[x] for x in d]
        if len(c) < 260:
            continue
        S = Series(c, h, l, nc)
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
    eq, ix = R.build_maps(scrip, list(nset["stocks"]), ["Nifty 50"])
    end = dt.datetime.now(R.IST).date()
    start = end - dt.timedelta(days=365 * years + 30)

    def series(resp):
        ts = resp.get("timestamp") or []
        return {"d": [dt.datetime.fromtimestamp(t, R.IST).date().isoformat() for t in ts],
                "c": resp["close"], "h": resp["high"], "l": resp["low"]}
    nifty = series(dhan.daily(ix["Nifty 50"], "IDX_I", "INDEX", start, end))
    stocks = {}
    for sym, sid in eq.items():
        try:
            stocks[sym] = series(dhan.daily(sid, "NSE_EQ", "EQUITY", start, end))
        except Exception as e:
            print(f"  skip {sym}: {e}")
    res = backtest(stocks, nifty)
    res.update({"asof": end.isoformat(), "from": nifty["d"][0] if nifty["d"] else None, "stocks": len(stocks),
                "note": "Excess return vs Nifty after the first day a setup appears. Today's Nifty 50 members (survivorship bias). t is naive."})
    (root / "docs/setup-backtest.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
