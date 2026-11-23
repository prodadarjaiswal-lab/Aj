"""Gold Desk: one page for gold only, rebuilt from Dhan daily closes once a day.

Research software, not advice. Never places orders.

Data
  history   docs/gold/history.json: weekly gold in $/oz and Rs/10 g from 2000 (Rs from Dec 2003), silver, Nifty,
            plus the drawdown, Nifty-fall and portfolio studies, all copied from the Gold Desk artifact of 7 Nov 2026.
  daily     docs/gold/daily.json, from Dhan, kept and extended every run:
            GOLDBEES (NSE gold ETF) daily closes back to 2009, the nearest MCX GOLD future's daily closes,
            and the Nifty 50's daily closes.
Level check (before joining the two)
  GOLDBEES is in rupees per unit, not per 10 g, so it is scaled: k = median of (history Rs/10 g / GOLDBEES close)
  over the last 52 weeks both have. The spread of that ratio over the year and the MCX future's gap to the scaled
  series are shown on the page; a spread above 3% marks the join as unreliable.
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
    return out


def merge(old: dict, new: dict) -> dict:
    """Keep every close ever saved; new values win. MCX closes keep the contract they came from."""
    m = {k: dict(old.get(k) or {}) for k in ("bees", "nifty", "mcx", "mcx_contract")}
    for k in ("bees", "nifty"):
        m[k].update(new.get(k) or {})
    sym = new.get("mcx_contract")
    for d, c in (new.get("mcx") or {}).items():
        m["mcx"][d] = c
        m["mcx_contract"][d] = sym
    return {k: dict(sorted(v.items())) for k, v in m.items()}


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
def level_check(hist_w: list, bees: dict) -> dict:
    bd = sorted(bees)
    import bisect
    pairs = []
    for row in hist_w:
        d, inr = row[0], row[2]
        if not inr:
            continue
        j = bisect.bisect_right(bd, d) - 1
        if j >= 0 and (dt.date.fromisoformat(d) - dt.date.fromisoformat(bd[j])).days <= 4:
            pairs.append((d, inr / bees[bd[j]]))
    if len(pairs) < 20:
        raise RuntimeError(f"only {len(pairs)} weeks where the history and GOLDBEES overlap; cannot join them")
    last = [r for _, r in pairs[-52:]]
    k = float(np.median(last))
    return {"k": round(k, 3), "weeks": len(last), "from": pairs[-52:][0][0], "to": pairs[-1][0],
            "lo": round(min(last), 3), "hi": round(max(last), 3), "spread": round(max(last) / min(last) - 1, 4),
            "ok": max(last) / min(last) - 1 <= 0.03}


def build(hist: dict, daily: dict, asof: str) -> dict:
    bees = daily.get("bees") or {}
    if len(bees) < 300:
        raise RuntimeError(f"only {len(bees)} GOLDBEES closes; need 300+")
    L = level_check(hist["w"], bees)
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
    ath_d, ath = max(hw + list(zip(d, c.tolist())), key=lambda z: z[1])
    mcx = daily.get("mcx") or {}
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
    return {"asof": asof, "date": d[i], "f": f, "horizons": H, "proof": P, "level": L, "mcx": mx, "chart": chart,
            "long": long, "rets": rets, "daily_from": d[0], "daily_n": len(d),
            "studies": {k: hist.get(k) for k in ("gold_dd", "falls_nifty", "falls_nifty_big", "trend_strategy", "hedge")},
            "hist_source": hist.get("source"), "hist_asof": hist.get("asof")}


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
    print(f"level check: k={L['k']} over {L['weeks']} weeks, spread {L['spread']:.2%} ({'OK' if L['ok'] else 'TOO WIDE'}); "
          f"MCX {data['mcx'] and data['mcx']['c']} gap {data['mcx'] and data['mcx']['gap']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
