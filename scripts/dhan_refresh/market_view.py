"""Market view: test the popular "what to buy in this kind of market" beliefs on back-dated Dhan data, out of sample,
and turn the ones that hold into tomorrow's view. Research software, not advice. Never places orders.

Pre-registered rules (written 26 Nov 2026 before any result was seen; do not loosen them after a bad run):
  * Market type on each day, known at that day's close (Nifty 50):
        rising   close above the 200-day average and up 3%+ over 63 sessions
        falling  close below the 200-day average and down 3%+ over 63 sessions
        flat     63-session change within +/-3% (the "slow / stagnant" market)
        turning  anything else (a pullback inside an uptrend, or a bounce inside a downtrend)
  * Outcome: forward return from the signal day's close minus the Nifty 50's over the same days. Stock baskets pay
    0.25% round-trip delivery charges; index views are compared gross (an index ETF costs a few basis points).
  * Split: in-sample = everything before the last 3 years; out-of-sample (OOS) = the last 3 years.
  * Overlapping windows are not independent, so every statistic is clustered by calendar month:
    t = mean of the monthly averages / its standard error.
  * HOLDS only if the in-sample mean has the claimed sign with t >= 2, the OOS mean has the claimed sign with a
    one-sided p-value that survives Holm's correction across every belief tested here, and OOS has 12+ months.
    FAILS when the OOS mean has the wrong sign. Anything else is UNPROVEN (right sign, not enough evidence).
  * Survivorship: today's index members and today's listed stocks. Exchange / broker stocks listed in 2017-2022,
    so their history is short and the verdict says so.
  * Walk-forward forecasts (the "how often the forecast was right" numbers) only use data that existed before
    each forecast date.
Writes docs/market-view.json and docs/market-view.md.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import os
import sys
from pathlib import Path

H = 21                  # one month of sessions
OOS_YEARS = 3.0
COST_STOCK = 0.0025
FLAT_BAND = 0.03
MIN_OOS_MONTHS = 12

IDX_IDS = {"Nifty 50": 13, "Nifty Bank": 25, "Nifty IT": 29, "Nifty FMCG": 28, "Nifty Pharma": 32, "Nifty Auto": 14,
           "Nifty Metal": 31, "Nifty Realty": 34, "Nifty Energy": 42, "Nifty PSU Bank": 33,
           "Nifty Financial Services": 27, "Nifty Midcap 100": 37, "India VIX": 21}
EXTRA_IDX = ["Nifty Infrastructure", "Nifty Media", "Nifty Private Bank", "Nifty PSE", "Nifty Commodities",
             "Nifty India Consumption", "Nifty Next 50", "Nifty Smallcap 100"]
# exchanges, depositories, brokers, registrars and AMCs: the stocks people buy "when the market is slow"
CAPMKT = ["BSE", "MCX", "CDSL", "ANGELONE", "CAMS", "KFINTECH", "HDFCAMC", "NUVAMA", "360ONE", "IEX", "NAM-INDIA",
          "UTIAMC", "MOTILALOFS", "IIFL"]
NOT_SECTORS = {"Nifty 50", "India VIX"}
REGIMES = ["rising", "flat", "turning", "falling"]
REGIME_TEXT = {"rising": "Rising market", "flat": "Flat / slow market", "turning": "Turning market",
               "falling": "Falling market"}


# ---------------------------------------------------------------- pure helpers (tested offline)
def align(series: dict, base: str = "Nifty 50") -> tuple[list, dict]:
    """series: name -> {"d": [iso dates], "c": [closes]}. Returns base dates and name -> closes on those dates (None = missing)."""
    days = series[base]["d"]
    out = {}
    for k, s in series.items():
        m = {d: c for d, c in zip(s["d"], s["c"]) if c}
        out[k] = [m.get(d) for d in days]
    return days, out


def sma(x: list, n: int, i: int):
    w = x[i - n + 1:i + 1] if i >= n - 1 else []
    return sum(w) / n if len(w) == n and all(w) else None


def regimes(n: list) -> list:
    out = []
    for i in range(len(n)):
        s200 = sma(n, 200, i)
        if s200 is None or i < 63 or not n[i - 63]:
            out.append(None)
            continue
        r63 = n[i] / n[i - 63] - 1
        if abs(r63) <= FLAT_BAND:
            out.append("flat")
        elif n[i] > s200 and r63 > 0:
            out.append("rising")
        elif n[i] < s200 and r63 < 0:
            out.append("falling")
        else:
            out.append("turning")
    return out


def fwd(x: list, i: int, h: int):
    if i + h >= len(x) or not x[i] or not x[i + h]:
        return None
    return x[i + h] / x[i] - 1


def basket_fwd(cols: list, i: int, h: int):
    rs = [r for r in (fwd(c, i, h) for c in cols) if r is not None]
    return sum(rs) / len(rs) if rs else None


def norm_sf(z: float) -> float:
    """One-sided upper-tail p-value of a standard normal (months are many enough for the normal approximation)."""
    return 0.5 * math.erfc(z / math.sqrt(2))


def monthly(cases: list) -> dict:
    """cases: [(iso_date, value)]. Clustered statistics by calendar month."""
    by = {}
    for d, v in cases:
        by.setdefault(d[:7], []).append(v)
    ms = [sum(v) / len(v) for v in by.values()]
    n = len(ms)
    if n == 0:
        return {"n": 0, "months": 0, "mean": None, "t": None, "hit": None}
    mean = sum(ms) / n
    sd = math.sqrt(sum((m - mean) ** 2 for m in ms) / (n - 1)) if n > 1 else 0.0
    t = mean / (sd / math.sqrt(n)) if n > 1 and sd > 0 else None
    hit = sum(v > 0 for _, v in cases) / len(cases)
    return {"n": len(cases), "months": n, "mean": round(mean, 5), "t": round(t, 2) if t is not None else None,
            "hit": round(hit, 3)}


def split_date(days: list, years: float = OOS_YEARS) -> str:
    last = dt.date.fromisoformat(days[-1])
    return (last - dt.timedelta(days=int(365.25 * years))).isoformat()


def test(cases: list, cut: str, sign: int = 1) -> dict:
    """sign=+1: the belief says the value is positive; -1: negative. Values are flipped so 'right' is always > 0."""
    ins = [(d, sign * v) for d, v in cases if d < cut]
    oos = [(d, sign * v) for d, v in cases if d >= cut]
    a, b = monthly(ins), monthly(oos)
    b["p"] = round(norm_sf(b["t"]), 4) if b["t"] is not None else None
    for s in (a, b):                                   # report means in the belief's own direction, as raw numbers
        if s["mean"] is not None:
            s["raw_mean"] = round(sign * s["mean"], 5)
    return {"is": a, "oos": b, "first": cases[0][0] if cases else None}


def holm(results: list, alpha: float = 0.05) -> None:
    """Mark r['pass_holm'] on each result dict, in place, with Holm's step-down over the OOS one-sided p-values."""
    ps = sorted([(r["oos"]["p"], k) for k, r in enumerate(results) if r["oos"].get("p") is not None])
    m = len(ps)
    for r in results:
        r["pass_holm"] = False
    for j, (p, k) in enumerate(ps):
        if p > alpha / (m - j):
            break
        results[k]["pass_holm"] = True


def verdict(r: dict) -> str:
    a, b = r["is"], r["oos"]
    if b["months"] < MIN_OOS_MONTHS or b["mean"] is None:
        return "UNPROVEN"
    if b["mean"] <= 0:
        return "FAILS"
    if a["mean"] is not None and a["mean"] > 0 and (a["t"] or 0) >= 2 and r.get("pass_holm"):
        return "HOLDS"
    return "UNPROVEN"


