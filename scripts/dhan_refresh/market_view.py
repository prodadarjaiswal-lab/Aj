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


def build(series: dict, cap: dict) -> dict:
    days, X = align(series)
    N = X["Nifty 50"]
    reg = regimes(N)
    cut = split_date(days)
    cap_cols = [align({"Nifty 50": series["Nifty 50"], k: s})[1][k] for k, s in cap.items()]
    bl = beliefs(days, X, reg, cap_cols)
    for b in bl:
        b.update(test(b.pop("cases"), cut, b["sign"]))
    holm(bl)
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
        "untested": ["FII / DII flows: only a few days are stored (docs/nse-feeds.json), so flow-driven views cannot "
                     "be back-tested yet; each day's figures are now kept so they can be later.",
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
    return series, cap


def run(dhan, root: Path) -> str:
    import requests
    import refresh as R
    now = dt.datetime.now(R.IST)
    scrip = requests.get(R.SCRIP_MASTER, timeout=60).text
    series, cap = fetch(dhan, scrip, dt.date(2010, 1, 1), now.date())
    v = build(series, cap)
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
