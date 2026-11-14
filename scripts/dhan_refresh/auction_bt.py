"""Back-test of the auction / order-flow signals on Dhan 5-minute history (Nifty 50 stocks).

Each signal is a same-day trade from the bar where it triggers to the 15:25 close,
in the signal's direction (long or short), measured as excess over the Nifty 50
for the same window and net of 0.06% round-trip cost. It is "tested" only if the
net excess is positive in both halves of the sample, t >= 2 and 100+ cases.

Signals (decided only with data up to the trigger bar):
  ibx_up / ibx_dn      first 5-minute close outside the Initial Balance (09:15-10:15), after 10:15
  va_accept_up / _dn   opened outside yesterday's value area and was still outside it at 10:15 (acceptance)
  va_reject_up / _dn   opened outside yesterday's value but back inside it at 10:15 (rejection: fade the open)
  vwap_reclaim         after 30+ minutes below session VWAP, first close back above it (10:15-13:30)
  vwap_loss            the mirror: after 30+ minutes above, first close below
Uses 5-minute bars (Dhan intraday); the value area is the derived volume profile (see auction.py).
"""
from __future__ import annotations

import datetime as dt
import json
import math
import os
import statistics as st
import sys
from pathlib import Path

import auction as A

COST = 0.0006
IB_END = A.OPEN_MIN + 60
NAMES = {
    "ibx_up": "Breaks above the first hour's range (Initial Balance) after 10:15",
    "ibx_dn": "Breaks below the first hour's range after 10:15 (short)",
    "va_accept_up": "Opens above yesterday's value area and is still above it at 10:15",
    "va_accept_dn": "Opens below yesterday's value area and is still below it at 10:15 (short)",
    "va_reject_up": "Opens above yesterday's value but is back inside it at 10:15 (short, fade the open)",
    "va_reject_dn": "Opens below yesterday's value but is back inside it at 10:15 (long, fade the open)",
    "vwap_reclaim": "Closes back above session VWAP after 30+ minutes below (10:15-13:30)",
    "vwap_loss": "Closes back below session VWAP after 30+ minutes above (10:15-13:30, short)",
}
SIDE = {"ibx_up": 1, "ibx_dn": -1, "va_accept_up": 1, "va_accept_dn": -1, "va_reject_up": -1, "va_reject_dn": 1,
        "vwap_reclaim": 1, "vwap_loss": -1}


def session_signals(rows: list, prev_rows: list | None) -> dict:
    """{signal: entry bar index} for one session. rows: [(minute, o, h, l, c, v)] 5-minute bars."""
    out = {}
    if len(rows) < 40:
        return out
    ib = [r for r in rows if r[0] < IB_END]
    if not ib:
        return out
    ib_h, ib_l = max(r[2] for r in ib), min(r[3] for r in ib)
    i10 = next((i for i, r in enumerate(rows) if r[0] >= IB_END), None)
    if i10 is None:
        return out
    for i in range(i10, len(rows)):
        c = rows[i][4]
        if "ibx_up" not in out and c > ib_h and rows[i][0] < 15 * 60:
            out["ibx_up"] = i
        if "ibx_dn" not in out and c < ib_l and rows[i][0] < 15 * 60:
            out["ibx_dn"] = i
    if prev_rows and len(prev_rows) >= 40:
        tick = A.tick_for(prev_rows[-1][4])
        pv = A.volume_profile(prev_rows, tick)
        if pv["vah"] is not None:
            o, c10 = rows[0][1], rows[i10 - 1][4]
            if o > pv["vah"]:
                out["va_accept_up" if c10 > pv["vah"] else "va_reject_up"] = i10 - 1
            elif o < pv["val"]:
                out["va_accept_dn" if c10 < pv["val"] else "va_reject_dn"] = i10 - 1
    pv = vv = 0.0
    side_run, side = 0, 0
    for i, (m, _, h, l, c, v) in enumerate(rows):
        tp = (h + l + c) / 3
        pv, vv = pv + tp * v, vv + v
        if vv <= 0:
            continue
        w = pv / vv
        s = 1 if c > w else -1
        if IB_END <= m <= 13 * 60 + 30 and s != side and side_run >= 6:
            key = "vwap_reclaim" if s > 0 else "vwap_loss"
            out.setdefault(key, i)
        side_run = side_run + 1 if s == side else 1
        side = s
    return out