# ---------------------------------------------------------------- the beliefs
def beliefs(days: list, X: dict, reg: list, cap_cols: list) -> list:
    """Every belief is a list of (date, value) cases plus the sign the belief predicts."""
    N = X["Nifty 50"]
    sectors = [k for k in X if k not in NOT_SECTORS]
    out = []

    def add(key, title, plain, cases, sign=1, horizon=H, note=""):
        out.append({"key": key, "title": title, "plain": plain, "sign": sign, "h": horizon, "cases": cases, "note": note})

    def ex(col, i, h=H, cost=0.0):
        a, b = fwd(col, i, h), fwd(N, i, h)
        return None if a is None or b is None else a - b - cost

    rng = range(len(days))
    bank = X.get("Nifty Bank")
    if bank:
        add("bank_flat", "Bank Nifty is the index to buy in a flat market",
            "In a flat / slow market, Nifty Bank beats the Nifty 50 over the next month.",
            [(days[i], v) for i in rng if reg[i] == "flat" and (v := ex(bank, i)) is not None])
        add("bank_always", "Bank Nifty is a no-brainer (beats the Nifty in any market)",
            "On any day, Nifty Bank beats the Nifty 50 over the next month.",
            [(days[i], v) for i in rng if reg[i] and (v := ex(bank, i)) is not None])
        lead = []
        for i in rng:
            b5, n5, nf = fwd(bank, i - 5, 5) if i >= 5 else None, fwd(N, i - 5, 5) if i >= 5 else None, fwd(N, i, 5)
            if None not in (b5, n5, nf) and abs(b5 - n5) >= 0.01:
                lead.append((days[i], nf if b5 > n5 else -nf))
        add("bank_leads", "Bank Nifty leads the Nifty",
            "When Nifty Bank beat the Nifty by 1%+ over the last 5 sessions, the Nifty rises over the next 5 "
            "(and falls after Bank Nifty lags by 1%+).", lead, horizon=5)
    if cap_cols:
        add("capmkt_flat", "Exchange, broker and AMC stocks win in a slow market",
            "In a flat market, an equal basket of " + ", ".join(CAPMKT[:6]) + " and peers beats the Nifty over the "
            "next month after 0.25% charges.",
            [(days[i], v) for i in rng if reg[i] == "flat" and (b := basket_fwd(cap_cols, i, H)) is not None
             and (n := fwd(N, i, H)) is not None and (v := b - n - COST_STOCK) is not None],
            note="Most of these stocks listed between 2017 and 2022, so the in-sample period is short.")
    # Nifty mean reversion (ADARSH's view: India reverts more than it trends)
    def nx5(i):                       # Nifty's next 5 sessions minus its average 5-session move over the past year
        f = fwd(N, i, 5)
        if f is None or i < 262:
            return None
        past = [r for j in range(i - 262, i - 10) if (r := fwd(N, j, 5)) is not None]
        return f - sum(past) / len(past) if past else None
    add("nifty_bounce", "After a sharp fall the Nifty bounces",
        "After the Nifty falls 3%+ in 5 sessions, its next 5 sessions are better than usual.",
        [(days[i], v) for i in rng if i >= 5 and (p := fwd(N, i - 5, 5)) is not None and p <= -0.03
         and (v := nx5(i)) is not None], horizon=5)
    add("nifty_fade", "After a sharp rise the Nifty gives some back",
        "After the Nifty rises 3%+ in 5 sessions, its next 5 sessions are worse than usual.",
        [(days[i], v) for i in rng if i >= 5 and (p := fwd(N, i - 5, 5)) is not None and p >= 0.03
         and (v := nx5(i)) is not None], sign=-1, horizon=5)
    # sector reversal vs momentum, rebalanced monthly on non-overlapping steps
    rev, mom, laggard = [], [], []
    for i in range(252, len(days), H):
        r1 = {k: (fwd(X[k], i - H, H), ex(X[k], i)) for k in sectors}
        r6 = {k: (fwd(X[k], i - 126, 126), ex(X[k], i)) for k in sectors}
        ok1 = {k: v for k, v in r1.items() if None not in v}
        ok6 = {k: v for k, v in r6.items() if None not in v}
        if len(ok1) >= 5:
            rev.append((days[i], min(ok1.items(), key=lambda kv: kv[1][0])[1][1]))
        if len(ok6) >= 5:
            mom.append((days[i], max(ok6.items(), key=lambda kv: kv[1][0])[1][1]))
    add("sector_reversal", "Last month's worst sector bounces (mean reversion)",
        "Buying the sector index that did worst last month beats the Nifty over the next month.", rev)
    add("sector_momentum", "The strongest sector keeps winning (momentum)",
        "Buying the sector index that did best over the last 6 months beats the Nifty over the next month.", mom)
    # "IT is cheap": a sector that lagged the Nifty by 15%+ over a year catches up over the next 6 months
    for i in range(252, len(days), H):
        for k in sectors:
            a, b = fwd(X[k], i - 252, 252), fwd(N, i - 252, 252)
            if a is not None and b is not None and a - b <= -0.15 and (v := ex(X[k], i, 126)) is not None:
                laggard.append((days[i], v))
    add("laggard_catchup", "A sector that lagged for a year is cheap and catches up",
        "A sector index that trailed the Nifty by 15%+ over 12 months beats it over the next 6 months "
        "(the shape of the 'IT is cheap' view).", laggard, horizon=126,
        note="Price-based proxy: index P/E history is not in the data yet.")
    return out


def sector_table(days: list, X: dict, reg: list, cut: str) -> dict:
    """Mean 1-month excess vs Nifty for each sector in each market type, in-sample and OOS."""
    N = X["Nifty 50"]
    tab = {}
    for k in X:
        if k in NOT_SECTORS:
            continue
        tab[k] = {}
        for r in REGIMES:
            cases = [(days[i], fwd(X[k], i, H) - fwd(N, i, H)) for i in range(len(days))
                     if reg[i] == r and fwd(X[k], i, H) is not None and fwd(N, i, H) is not None]
            t = test(cases, cut)
            tab[k][r] = {"is": t["is"]["mean"], "oos": t["oos"]["mean"], "is_t": t["is"]["t"], "oos_t": t["oos"]["t"],
                         "oos_hit": t["oos"]["hit"], "oos_months": t["oos"]["months"]}
    return tab


def walk_rotation(days: list, X: dict, reg: list, start: int = 756) -> dict:
    """Each month: in today's market type, hold the sector with the best average 1-month excess in that market
    type using only windows that had fully finished before today. Returns the forecast record."""
    N = X["Nifty 50"]
    sectors = [k for k in X if k not in NOT_SECTORS]
    acc = {r: {k: [0.0, 0] for k in sectors} for r in REGIMES}
    recs, j = [], 0
    for i in range(start, len(days) - H, H):
        while j + H <= i:                                  # windows that ended by day i are known
            if reg[j]:
                for k in sectors:
                    a, b = fwd(X[k], j, H), fwd(N, j, H)
                    if a is not None and b is not None:
                        acc[reg[j]][k][0] += a - b
                        acc[reg[j]][k][1] += 1
            j += 1
        r = reg[i]
        if not r:
            continue
        cand = {k: s / n for k, (s, n) in acc[r].items() if n >= 60 and fwd(X[k], i, H) is not None}
        if not cand:
            continue
        pick = max(cand, key=cand.get)
        recs.append({"d": days[i], "regime": r, "pick": pick, "ex": round(fwd(X[pick], i, H) - fwd(N, i, H), 5)})
    m = monthly([(x["d"], x["ex"]) for x in recs])
    m["p"] = round(norm_sf(m["t"]), 4) if m["t"] is not None else None
    return {"record": recs, "stats": m, "start": recs[0]["d"] if recs else None}


def next_day(days: list, N: list, reg: list, start: int = 756) -> dict:
    """Walk-forward next-session direction: P(up) in today's (market type, today's move) bucket from earlier days only."""
    def bucket(i):
        r = N[i] / N[i - 1] - 1
        return (reg[i], "down" if r <= -0.01 else "up" if r >= 0.01 else "quiet")
    cnt, right, base_right, total, last = {}, 0, 0, 0, None
    for i in range(201, len(days) - 1):
        if not reg[i] or not N[i + 1]:
            continue
        b = bucket(i)
        up = N[i + 1] > N[i]
        if i >= start:
            u, n = cnt.get(b, (0, 0))
            p_up = (u + 1) / (n + 2)
            right += (p_up >= 0.5) == up
            base_right += up
            total += 1
        u, n = cnt.get(b, (0, 0))
        cnt[b] = (u + up, n + 1)
    i = len(days) - 1
    if reg[i]:
        u, n = cnt.get(bucket(i), (0, 0))
        last = {"bucket": list(bucket(i)), "p_up": round((u + 1) / (n + 2), 3), "n": n}
    return {"accuracy": round(right / total, 3) if total else None,
            "always_up": round(base_right / total, 3) if total else None, "days": total, "today": last}


def downside(days: list, X: dict, reg: list, a: str, b: str, r: str, cut: str) -> dict:
    """How often a month in market type r lost 5%+ for index a vs index b (the 'safest' part of the claim)."""
    out = {}
    for part, keep in (("is", lambda d: d < cut), ("oos", lambda d: d >= cut)):
        ra = [fwd(X[a], i, H) for i in range(len(days)) if reg[i] == r and keep(days[i]) and fwd(X[a], i, H) is not None]
        rb = [fwd(X[b], i, H) for i in range(len(days)) if reg[i] == r and keep(days[i]) and fwd(X[b], i, H) is not None]
        out[part] = {a: round(sum(x <= -0.05 for x in ra) / len(ra), 3) if ra else None,
                     b: round(sum(x <= -0.05 for x in rb) / len(rb), 3) if rb else None}
    return out


def corr(x: list, y: list) -> float | None:
    p = [(a, b) for a, b in zip(x, y) if a is not None and b is not None]
    if len(p) < 30:
        return None
    ma, mb = sum(a for a, _ in p) / len(p), sum(b for _, b in p) / len(p)
    va, vb = sum((a - ma) ** 2 for a, _ in p), sum((b - mb) ** 2 for _, b in p)
    return round(sum((a - ma) * (b - mb) for a, b in p) / math.sqrt(va * vb), 3) if va and vb else None



# ---------------------------------------------------------------- risk, options maths and the low-risk screen
RF = 0.065              # risk-free rate for Sharpe (91-day T-bill, roughly)
FACTOR_KEYS = {"LOWVOL": "Low volatility", "LOWVOLATILITY": "Low volatility", "MOMENTM": "Momentum",
               "MOMENTUM": "Momentum", "QUALITY": "Quality", "QLTY": "Quality", "VALUE": "Value",
               "ALPHA": "Alpha", "DIVOPP": "Dividend", "EQUALWEIGHT": "Equal weight", "EQLWGT": "Equal weight"}


def factor_ids(scrip_csv: str) -> dict:
    """NSE factor (smart-beta) indices in Dhan's list: name -> security id. Names vary, so match keywords."""
    import csv
    import io
    out = {}
    for r in csv.DictReader(io.StringIO(scrip_csv)):
        if r.get("SEM_EXM_EXCH_ID") != "NSE" or r.get("SEM_INSTRUMENT_NAME") != "INDEX":
            continue
        name = (r.get("SM_SYMBOL_NAME") or r.get("SEM_TRADING_SYMBOL") or "").strip()
        key = "".join(ch for ch in name.upper() if ch.isalnum())
        if any(k in key for k in FACTOR_KEYS) and name not in out:
            out[name] = r["SEM_SMST_SECURITY_ID"]
    return out


def ncdf(x: float) -> float:
    return 0.5 * math.erfc(-x / math.sqrt(2))


def risk_stats(c: list, n: list, lo: int, hi: int) -> dict | None:
    """Annual return, volatility, Sharpe, Sortino, max drawdown, beta and correlation to the Nifty, days lo..hi."""
    p = [(c[i], n[i], c[i - 1], n[i - 1]) for i in range(max(lo, 1), hi + 1) if c[i] and c[i - 1] and n[i] and n[i - 1]]
    if len(p) < 120:
        return None
    r = [a / b - 1 for a, _, b, _ in p]
    m = [a / b - 1 for _, a, _, b in p]
    k = len(r)
    mu, mm = sum(r) / k, sum(m) / k
    sd = math.sqrt(sum((x - mu) ** 2 for x in r) / (k - 1))
    dn = math.sqrt(sum(min(0.0, x) ** 2 for x in r) / k)
    vm = sum((x - mm) ** 2 for x in m) / (k - 1)
    cov = sum((x - mu) * (y - mm) for x, y in zip(r, m)) / (k - 1)
    eq, peak, dd = 1.0, 1.0, 0.0
    for x in r:
        eq *= 1 + x
        peak = max(peak, eq)
        dd = min(dd, eq / peak - 1)
    ann = eq ** (252 / k) - 1
    vol = sd * math.sqrt(252)
    return {"ret": round(ann, 4), "vol": round(vol, 4), "sharpe": round((ann - RF) / vol, 2) if vol else None,
            "sortino": round((ann - RF) / (dn * math.sqrt(252)), 2) if dn else None, "maxdd": round(dd, 4),
            "beta": round(cov / vm, 2) if vm else None, "corr": round(cov / math.sqrt(vm) / sd, 2) if vm and sd else None}


def risk_table(days: list, X: dict, cut: str) -> list:
    k0 = next(i for i, d in enumerate(days) if d >= cut)
    out = []
    for k, c in X.items():
        if k == "India VIX":
            continue
        a, b = risk_stats(c, X["Nifty 50"], 1, k0 - 1), risk_stats(c, X["Nifty 50"], k0, len(days) - 1)
        if b:
            out.append({"k": k, "is": a, "oos": b})
    return sorted(out, key=lambda r: -(r["oos"]["sharpe"] or -9))


def vix_range(days: list, X: dict) -> dict | None:
    """Black-Scholes reading of India VIX: the market's own 1-day and 1-month ranges for the Nifty, and how often
    the Nifty actually stayed inside them (a calibrated range covers about 68% of days at 1 sigma)."""
    v, n = X.get("India VIX"), X["Nifty 50"]
    if not v:
        return None
    in1 = in2 = tot = big = big_pred = 0
    for i in range(len(days) - 1):
        if v[i] and n[i] and n[i + 1]:
            s = v[i] / 100 / math.sqrt(252)
            mv = abs(n[i + 1] / n[i] - 1)
            in1 += mv <= s
            in2 += mv <= 2 * s
            big += mv >= 0.015
            big_pred += 2 * (1 - ncdf(0.015 / s))
            tot += 1
    s1, s21 = v[-1] / 100 / math.sqrt(252), v[-1] / 100 * math.sqrt(21 / 252)
    return {"vix": round(v[-1], 2), "nifty": round(n[-1], 2), "day_pts": round(n[-1] * s1), "month_pts": round(n[-1] * s21),
            "p_move15": round(2 * (1 - ncdf(0.015 / s1)), 3), "hit1": round(in1 / tot, 3), "hit2": round(in2 / tot, 3),
            "big_actual": round(big / tot, 3), "big_implied": round(big_pred / tot, 3), "days": tot}


def screen_scores(cols: dict, i: int) -> dict:
    """sym -> (score, vol, mom) at day i: 12-1 month momentum divided by 1-year volatility (a trailing Sharpe)."""
    out = {}
    for s, c in cols.items():
        w = c[i - 252:i + 1] if i >= 252 else []
        if len(w) < 253 or not all(w):
            continue
        r = [w[j] / w[j - 1] - 1 for j in range(1, len(w))]
        mu = sum(r) / len(r)
        vol = math.sqrt(sum((x - mu) ** 2 for x in r) / (len(r) - 1)) * math.sqrt(252)
        mom = w[-22] / w[0] - 1
        if vol > 0:
            out[s] = ((mom - RF) / vol, vol, mom)
    return out