def backtest(stocks: dict, nifty: dict) -> dict:
    """stocks/nifty: {date: rows}. Returns per-signal stats with in/out-of-sample halves."""
    days = sorted(nifty)
    cut = days[len(days) // 2] if days else ""
    res = {k: [] for k in NAMES}
    base = []
    for sym, ses in stocks.items():
        ds = sorted(ses)
        for j, d in enumerate(ds):
            rows, nrows = ses[d], nifty.get(d)
            if not nrows:
                continue
            nmap = {r[0]: r[4] for r in nrows}
            prev = ses[ds[j - 1]] if j else None
            close, nclose = rows[-1][4], nrows[-1][4]

            def ex(i):
                m = rows[i][0]
                nm = nmap.get(m)
                if not nm:
                    return None
                return (close / rows[i][4] - 1) - (nclose / nm - 1)
            if len(rows) > 20:
                x = ex(len(rows) // 3)
                if x is not None:
                    base.append((x, d >= cut))
            for k, i in session_signals(rows, prev).items():
                x = ex(i)
                if x is not None:
                    res[k].append((SIDE[k] * x - COST, d >= cut))
    out = {"cutoff": cut, "days": len(days), "cost": COST, "signals": {}}

    def stats(a):
        if len(a) < 30:
            return {"n": len(a)}
        m, sd = st.mean(a), st.pstdev(a) or 1e-9
        return {"n": len(a), "net": round(m, 5), "hit": round(sum(x > 0 for x in a) / len(a), 4), "t": round(m / (sd / math.sqrt(len(a))), 2)}
    out["base_drift"] = stats([x for x, _ in base])
    for k, rows in res.items():
        i_, o_ = stats([x for x, oos in rows if not oos]), stats([x for x, oos in rows if oos])
        tested = bool(i_.get("net", -1) > 0 and o_.get("net", -1) > 0 and o_.get("t", 0) >= 2 and o_.get("n", 0) >= 100)
        out["signals"][k] = {"in": i_, "out": o_, "tested": tested, "name": NAMES[k]}
    return out


# ---------------------------------------------------------------- swing test: end-of-day order-flow / auction states
SWING = {
    "sw_va_up": "Closed above yesterday's value area (auction accepted higher)",
    "sw_poc_up": "Today's point of control moved above yesterday's value area",
    "sw_vwap_buy": "Closed above VWAP all afternoon with buyers at 55%+ of volume (delta estimate)",
    "sw_ib_up": "Extended above the first hour's range and closed above it",
    "sw_absorb": "Closed in the top third after trading below yesterday's value (sellers absorbed)",
    "sw_cvd_div": "Price fell on the day but estimated delta was positive (bullish divergence)",
    "sw_va_dn": "Closed below yesterday's value area (warning)",
}
SWING_WARN = ("sw_va_dn",)
SWING_H = (5, 10)


def day_flags(rows: list, prev_rows: list | None) -> set:
    """End-of-day states from one session's intraday bars [(minute, o, h, l, c, v)] and the previous session."""
    out = set()
    if len(rows) < 30:
        return out
    tick = A.tick_for(rows[-1][4])
    close, hi, lo = rows[-1][4], max(r[2] for r in rows), min(r[3] for r in rows)
    vp = A.volume_profile(rows, tick)
    de = A.delta_est(rows)
    vw = A.vwap(rows)
    ib = [r for r in rows if r[0] < IB_END]
    if ib:
        ib_h = max(r[2] for r in ib)
        if hi > ib_h and close > ib_h:
            out.add("sw_ib_up")
    pvv = cum = 0.0
    above_pm = True
    for m, _, h, l, c, v in rows:
        pvv, cum = pvv + (h + l + c) / 3 * v, cum + v
        if m >= 13 * 60 and cum > 0 and c < pvv / cum:
            above_pm = False
    if above_pm and vw.get("vwap") and close > vw["vwap"] and (de.get("buy_share_est") or 0) >= 0.55:
        out.add("sw_vwap_buy")
    if (de.get("cum_delta_est") or 0) > 0 and close < rows[0][1]:
        out.add("sw_cvd_div")
    if prev_rows and len(prev_rows) >= 30:
        pv = A.volume_profile(prev_rows, A.tick_for(prev_rows[-1][4]))
        if pv["vah"] is not None:
            if close > pv["vah"]:
                out.add("sw_va_up")
            if close < pv["val"]:
                out.add("sw_va_dn")
            if vp.get("poc") is not None and vp["poc"] > pv["vah"]:
                out.add("sw_poc_up")
            if lo < pv["val"] and hi > lo and (close - lo) / (hi - lo) >= 0.67 and close >= pv["val"]:
                out.add("sw_absorb")
    return out


def swing_backtest(stocks: dict, nifty: dict) -> dict:
    """Hold from the close for 5 and 10 sessions; excess over the Nifty; lift over the average stock-day.
    Passes: lift positive in both halves, t >= 2 on the later half after an overlap adjustment, 100+ cases."""
    days = sorted(nifty)
    cut = days[len(days) // 2] if days else ""
    nclose = {d: nifty[d][-1][4] for d in days}
    res = {(k, h): [] for k in SWING for h in SWING_H}
    base = {h: [] for h in SWING_H}
    for sym, ses in stocks.items():
        ds = [d for d in sorted(ses) if d in nclose]
        cl = [ses[d][-1][4] for d in ds]
        for j in range(1, len(ds)):
            fl = day_flags(ses[ds[j]], ses[ds[j - 1]])
            for h in SWING_H:
                if j + h >= len(ds) or not cl[j]:
                    continue
                x = (cl[j + h] / cl[j] - 1) - (nclose[ds[j + h]] / nclose[ds[j]] - 1)
                base[h].append((x, ds[j] >= cut))
                for k in fl:
                    res[(k, h)].append((x, ds[j] >= cut))
    out = {"cutoff": cut, "names": SWING, "signals": {}}
    mean = lambda a: sum(a) / len(a) if a else 0.0
    for k in SWING:
        r = {"name": SWING[k], "tested": False, "h": None}
        for h in SWING_H:
            b_in, b_out = mean([x for x, o in base[h] if not o]), mean([x for x, o in base[h] if o])
            a_in, a_out = [x for x, o in res[(k, h)] if not o], [x for x, o in res[(k, h)] if o]
            if len(a_in) < 30 or len(a_out) < 30:
                r[str(h)] = {"n": len(a_in) + len(a_out)}
                continue
            li, lo_ = mean(a_in) - b_in, mean(a_out) - b_out
            sd = st.pstdev(a_out) or 1e-9
            t = lo_ / (sd / math.sqrt(len(a_out))) / math.sqrt(h)
            r[str(h)] = {"n": len(a_in) + len(a_out), "n_out": len(a_out), "lift_in": round(li, 5), "lift_out": round(lo_, 5),
                         "t": round(t, 2), "hit_out": round(sum(x > 0 for x in a_out) / len(a_out), 3)}
            good = (li < 0 and lo_ < 0 and t <= -2) if k in SWING_WARN else (li > 0 and lo_ > 0 and t >= 2)
            if good and len(a_out) >= 100 and not r["tested"]:
                r["tested"], r["h"] = True, h
        out["signals"][k] = r
    return out


def fetch(dhan, symbols: list, months: int = 12):
    """5-minute bars in 60-day chunks."""
    import refresh as R
    import requests
    scrip = requests.get(R.SCRIP_MASTER, timeout=60).text
    eq, ix = R.build_maps(scrip, symbols, ["Nifty 50"])
    end = dt.datetime.now(R.IST)

    def bars(sid, seg, inst):
        t, o, h, l, c, v = [], [], [], [], [], []
        s = end - dt.timedelta(days=30 * months)
        while s < end:
            e = min(s + dt.timedelta(days=60), end)
            r = dhan.post("/charts/intraday", {"securityId": str(sid), "exchangeSegment": seg, "instrument": inst, "interval": "5",
                                               "oi": False, "fromDate": s.strftime("%Y-%m-%d 09:00:00"), "toDate": e.strftime("%Y-%m-%d 16:00:00")})
            for key, arr in (("timestamp", t), ("open", o), ("high", h), ("low", l), ("close", c), ("volume", v)):
                arr.extend(r.get(key) or [])
            s = e
        return A.sessions({"t": t, "o": o, "h": h, "l": l, "c": c, "v": v or [0] * len(t)})
    nifty = bars(ix["Nifty 50"], "IDX_I", "INDEX")
    stocks = {}
    for sym, sid in eq.items():
        try:
            stocks[sym] = bars(sid, "NSE_EQ", "EQUITY")
        except Exception as e:
            print(f"  skip {sym}: {str(e)[:80]}")
    return stocks, nifty


def main() -> int:
    import refresh as R
    root = Path(sys.argv[sys.argv.index("--root") + 1]) if "--root" in sys.argv else Path("../..")
    nset = R.read_nset((root / "docs/nse-terminal.html").read_text(encoding="utf-8"))
    cid, pin, sec = (os.environ[k] for k in ("DHAN_CLIENT_ID", "DHAN_PIN", "DHAN_TOTP_SECRET"))
    dhan = R.Dhan(cid, R.login(cid, pin, sec))
    stocks, nifty = fetch(dhan, list(nset["stocks"]))
    res = backtest(stocks, nifty)
    res["swing"] = swing_backtest(stocks, nifty)
    res["swing"]["note"] = ("End-of-day states from 5-minute Dhan bars, bought at the close and held 5 or 10 sessions; excess over "
                            "the Nifty 50 minus the average stock-day. Nifty 50 members today, 12 months.")
    res.update({"asof": max(nifty) if nifty else None, "from": min(nifty) if nifty else None, "stocks": len(stocks),
                "note": "Same-day trade from the trigger bar to the close, in the signal's direction, excess over Nifty 50, "
                        "net of 0.06% round trip. 5-minute Dhan bars; Nifty 50 members today."})
    (root / "docs/auction-backtest.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    for k, r in res["signals"].items():
        print(f"{k:13s} tested={r['tested']!s:5s} in={r['in']} out={r['out']}")
    for k, r in res["swing"]["signals"].items():
        print(f"{k:12s} tested={r['tested']!s:5s} 5d={r.get('5')} 10d={r.get('10')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