def calm_strong(sc: dict, top: int = 20) -> list:
    """Low risk, high return: the calmer half of stocks by volatility, then the best trailing Sharpe."""
    if len(sc) < 40:
        return []
    vols = sorted(v[1] for v in sc.values())
    med = vols[len(vols) // 2]
    calm = [(s, v) for s, v in sc.items() if v[1] <= med]
    return [s for s, _ in sorted(calm, key=lambda kv: -kv[1][0])[:top]]


def screen_test(days: list, N: list, cols: dict) -> tuple[list, list]:
    """Monthly, non-overlapping: the calm-and-strong 20 and the calmest 20%, each vs the Nifty after charges."""
    cs, lv = [], []
    for i in range(252, len(days) - H, H):
        sc = screen_scores(cols, i)
        n = fwd(N, i, H)
        if n is None or len(sc) < 40:
            continue
        for pick, out in ((calm_strong(sc), cs), ([s for s, _ in sorted(sc.items(), key=lambda kv: kv[1][1])[:max(1, len(sc) // 5)]], lv)):
            rs = [r for s in pick if (r := fwd(cols[s], i, H)) is not None]
            if rs:
                out.append((days[i], sum(rs) / len(rs) - n - COST_STOCK))
    return cs, lv


def screen_today(days: list, N: list, cols: dict, top: int = 15) -> list:
    i = len(days) - 1
    sc = screen_scores(cols, i)
    rows = []
    for s in calm_strong(sc, top):
        st = risk_stats(cols[s], N, i - 251, i) or {}
        rows.append({"s": s, "score": round(sc[s][0], 2), "vol": round(sc[s][1], 3), "mom": round(sc[s][2], 3),
                     "maxdd": st.get("maxdd"), "beta": st.get("beta"), "sharpe": st.get("sharpe")})
    return rows



# ---------------------------------------------------------------- hedged trading ideas (index legs only)
COST_PAIR = 0.001        # both legs of an index-futures pair, in and out (brokerage, STT on futures sells, exchange)
CONDOR_HAIRCUT = 0.85    # keep only 85% of the Black-Scholes credit: real out-of-the-money puts trade at a higher
                         # implied volatility than VIX (skew) and fills are worse than mid; pre-registered, not tuned


def beta(a: list, n: list, i: int, look: int = 252) -> float | None:
    p = [(a[j] / a[j - 1] - 1, n[j] / n[j - 1] - 1) for j in range(max(1, i - look + 1), i + 1)
         if a[j] and a[j - 1] and n[j] and n[j - 1]]
    if len(p) < 120:
        return None
    mx, my = sum(y for _, y in p) / len(p), sum(x for x, _ in p) / len(p)
    vy = sum((y - mx) ** 2 for _, y in p)
    return sum((x - my) * (y - mx) for x, y in p) / vy if vy else None


def zscore(a: list, n: list, i: int, look: int = 60) -> float | None:
    w = [math.log(a[j] / n[j]) for j in range(i - look + 1, i + 1) if j >= 0 and a[j] and n[j]]
    if len(w) < look:
        return None
    mu = sum(w) / look
    sd = math.sqrt(sum((x - mu) ** 2 for x in w) / (look - 1))
    return (w[-1] - mu) / sd if sd else None


def pair_trades(days: list, a: list, n: list, entry: float = 2.0, hold: int = H) -> list:
    """Spread of an index against the Nifty, beta-hedged. z <= -entry: long the index, short beta x Nifty;
    z >= +entry: the reverse. Exit when z crosses 0 or after `hold` sessions. One trade at a time."""
    out, i = [], 252
    while i < len(days) - 1:
        z = zscore(a, n, i)
        b = beta(a, n, i)
        if z is None or b is None or abs(z) < entry:
            i += 1
            continue
        side = 1 if z < 0 else -1
        j = i + 1
        while j < min(len(days) - 1, i + hold):
            zj = zscore(a, n, j)
            if zj is not None and zj * side >= 0:
                break
            j += 1
        if not (a[j] and n[j]):
            break
        r = side * ((a[j] / a[i] - 1) - b * (n[j] / n[i] - 1)) - COST_PAIR
        out.append({"d": days[i], "exit": days[j], "side": side, "z": round(z, 2), "beta": round(b, 2), "r": round(r, 5)})
        i = j + 1
    return out


def bs(S: float, K: float, T: float, sig: float, call: bool, r: float = RF) -> float:
    if T <= 0 or sig <= 0:
        return max(0.0, (S - K) if call else (K - S))
    d1 = (math.log(S / K) + (r + sig * sig / 2) * T) / (sig * math.sqrt(T))
    d2 = d1 - sig * math.sqrt(T)
    return S * ncdf(d1) - K * math.exp(-r * T) * ncdf(d2) if call else K * math.exp(-r * T) * ncdf(-d2) - S * ncdf(-d1)


SIZE = {"capital": 500000, "max_loss": 5000, "lot": 65}   # overwritten from config/trading.json in run()
TIGHT_WING = 100         # narrow condor: wings 100 Nifty points beyond the short strikes (pre-registered, not tuned)


def condor(S: float, vix: float, T: float = H / 252, wing: float | None = None) -> dict:
    """Short 1-sigma strangle, long 2-sigma wings (or wings `wing` points out), priced off India VIX, with the skew haircut."""
    sig = vix / 100
    m = sig * math.sqrt(T)
    step = 50 if S > 5000 else 0.5                                         # Nifty strikes are 50 points apart
    k = {"sc": S * math.exp(m), "sp": S * math.exp(-m), "lc": S * math.exp(2 * m), "lp": S * math.exp(-2 * m)}
    k = {x: round(v / step) * step for x, v in k.items()}
    if wing:
        w = wing if S > 5000 else wing * S / 26000                         # synthetic prices in tests
        k["lc"], k["lp"] = k["sc"] + w, k["sp"] - w
    credit = (bs(S, k["sc"], T, sig, True) + bs(S, k["sp"], T, sig, False)
              - bs(S, k["lc"], T, sig, True) - bs(S, k["lp"], T, sig, False)) * CONDOR_HAIRCUT
    width = max(k["lc"] - k["sc"], k["sp"] - k["lp"])
    return {**k, "credit": round(credit, 1), "max_loss": round(width - credit, 1)}


def condor_pnl(c: dict, ST: float, S: float) -> float:
    pay = -(max(ST - c["sc"], 0) - max(ST - c["lc"], 0)) - (max(c["sp"] - ST, 0) - max(c["lp"] - ST, 0))
    return c["credit"] + pay - 0.0004 * S                                    # 4 legs in and out, about 0.04% of spot


def condor_trades(days: list, n: list, v: list, wing: float | None = None) -> list:
    out = []
    for i in range(0, len(days) - H, H):
        if not (v[i] and n[i] and n[i + H]):
            continue
        c = condor(n[i], v[i], wing=wing)
        if c["max_loss"] <= 0:
            continue
        p = condor_pnl(c, n[i + H], n[i])
        out.append({"d": days[i], "pnl": round(p, 1), "r": round(p / c["max_loss"], 4)})
    return out


def ideas(days: list, X: dict, reg: list, cut: str) -> list:
    N, out = X["Nifty 50"], []
    pairs = {k: pair_trades(days, X[k], N) for k in X if k not in NOT_SECTORS | {"Nifty Midcap 100", "Nifty Smallcap 100", "Nifty Next 50"}}
    pooled = sorted([(t["d"], t["r"]) for ts in pairs.values() for t in ts])
    live = []
    for k in pairs:
        z, b = zscore(X[k], N, len(days) - 1), beta(X[k], N, len(days) - 1)
        if z is not None and b is not None and abs(z) >= 2:
            live.append({"k": k, "z": round(z, 2), "beta": round(b, 2), "side": 1 if z < 0 else -1})
    out.append({"key": "pair_revert", "title": "Sector vs Nifty spread snaps back",
                "plain": "When a sector index is 2+ standard deviations cheap (or rich) against the Nifty over 60 days, "
                         "buy it and sell beta x Nifty futures (or the reverse). Exit when the gap closes or after 21 sessions.",
                "hedge": "Market-neutral: the Nifty leg cancels the market move.", "cases": pooled, "live": live,
                "sizing": "Needs two futures legs (a Nifty lot is roughly Rs 15 lakh of exposure), so it is above a "
                          "Rs 5 lakh account; paper-trade it or use the option version later."})
    bank = X.get("Nifty Bank")
    if bank:
        bf = []
        for i in range(252, len(days) - H, H):
            b = beta(bank, N, i)
            if reg[i] == "flat" and b and fwd(bank, i, H) is not None and fwd(N, i, H) is not None:
                bf.append((days[i], fwd(bank, i, H) - b * fwd(N, i, H) - COST_PAIR))
        out.append({"key": "bank_pair_flat", "title": "Long Bank Nifty, short Nifty in a slow market",
                    "plain": "In a flat market, buy Bank Nifty and sell beta x Nifty for one month (the hedged form of "
                             "'Bank Nifty is the safest index in a slow market').",
                    "hedge": "Market-neutral pair.", "cases": bf, "live": [{"k": "Nifty Bank", "beta": round(beta(bank, N, len(days) - 1) or 0, 2), "side": 1}] if reg[-1] == "flat" else [],
                    "sizing": "Two futures legs, above a Rs 5 lakh account."})
    v = X.get("India VIX")
    if v:
        ct = condor_trades(days, N, v)
        today = condor(N[-1], v[-1]) if v[-1] else None
        out.append({"key": "nifty_condor", "title": "Sell Nifty's 1-month range, wings bought (iron condor)",
                    "plain": "Each month sell the Nifty call and put one VIX standard deviation away and buy the ones two "
                             "away. Earns when the Nifty stays inside the range VIX prices; the loss is capped by the wings.",
                    "hedge": "Defined risk: the bought wings cap the loss at the strike gap minus the credit.",
                    "cases": [(t["d"], t["r"]) for t in ct], "live": [today] if today else [],
                    "pts": {"mean": round(sum(t["pnl"] for t in ct) / len(ct), 1) if ct else None,
                            "worst": min((t["pnl"] for t in ct), default=None)},
                    "sizing": "Max loss per lot = max loss points x lot size, far above the Rs 5,000 per-trade limit; "
                              "it only fits that limit as a much narrower spread.",
                    "note": "Priced with Black-Scholes off India VIX with a 15% haircut for skew and fills (no real option "
                            "history yet); per-trade figures are return on the capped loss."})
    if v:
        ct = condor_trades(days, N, v, TIGHT_WING)
        today = condor(N[-1], v[-1], wing=TIGHT_WING) if v[-1] else None
        lot, ml = SIZE["lot"], SIZE["max_loss"]
        if today:
            today["loss_rs_lot"] = round(today["max_loss"] * lot)
            today["lots"] = int(ml // today["loss_rs_lot"]) if today["loss_rs_lot"] > 0 else 0
        out.append({"key": "nifty_condor_tight", "title": "Narrow Nifty iron condor that fits the per-trade limit",
                    "plain": f"Same monthly 1-sigma short call and put, but the bought wings sit only {TIGHT_WING} points "
                             "further out, so the worst case is small enough for the per-trade limit.",
                    "hedge": "Defined risk: worst case = 100 points minus the credit, per lot.",
                    "cases": [(t["d"], t["r"]) for t in ct], "live": [today] if today else [],
                    "pts": {"mean": round(sum(t["pnl"] for t in ct) / len(ct), 1) if ct else None,
                            "worst": min((t["pnl"] for t in ct), default=None)},
                    "sizing": (f"Worst case about Rs {today['loss_rs_lot']:,} a lot ({lot} units), so {today['lots']} lot(s) "
                               f"within the Rs {ml:,} limit.") if today else "",
                    "note": f"Lot size {lot} assumed (check NSE's current Nifty lot). Same Black-Scholes pricing and 15% "
                            "haircut; narrow wings are priced least reliably this way, so treat the back-test as rough."})
    for o in out:
        o.update(test(o.pop("cases"), cut))
    return out


# ---------------------------------------------------------------- classic index timing rules (published research)
# Each rule decides at a day's close whether to hold the index for the next session (1) or sit in cash at the
# T-bill rate (0). Switching costs 0.05% (index futures or ETF). Judged against simply holding the same index:
# the monthly difference in return (clustered by month like everything else), plus Sharpe and worst fall.
SWITCH_COST = 0.0005
RULES = {
    "trend200": ("Hold only above the 200-day average (trend filter)",
                 "Faber 2007; Moskowitz, Ooi and Pedersen 2012 (time-series momentum); Livermore: trade with the trend."),
    "breakout55": ("Buy a 55-day high, sell a 20-day low (Turtle / Donchian breakout)",
                   "Donchian channels; the Turtle rules; Livermore's 'pivotal points'."),
    "month_turn": ("Hold only from the last session of the month to the 3rd of the next (turn of the month)",
                   "Lakonishok and Smidt 1988; Ariel 1987; reported for Indian indices too."),
    "rsi2_dip": ("Buy when RSI(2) is under 10 above the 200-day average, sell when it is over 70 (dip buying)",
                 "Connors and Alvarez, Short-Term Trading Strategies That Work; the 'India mean-reverts' view."),
    "fear_buy": ("Buy after India VIX jumps to its highest 10% of the past year, hold 21 sessions (buy fear)",
                 "Whaley 2000 (VIX as the fear gauge); Buffett: be greedy when others are fearful."),
}


def rsi2(c: list, i: int) -> float | None:
    if i < 3 or not all(c[i - 2:i + 1]) or not c[i - 3]:
        return None
    up = dn = 0.0
    for j in range(i - 1, i + 1):
        d = c[j] - c[j - 1]
        up, dn = up + max(d, 0), dn + max(-d, 0)
    return 100.0 if dn == 0 else 100 - 100 / (1 + up / dn)


def positions(rule: str, days: list, c: list, v: list | None) -> list:
    pos, held, until = [0] * len(days), 0, -1
    for i in range(len(days)):
        if not c[i]:
            pos[i] = held
            continue
        if rule == "trend200":
            m = sma(c, 200, i)
            held = int(m is not None and c[i] > m)
        elif rule == "breakout55":
            if i >= 55 and all(c[i - 55:i]):
                if c[i] > max(c[i - 55:i]):
                    held = 1
                elif c[i] < min(c[i - 20:i]):
                    held = 0
        elif rule == "month_turn":                   # hold into the last session's close until the 3rd session's close
            last = i + 1 < len(days) and days[i + 1][:7] != days[i][:7]
            k = 1
            while i - k >= 0 and days[i - k][:7] == days[i][:7]:
                k += 1
            held = int(last or k <= 2)
        elif rule == "rsi2_dip":
            r, m = rsi2(c, i), sma(c, 200, i)
            if held and r is not None and r > 70:
                held = 0
            elif not held and r is not None and m is not None and r < 10 and c[i] > m:
                held = 1
        elif rule == "fear_buy":
            if v and v[i] and i >= 252:
                w = sorted(x for x in v[i - 252:i] if x)
                if w and v[i] >= w[int(len(w) * 0.9)] and i > until:
                    until = i + H
            held = int(i <= until)
        pos[i] = held
    return pos


def rule_test(rule: str, days: list, c: list, v: list | None, cut: str) -> dict:
    pos = positions(rule, days, c, v)
    rs, bh, cases = [], [], {}
    for i in range(1, len(days)):
        if not (c[i] and c[i - 1]):
            continue
        r = c[i] / c[i - 1] - 1
        p = pos[i - 1]
        sr = p * r + (1 - p) * RF / 252 - (SWITCH_COST if i >= 2 and pos[i - 1] != pos[i - 2] else 0)
        rs.append((days[i], sr))
        bh.append((days[i], r))
        cases.setdefault(days[i][:7], [days[i], 0.0])[1] += sr - r
    out = test([tuple(x) for x in cases.values()], cut)

    def stats(xs):
        if len(xs) < 120:
            return None
        k = len(xs)
        eq = peak = 1.0
        dd = 0.0
        for _, x in xs:
            eq *= 1 + x
            peak = max(peak, eq)
            dd = min(dd, eq / peak - 1)
        mu = sum(x for _, x in xs) / k
        sd = math.sqrt(sum((x - mu) ** 2 for _, x in xs) / (k - 1))
        ann = eq ** (252 / k) - 1
        return {"ret": round(ann, 4), "sharpe": round((ann - RF) / (sd * math.sqrt(252)), 2) if sd else None, "maxdd": round(dd, 4)}
    for part, keep in (("is", lambda d: d < cut), ("oos", lambda d: d >= cut)):
        out[part]["strat"] = stats([x for x in rs if keep(x[0])])
        out[part]["hold"] = stats([x for x in bh if keep(x[0])])
        out[part]["in_mkt"] = round(sum(pos[i] for i, d in enumerate(days) if keep(d)) / max(1, sum(keep(d) for d in days)), 3)
    out["on_today"] = bool(pos[-1])
    return out


def safer(o: dict) -> bool:
    """Lower worst fall and at least the same Sharpe as holding, both before and after the cut."""
    try:
        return all(o[p]["strat"]["maxdd"] > o[p]["hold"]["maxdd"] and o[p]["strat"]["sharpe"] >= o[p]["hold"]["sharpe"]
                   for p in ("is", "oos"))
    except (TypeError, KeyError):
        return False


def timing_ideas(days: list, X: dict, cut: str) -> list:
    out = []
    for idx in ("Nifty 50", "Nifty Bank", "Nifty Midcap 100"):
        if idx not in X:
            continue
        for rule, (title, src) in RULES.items():
            if rule == "fear_buy" and not X.get("India VIX"):
                continue
            o = rule_test(rule, days, X[idx], X.get("India VIX"), cut)
            o.update({"key": f"{rule}:{idx}", "rule": rule, "index": idx, "title": f"{idx}: {title}", "src": src,
                      "plain": title, "h": 21, "live": [{"k": idx, "on": o["on_today"]}]})
            out.append(o)
    return out


# ---------------------------------------------------------------- the desk: tested pieces -> trade memos
# How a fund desk turns research into a trade: thesis -> evidence on unseen data -> instrument -> size from the
# risk budget (volatility, not conviction) -> stop and exit decided before entry -> hedge -> portfolio limits
# (correlated trades share one risk budget). Nothing here is new evidence; it only assembles what was tested above.
ETF = {"Nifty 50": "NIFTYBEES", "Nifty Bank": "BANKBEES", "Nifty Midcap 100": "MID150BEES", "Nifty IT": "ITBEES",
       "Nifty PSU Bank": "PSUBNKBEES"}
MAX_POSITION = 0.5        # no single trade above half the capital


def daily_vol(c: list, i: int, n: int = 63) -> float | None:
    r = [c[j] / c[j - 1] - 1 for j in range(i - n + 1, i + 1) if j > 0 and c[j] and c[j - 1]]
    if len(r) < n // 2:
        return None
    mu = sum(r) / len(r)
    return math.sqrt(sum((x - mu) ** 2 for x in r) / (len(r) - 1))


def conviction(o: dict) -> str:
    if o.get("verdict") == "HOLDS":
        return "high"
    t, a = o["oos"].get("t") or 0, o["is"].get("raw_mean")
    return "medium" if t >= 1.5 and (a or 0) > 0 else "low"


def memo_long(idx: str, c: list, i: int, vix: float | None, hold: int, o: dict, why: str, exit_rule: str) -> dict:
    sd = daily_vol(c, i) or 0.01
    stop_pct = sd * math.sqrt(hold)                       # one ordinary holding-period move
    px = c[i]
    notional = min(SIZE["max_loss"] / stop_pct, SIZE["capital"] * MAX_POSITION)
    risk = notional * stop_pct
    sig = (vix or sd * math.sqrt(252) * 100) / 100
    put_k = round(px * (1 - stop_pct) / 50) * 50 if px > 5000 else px * (1 - stop_pct)
    put = bs(px, put_k, hold / 252, sig, False) / px if px > 0 else None
    return {"k": o["key"], "idx": idx, "etf": ETF.get(idx), "title": o.get("title"), "why": why, "src": o.get("src"),
            "conv": conviction(o), "verdict": o.get("verdict"), "safer": o.get("safer"),
            "ev": {x: o["oos"].get(x) for x in ("raw_mean", "hit", "months", "t", "n")},
            "px": round(px, 2), "stop": round(px * (1 - stop_pct), 2), "stop_pct": round(stop_pct, 4),
            "notional": round(notional, -2), "risk_rs": round(risk), "hold": hold, "exit": exit_rule,
            "hedge": {"put_strike": put_k, "cost_pct": round(put, 4) if put else None,
                      "text": f"Optional: buy the {put_k:.0f} {idx} put for about {put * 100:.1f}% of the position; "
                              "it replaces the stop on a gap down." if put else None}}


def desk(days: list, X: dict, reg: list, bl: list, idl: list, tim: list, vix: dict | None) -> dict:
    i = len(days) - 1
    v = (vix or {}).get("vix")
    cand = []
    for o in tim:                                          # timing rules in the market today, with positive unseen evidence
        if o.get("on_today") and ((o["oos"].get("raw_mean") or 0) > 0 or o.get("safer")):
            hold = H if o["rule"] in ("trend200", "breakout55", "fear_buy") else 5
            ex = {"trend200": "Sell when the index closes below its 200-day average, or at the stop.",
                  "breakout55": "Sell on a close below the 20-day low, or at the stop.",
                  "month_turn": "Sell at the close of the 3rd session of the month.",
                  "rsi2_dip": "Sell when RSI(2) closes above 70, or at the stop.",
                  "fear_buy": "Sell 21 sessions after the VIX spike, or at the stop."}[o["rule"]]
            cand.append(memo_long(o["index"], X[o["index"]], i, v, hold, o, o["plain"], ex))
    for b in bl:                                           # market-type beliefs that apply today
        if b["key"] in ("bank_flat",) and reg[i] == "flat" and (b["oos"].get("raw_mean") or 0) > 0:
            cand.append(memo_long("Nifty Bank", X["Nifty Bank"], i, v, H, b, b["plain"], "Sell after one month, or at the stop."))
    rank = {"high": 0, "medium": 1, "low": 2}
    cand.sort(key=lambda m: (rank[m["conv"]], -(m["ev"].get("t") or 0)))
    picks, used = [], set()
    for m in cand:                                         # one trade per index; correlated index longs share the budget
        if m["idx"] in used:
            continue
        used.add(m["idx"])
        picks.append(m)
        if len(picks) == 3:
            break
    longs = [m for m in picks if m["conv"] != "low"]
    if len(longs) > 1:                                      # Nifty, Bank Nifty and Midcap move together (corr ~0.85)
        for m in longs:
            m["notional"], m["risk_rs"] = round(m["notional"] / len(longs), -2), round(m["risk_rs"] / len(longs))
            m["note"] = f"Size cut to 1/{len(longs)}: these indices move together, so they share one risk budget."
    heat = sum(m["risk_rs"] for m in longs)
    trade = [m for m in picks if m["conv"] in ("high", "medium")]
    stance = ("TRADE: " + ", ".join(m["etf"] or m["idx"] for m in trade)) if trade else "NO TRADE TODAY"
    why = ("Only ideas with positive results on data they were never fitted on are traded; size comes from the "
           f"Rs {SIZE['max_loss']:,} per-trade loss limit and the index's own volatility.") if trade else \
          ("Nothing that is in play today has enough unseen evidence. " + ("The watch list below is what the desk "
           "would trade if its evidence firms up. " if picks else "No tested rule is signalling today. ") +
           "Sitting out is a position.")
    fails = [b["title"] for b in bl if b.get("verdict") == "FAILS"][:3]
    nxt = []                                               # what would make the desk act, in plain numbers
    vv = X.get("India VIX")
    if vv and vv[-1] and len(vv) > 252:
        w = sorted(x for x in vv[-253:-1] if x)
        thr = w[int(len(w) * 0.9)] if w else None
        if thr and vv[-1] < thr:
            nxt.append(f"India VIX above {thr:.1f} (now {vv[-1]:.1f}): the buy-the-fear rule switches on, watch list only.")
    n = X["Nifty 50"]
    if reg[i] != "flat" and i > 63 and n[i - 63]:
        lo, hi = n[i - 63] * (1 - FLAT_BAND), n[i - 63] * (1 + FLAT_BAND)
        nxt.append(f"Nifty back between {lo:,.0f} and {hi:,.0f} (now {n[i]:,.0f}): a flat market, where the Bank Nifty "
                   "views apply.")
    label = REGIME_TEXT.get(reg[i], "this").lower()
    headline = (f"Trade: {', '.join(m['etf'] or m['idx'] for m in trade)}, sized for a Rs {SIZE['max_loss']:,} worst case."
                if trade else f"Do nothing today: no tested edge in a {label}.")
    return {"stance": stance, "headline": headline, "next": nxt, "why": why, "memos": picks, "heat_rs": heat, "limit_rs": SIZE["max_loss"],
            "capital": SIZE["capital"], "avoid": fails,
            "process": ["Thesis from published research or a market belief", "Tested on data it was never fitted on",
                        "Size from the loss limit and volatility, not from conviction", "Stop and exit fixed before entry",
                        "Optional put hedge for gaps", "Correlated trades share one risk budget"]}


def paper_log(log: dict, days: list, N: list, v: list | None) -> dict:
    """Forward (paper) record of the condor ideas from the day this went live: one open trade per idea, entered at
    the evening close, settled 21 sessions later on the Nifty close. Nothing here is fitted; it only accumulates."""
    log = log or {"since": days[-1], "trades": []}
    idx = {d: i for i, d in enumerate(days)}
    for t in log["trades"]:
        if t.get("exit") is None and t["d"] in idx and idx[t["d"]] + H < len(days):
            j = idx[t["d"]] + H
            t["exit"], t["exit_px"] = days[j], N[j]
            t["pnl"] = round(condor_pnl(t["legs"], N[j], t["px"]), 1)
    if v and v[-1]:
        for key, wing in (("nifty_condor", None), ("nifty_condor_tight", TIGHT_WING)):
            if not any(t["k"] == key and t.get("exit") is None for t in log["trades"]):
                c = condor(N[-1], v[-1], wing=wing)
                log["trades"].append({"k": key, "d": days[-1], "px": N[-1], "legs": c, "exit": None})
    done = [t for t in log["trades"] if t.get("exit")]
    log["summary"] = {k: {"closed": len(xs), "won": sum(t["pnl"] > 0 for t in xs), "pts": round(sum(t["pnl"] for t in xs), 1),
                          "open": next(({"d": t["d"], "legs": t["legs"]} for t in log["trades"] if t["k"] == k and not t.get("exit")), None)}
                      for k in ("nifty_condor", "nifty_condor_tight")
                      for xs in [[t for t in done if t["k"] == k]]}
    return log

def build(series: dict, cap: dict, factors: dict | None = None, stocks: dict | None = None) -> dict:
    days, X = align(series)
    N = X["Nifty 50"]
    reg = regimes(N)
    cut = split_date(days)
    cap_cols = [align({"Nifty 50": series["Nifty 50"], k: s})[1][k] for k, s in cap.items()]
    bl = beliefs(days, X, reg, cap_cols)
    F = {k: align({"Nifty 50": series["Nifty 50"], k: v})[1][k] for k, v in (factors or {}).items()}
    for k, c in F.items():
        bl.append({"key": "factor:" + k, "title": f"{k} index beats the Nifty", "sign": 1, "h": H,
                   "plain": f"Holding the NSE {k} index beats the Nifty 50 over the next month (any market).",
                   "cases": [(days[i], a - b) for i in range(len(days)) if reg[i] and (a := fwd(c, i, H)) is not None
                             and (b := fwd(N, i, H)) is not None], "note": "Smart-beta index; NSE back-calculated its early history."})
    S = {k: align({"Nifty 50": series["Nifty 50"], k: v})[1][k] for k, v in (stocks or {}).items()}
    screen = []
    if S:
        cs, lv = screen_test(days, N, S)
        bl.append({"key": "calm_strong", "title": "Low risk, high return screen (calm half, best trailing Sharpe)", "sign": 1, "h": H,
                   "plain": "Each month buy the 20 Nifty 500 stocks with the best 12-month return per unit of risk among the "
                            "calmer half; they beat the Nifty over the next month after 0.25% charges.", "cases": cs,
                   "note": "Today's Nifty 500 members (survivorship bias flatters this)."})
        bl.append({"key": "low_vol", "title": "The calmest stocks beat the Nifty (low-volatility effect)", "sign": 1, "h": H,
                   "plain": "Each month buy the calmest 20% of Nifty 500 stocks; they beat the Nifty over the next month "
                            "after charges.", "cases": lv, "note": "Today's Nifty 500 members (survivorship bias)."})
        screen = screen_today(days, N, S)
    for b in bl:
        b.update(test(b.pop("cases"), cut, b["sign"]))
    idl = ideas(days, X, reg, cut)
    tim = timing_ideas(days, X, cut)
    holm(bl + idl + tim)
    for o in idl + tim:
        o["verdict"] = verdict(o)
    for o in tim:
        o["safer"] = safer(o)
    for b in bl:
        b["verdict"] = verdict(b)
    today_reg = reg[-1]
    tab = sector_table(days, X, reg, cut)
    favour = sorted(((k, v[today_reg]) for k, v in tab.items() if today_reg and v[today_reg]["is"] is not None),
                    key=lambda kv: -(kv[1]["is"] or 0))
    rot = walk_rotation(days, X, reg)
    rot["record"] = rot["record"][-36:]
    nd = next_day(days, N, reg)
    dr = lambda c: [None if i == 0 or not c[i] or not c[i - 1] else c[i] / c[i - 1] - 1 for i in range(len(c))]
    bank = X.get("Nifty Bank")
    k0 = next(i for i, d in enumerate(days) if d >= cut)
    rel = {}
    for k in [k for k in X if k not in NOT_SECTORS]:
        a, b = fwd(X[k], len(days) - 253, 252), fwd(N, len(days) - 253, 252)
        if a is not None and b is not None:
            rel[k] = round(a - b, 4)
    regime_hist = {r: round(sum(x == r for x in reg[-756:]) / 756, 3) for r in REGIMES}
    active = {"flat": ["bank_flat", "capmkt_flat"]}.get(today_reg, [])
    return {
        "asof": days[-1], "from": days[0], "oos_from": cut, "regime": today_reg,
        "regime_text": REGIME_TEXT.get(today_reg, "Not enough history"),
        "nifty_r63": round(N[-1] / N[-64] - 1, 4), "nifty_vs200": round(N[-1] / sma(N, 200, len(N) - 1) - 1, 4),
        "regime_share_3y": regime_hist,
        "beliefs": bl, "active_today": active,
        "sectors_today": [{"k": k, **v} for k, v in favour],
        "sector_table": tab,
        "rotation": rot, "next_day": nd,
        "bank_downside_flat": downside(days, X, reg, "Nifty Bank", "Nifty 50", "flat", cut) if bank else None,
        "bank_corr": {"is": corr(dr(bank)[:k0], dr(N)[:k0]), "oos": corr(dr(bank)[k0:], dr(N)[k0:])} if bank else None,
        "rel_12m": dict(sorted(rel.items(), key=lambda kv: kv[1])),
        "cap_names": list(cap),
        "desk": desk(days, X, reg, bl, idl, tim, vix_range(days, X)),
        "ideas": idl, "timing": tim, "risk": risk_table(days, X | F, cut), "vix": vix_range(days, X), "screen": screen,
        "factors": list(F),
        "untested": ["FII / DII flows: only a few days are stored (docs/nse-feeds.json), so flow-driven views cannot "
                     "be back-tested yet.",
                     "Valuation (P/E) of sector indices: no history in the data, so 'cheap' is tested with a price proxy."],
        "note": "Research software, not advice. Index history from Dhan; today's index members and listed stocks "
                "(survivorship bias). Holm's many-ideas correction across every belief on this page.",
    }


# ---------------------------------------------------------------- report
def pct(x, d=1):
    return "n/a" if x is None else f"{x * 100:+.{d}f}%"


def share(x):
    return "n/a" if x is None else f"{x * 100:.0f}%"


def markdown(v: dict) -> str:
    L = [f"# Market view, {v['asof']}", "",
         f"Research software, not advice. Dhan daily history {v['from']} to {v['asof']}; out of sample from {v['oos_from']}.", "",
         f"**Market type today: {v['regime_text']}** (Nifty {pct(v['nifty_r63'])} over 63 sessions, "
         f"{pct(v['nifty_vs200'])} vs its 200-day average).", "",
         "## Popular beliefs, tested", "",
         "| Belief | Verdict | In-sample (avg, t) | Out of sample (avg, t, worked) | Months OOS |", "|---|---|---|---|---|"]
    for b in v["beliefs"]:
        a, o = b["is"], b["oos"]
        L.append(f"| {b['title']} | **{b['verdict']}** | {pct(a.get('raw_mean'), 2)}, t {a['t']} | "
                 f"{pct(o.get('raw_mean'), 2)}, t {o['t']}, {share(o['hit'])} | {o['months']} |")
    L += ["", "Worked = share of cases where the belief was right. Averages are per case, over the belief's horizon "
          "(1 month, 5 sessions for the lead and bounce beliefs, 6 months for the laggard belief).", ""]
    nd, rot = v["next_day"], v["rotation"]
    L += ["## Forecast track record (walk-forward, no look-ahead)", "",
          f"- Next-session Nifty direction from market type + today's move: right {share(nd['accuracy'])} of "
          f"{nd['days']} days, vs {share(nd['always_up'])} for simply saying 'up' every day.",
          f"- Monthly sector rotation (hold the sector that did best in this market type before): average "
          f"{pct(rot['stats']['mean'], 2)} a month vs the Nifty, beat it in {share(rot['stats']['hit'])} of "
          f"{rot['stats']['n']} months, t {rot['stats']['t']}.", ""]
    if nd.get("today"):
        L.append(f"Tomorrow: in this setup ({' / '.join(nd['today']['bucket'])}) the Nifty rose the next session "
                 f"{nd['today']['p_up'] * 100:.0f}% of {nd['today']['n']} times.")
    L += ["", "## Sectors in this market type (1-month excess vs Nifty)", "", "| Sector | In-sample | Out of sample | OOS worked |", "|---|---|---|---|"]
    for s in v["sectors_today"]:
        L.append(f"| {s['k']} | {pct(s['is'], 2)} | {pct(s['oos'], 2)} | {share(s['oos_hit'])} |")
    vx = v.get("vix")
    if vx:
        L += ["", "## Tomorrow's range from India VIX (Black-Scholes)", "",
              f"VIX {vx['vix']}: the options market prices a 1-day move of about {vx['day_pts']} Nifty points (1 sigma) and "
              f"{vx['month_pts']} points over a month. Chance of a 1.5%+ move tomorrow: {share(vx['p_move15'])}.",
              f"Check on {vx['days']} days: the Nifty stayed inside the 1-sigma range {share(vx['hit1'])} of days "
              f"(68% if calibrated) and inside 2 sigma {share(vx['hit2'])} (95%). 1.5%+ moves happened "
              f"{share(vx['big_actual'])} of days vs {share(vx['big_implied'])} implied."]
    if v.get("risk"):
        L += ["", "## Risk and return, last 3 years (best Sharpe first)", "",
              "| Index | Return a year | Volatility | Sharpe | Max drawdown | Beta | Corr to Nifty |", "|---|---|---|---|---|---|---|"]
        for r in v["risk"]:
            o = r["oos"]
            L.append(f"| {r['k']} | {pct(o['ret'])} | {share(o['vol'])} | {o['sharpe']} | {pct(o['maxdd'])} | {o['beta']} | {o['corr']} |")
    if v.get("screen"):
        L += ["", "## Low risk, high return: today's screen", "",
              "| Stock | Return/risk | Volatility | 12-1m return | Max drawdown 1y | Beta |", "|---|---|---|---|---|---|"]
        for r in v["screen"]:
            L.append(f"| {r['s']} | {r['score']} | {share(r['vol'])} | {pct(r['mom'])} | {pct(r['maxdd'])} | {r['beta']} |")
    L += ["", "## Not testable yet", ""] + [f"- {u}" for u in v["untested"]]
    return "\n".join(L) + "\n"


# ---------------------------------------------------------------- run (needs Dhan secrets)
def fetch(dhan, scrip: str, start: dt.date, end: dt.date) -> tuple[dict, dict]:
    import refresh as R
    import terminal_bt as TB
    _, ix = R.build_maps(scrip, [], EXTRA_IDX)
    ids = dict(IDX_IDS) | ix
    series, cap = {}, {}
    for name, sid in ids.items():
        try:
            s = TB.series(dhan.daily(sid, "IDX_I", "INDEX", start, end), R.IST)
            if len(s["c"]) > 300:
                series[name] = s
        except Exception as e:
            print(f"  skip {name}: {str(e)[:80]}")
    eq, _ = R.build_maps(scrip, CAPMKT, [])
    for sym, sid in eq.items():
        try:
            s = TB.series(dhan.daily(sid, "NSE_EQ", "EQUITY", start, end), R.IST)
            if len(s["c"]) > 150:
                cap[sym] = s
        except Exception as e:
            print(f"  skip {sym}: {str(e)[:80]}")
    fac = {}
    for name, sid in factor_ids(scrip).items():
        try:
            f = TB.series(dhan.daily(sid, "IDX_I", "INDEX", start, end), R.IST)
            if len(f["c"]) > 300:
                fac[name] = f
        except Exception as e:
            print(f"  skip {name}: {str(e)[:80]}")
    print(f"  factor indices: {list(fac)}", flush=True)
    return series, cap, fac


def fetch_stocks(dhan, root: Path, start: dt.date, end: dt.date) -> dict:
    import refresh as R
    import terminal_bt as TB
    try:
        import tech_model
        if tech_model.LAST:
            return {k: v for k, v in tech_model.LAST[0].items()}
    except Exception:
        pass
    out = {}
    rows = [r for r in json.loads((root / "docs/n500.json").read_text(encoding="utf-8"))["rows"] if r.get("sid")]
    for r in rows:
        try:
            out[r["s"]] = TB.series(dhan.daily(r["sid"], "NSE_EQ", "EQUITY", start, end), R.IST)
        except Exception as e:
            print(f"  skip {r['s']}: {str(e)[:60]}")
    return out


def run(dhan, root: Path) -> str:
    import requests
    import refresh as R
    now = dt.datetime.now(R.IST)
    scrip = requests.get(R.SCRIP_MASTER, timeout=60).text
    try:
        cfg = json.loads((root / "config/trading.json").read_text(encoding="utf-8"))
        SIZE.update({"capital": int(cfg.get("capital", SIZE["capital"])), "max_loss": int(cfg.get("max_loss_per_trade", SIZE["max_loss"])),
                     "lot": int(cfg.get("nifty_lot", SIZE["lot"]))})
    except Exception as e:
        print(f"  sizing from config failed, using {SIZE}: {e}")
    series, cap, fac = fetch(dhan, scrip, dt.date(2010, 1, 1), now.date())
    stocks = fetch_stocks(dhan, root, dt.date(2013, 1, 1), now.date())
    v = build(series, cap, fac, stocks)
    lp = root / "docs/ideas-log.json"
    try:
        old = json.loads(lp.read_text(encoding="utf-8"))
    except Exception:
        old = None
    days, X = align(series)
    log = paper_log(old, days, X["Nifty 50"], X.get("India VIX"))
    lp.write_text(json.dumps(log, indent=1), encoding="utf-8")
    v["paper"] = log["summary"] | {"since": log["since"]}
    try:                                              # weekly-candle re-test of the same ideas, last 11 years
        import weekly_view as WV
        w = WV.build(series, cap)
        w["compare"] = WV.compare(w, v)
        (root / "docs/weekly-view.json").write_text(json.dumps(w, separators=(",", ":")), encoding="utf-8")
        (root / "docs/weekly-view.md").write_text(WV.markdown(w), encoding="utf-8")
        v["weekly"] = {"from": w["from"], "asof": w["asof"], "weeks": w["weeks"], "regime": w["regime"], "held": w["held"],
                       "rows": [{"k": o["key"], "t": o["title"], "g": o["group"], "v": o["verdict"], "live": bool(o["live"]),
                                 "is": o["is"].get("raw_mean"), "oos": o["oos"].get("raw_mean"), "hit": o["oos"]["hit"],
                                 "m": o["oos"]["months"]} for o in w["results"]]}
    except Exception as e:
        print(f"  weekly view failed: {e}", flush=True)
    (root / "docs/market-view.json").write_text(json.dumps(v, separators=(",", ":")), encoding="utf-8")
    (root / "docs/market-view.md").write_text(markdown(v), encoding="utf-8")
    held = [b["key"] for b in v["beliefs"] if b["verdict"] == "HOLDS"]
    return f"market view {v['asof']}: {v['regime']}; {len(held)} of {len(v['beliefs'])} beliefs hold {held}"


def main() -> int:
    import refresh as R
    root = Path(__file__).resolve().parents[2]
    cid, pin, sec = R.clean_secrets(*(os.environ[k] for k in ("DHAN_CLIENT_ID", "DHAN_PIN", "DHAN_TOTP_SECRET")))
    dhan = R.Dhan(cid, R.login(cid, pin, sec))
    print(run(dhan, root), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
