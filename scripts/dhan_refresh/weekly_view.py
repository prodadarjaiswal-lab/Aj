"""Weekly-candle re-test of every idea on the Market view (ADARSH, 27 Nov 2026: "use the weekly candles and run
all the ideas on the last 10 to 11 years").

Same daily index history as market_view.py (Dhan, from 2010), turned into weekly candles (the close of each
week's last session). Every belief, hedged idea and timing rule is re-run on those weekly bars with weekly
settings (one month = 4 weeks, 200 days = 40 weeks, 63 sessions = 13 weeks). Results count only weeks from the
last 11 years; the year before that is warm-up for the averages. Same out-of-sample split (last 3 years), same
month-clustered statistics and the same Holm many-ideas correction, run across the weekly tests together.

Writes docs/weekly-view.json and docs/weekly-view.md. Research software, not advice.
"""
from __future__ import annotations

import datetime as dt
import math

import market_view as M

YEARS = 11
H = 4                    # one month in weeks
PPY = 52                 # weeks a year
SMA_W, CHG_W = 40, 13    # 200 sessions ~ 40 weeks, 63 sessions ~ 13 weeks


def weekly(days: list, X: dict) -> tuple[list, dict]:
    """Daily (days, name -> closes) -> weekly bars dated on each ISO week's last session (last known close)."""
    wk = [dt.date.fromisoformat(d).isocalendar()[:2] for d in days]
    ends = [i for i in range(len(days)) if i == len(days) - 1 or wk[i + 1] != wk[i]]
    out, start = {k: [] for k in X}, 0
    for e in ends:
        for k, c in X.items():
            out[k].append(next((c[j] for j in range(e, start - 1, -1) if c[j]), None))
        start = e + 1
    return [days[i] for i in ends], out


def wregimes(n: list) -> list:
    out = []
    for i in range(len(n)):
        s = M.sma(n, SMA_W, i)
        if s is None or i < CHG_W or not n[i - CHG_W] or not n[i]:
            out.append(None)
            continue
        r = n[i] / n[i - CHG_W] - 1
        out.append("flat" if abs(r) <= M.FLAT_BAND else "rising" if n[i] > s and r > 0
                   else "falling" if n[i] < s and r < 0 else "turning")
    return out


def wbeta(a: list, n: list, i: int, look: int = 52) -> float | None:
    p = [(a[j] / a[j - 1] - 1, n[j] / n[j - 1] - 1) for j in range(max(1, i - look + 1), i + 1)
         if a[j] and a[j - 1] and n[j] and n[j - 1]]
    if len(p) < 26:
        return None
    ma, mn = sum(x for x, _ in p) / len(p), sum(y for _, y in p) / len(p)
    vn = sum((y - mn) ** 2 for _, y in p)
    return sum((x - ma) * (y - mn) for x, y in p) / vn if vn else None


def pair_trades(days, a, n, start, entry=2.0, hold=8, look=26) -> list:
    out, i = [], max(start, 52)
    while i < len(days) - 1:
        z, b = M.zscore(a, n, i, look), wbeta(a, n, i)
        if z is None or b is None or abs(z) < entry:
            i += 1
            continue
        side, j = (1 if z < 0 else -1), i + 1
        while j < min(len(days) - 1, i + hold):
            zj = M.zscore(a, n, j, look)
            if zj is not None and zj * side >= 0:
                break
            j += 1
        if not (a[j] and n[j] and a[i] and n[i]):
            break
        out.append((days[i], side * ((a[j] / a[i] - 1) - b * (n[j] / n[i] - 1)) - M.COST_PAIR))
        i = j + 1
    return out


def rsi2(c, i):
    return M.rsi2(c, i)


def positions(rule: str, c: list, v: list | None) -> list:
    pos, held, until = [0] * len(c), 0, -1
    for i in range(len(c)):
        if not c[i]:
            pos[i] = held
            continue
        if rule == "trend40":
            m = M.sma(c, SMA_W, i)
            held = int(m is not None and c[i] > m)
        elif rule == "breakout26":
            if i >= 26 and all(c[i - 26:i]):
                if c[i] > max(c[i - 26:i]):
                    held = 1
                elif c[i] < min(c[i - 13:i]):
                    held = 0
        elif rule == "rsi2_dip":
            r, m = rsi2(c, i), M.sma(c, SMA_W, i)
            if held and r is not None and r > 70:
                held = 0
            elif not held and r is not None and m is not None and r < 10 and c[i] > m:
                held = 1
        elif rule == "fear_buy":
            if v and v[i] and i >= 52:
                w = sorted(x for x in v[i - 52:i] if x)
                if w and v[i] >= w[int(len(w) * 0.9)] and i > until:
                    until = i + H
            held = int(i <= until)
        pos[i] = held
    return pos


RULES = {
    "trend40": ("Hold only above the 40-week average (Faber's 10-month rule)", "Faber 2007; Livermore: trade with the trend."),
    "breakout26": ("Buy a 26-week high, sell a 13-week low (weekly breakout)", "Donchian / Turtle rules on weekly bars."),
    "rsi2_dip": ("Buy when weekly RSI(2) is under 10 above the 40-week average, sell over 70", "Connors and Alvarez, on weekly bars."),
    "fear_buy": ("Buy the week India VIX reaches its top 10% of the past year, hold 4 weeks", "Whaley 2000; Buffett."),
}


def rule_test(rule, days, c, v, cut, start) -> dict:
    pos = positions(rule, c, v)
    rs, bh, cases = [], [], {}
    for i in range(max(1, start), len(days)):
        if not (c[i] and c[i - 1]):
            continue
        r = c[i] / c[i - 1] - 1
        p = pos[i - 1]
        sr = p * r + (1 - p) * M.RF / PPY - (M.SWITCH_COST if i >= 2 and pos[i - 1] != pos[i - 2] else 0)
        rs.append((days[i], sr))
        bh.append((days[i], r))
        cases.setdefault(days[i][:7], [days[i], 0.0])[1] += sr - r
    out = M.test([tuple(x) for x in cases.values()], cut)

    def stats(xs):
        if len(xs) < 26:
            return None
        eq = peak = 1.0
        dd = 0.0
        for _, x in xs:
            eq *= 1 + x
            peak = max(peak, eq)
            dd = min(dd, eq / peak - 1)
        mu = sum(x for _, x in xs) / len(xs)
        sd = math.sqrt(sum((x - mu) ** 2 for _, x in xs) / (len(xs) - 1))
        ann = eq ** (PPY / len(xs)) - 1
        return {"ret": round(ann, 4), "sharpe": round((ann - M.RF) / (sd * math.sqrt(PPY)), 2) if sd else None,
                "maxdd": round(dd, 4)}
    for part, keep in (("is", lambda d: d < cut), ("oos", lambda d: d >= cut)):
        out[part]["strat"] = stats([x for x in rs if keep(x[0])])
        out[part]["hold"] = stats([x for x in bh if keep(x[0])])
    out["on_today"] = bool(pos[-1])
    return out


def build(series: dict, cap: dict | None = None, years: int = YEARS) -> dict:
    ddays, DX = M.align(series)
    days, X = weekly(ddays, DX)
    first = (dt.date.fromisoformat(days[-1]) - dt.timedelta(days=int(365.25 * years))).isoformat()
    s0 = next(i for i, d in enumerate(days) if d >= first)
    cut = M.split_date(days)
    N = X["Nifty 50"]
    reg = wregimes(N)
    rng = range(s0, len(days))
    sectors = [k for k in X if k not in M.NOT_SECTORS]
    out = []

    def add(key, group, title, plain, cases, sign=1, live=None, extra=None):
        out.append({"key": key, "group": group, "title": title, "plain": plain, "sign": sign,
                    "live": bool(live), **(extra or {}), **M.test(cases, cut, sign)})

    def ex(col, i, h=H):
        a, b = M.fwd(col, i, h), M.fwd(N, i, h)
        return None if a is None or b is None else a - b

    bank = X.get("Nifty Bank")
    if bank:
        add("bank_flat", "belief", "Bank Nifty is the index to buy in a flat market",
            "In a flat week (Nifty within 3% of 13 weeks ago), Bank Nifty beats the Nifty over the next 4 weeks.",
            [(days[i], v) for i in rng if reg[i] == "flat" and (v := ex(bank, i)) is not None], live=reg[-1] == "flat")
        add("bank_always", "belief", "Bank Nifty beats the Nifty in any market",
            "Any week, Bank Nifty beats the Nifty over the next 4 weeks.",
            [(days[i], v) for i in rng if reg[i] and (v := ex(bank, i)) is not None], live=True)
        lead = []
        for i in rng:
            b1, n1, nf = M.fwd(bank, i - 1, 1), M.fwd(N, i - 1, 1), M.fwd(N, i, 1)
            if None not in (b1, n1, nf) and abs(b1 - n1) >= 0.01:
                lead.append((days[i], nf if b1 > n1 else -nf))
        add("bank_leads", "belief", "Bank Nifty leads the Nifty",
            "After a week where Bank Nifty beat (lagged) the Nifty by 1%+, the Nifty rises (falls) the next week.", lead)
    capc = [M.align({"Nifty 50": series["Nifty 50"], k: s})[1][k] for k, s in (cap or {}).items()]
    if capc:
        capw = [weekly(ddays, {"x": c})[1]["x"] for c in capc]
        add("capmkt_flat", "belief", "Exchange, broker and AMC stocks win in a slow market",
            "In a flat week, an equal basket of BSE, MCX, CDSL, Angel One, CAMS and peers beats the Nifty over the next "
            "4 weeks after 0.25% charges.",
            [(days[i], b - n - M.COST_STOCK) for i in rng if reg[i] == "flat"
             and (b := M.basket_fwd(capw, i, H)) is not None and (n := M.fwd(N, i, H)) is not None], live=reg[-1] == "flat")

    def nx(i):
        f = M.fwd(N, i, H)
        if f is None or i < 54:
            return None
        past = [r for j in range(i - 54, i - H) if (r := M.fwd(N, j, H)) is not None]
        return f - sum(past) / len(past) if past else None
    w1 = lambda i: M.fwd(N, i - 1, 1) if i >= 1 else None
    add("nifty_bounce", "belief", "After a sharp weekly fall the Nifty bounces",
        "After a week the Nifty falls 3%+, its next 4 weeks are better than usual.",
        [(days[i], v) for i in rng if (p := w1(i)) is not None and p <= -0.03 and (v := nx(i)) is not None],
        live=(w1(len(days) - 1) or 0) <= -0.03)
    add("nifty_fade", "belief", "After a sharp weekly rise the Nifty gives some back",
        "After a week the Nifty rises 3%+, its next 4 weeks are worse than usual.",
        [(days[i], v) for i in rng if (p := w1(i)) is not None and p >= 0.03 and (v := nx(i)) is not None], sign=-1,
        live=(w1(len(days) - 1) or 0) >= 0.03)
    rev, mom, lag = [], [], []
    for i in range(max(s0, 52), len(days), H):
        r1 = {k: (M.fwd(X[k], i - H, H), ex(X[k], i)) for k in sectors}
        r6 = {k: (M.fwd(X[k], i - 26, 26), ex(X[k], i)) for k in sectors}
        ok1 = {k: v for k, v in r1.items() if None not in v}
        ok6 = {k: v for k, v in r6.items() if None not in v}
        if len(ok1) >= 5:
            rev.append((days[i], min(ok1.items(), key=lambda kv: kv[1][0])[1][1]))
        if len(ok6) >= 5:
            mom.append((days[i], max(ok6.items(), key=lambda kv: kv[1][0])[1][1]))
        for k in sectors:
            a, b = M.fwd(X[k], i - 52, 52), M.fwd(N, i - 52, 52)
            if a is not None and b is not None and a - b <= -0.15 and (v := ex(X[k], i, 26)) is not None:
                lag.append((days[i], v))
    add("sector_reversal", "belief", "Last month's worst sector bounces",
        "Every 4 weeks buy the sector index that did worst over the last 4 weeks; it beats the Nifty over the next 4.", rev)
    add("sector_momentum", "belief", "The strongest sector keeps winning",
        "Every 4 weeks buy the sector that did best over the last 26 weeks; it beats the Nifty over the next 4.", mom)
    add("laggard_catchup", "belief", "A sector that lagged for a year catches up ('IT is cheap')",
        "A sector that trailed the Nifty by 15%+ over 52 weeks beats it over the next 26 weeks.", lag)

    # hedged ideas
    skip = M.NOT_SECTORS | {"Nifty Midcap 100", "Nifty Smallcap 100", "Nifty Next 50"}
    pooled, fired = [], []
    for k in X:
        if k in skip:
            continue
        pooled += pair_trades(days, X[k], N, s0)
        z = M.zscore(X[k], N, len(days) - 1, 26)
        if z is not None and abs(z) >= 2:
            fired.append(k)
    add("pair_revert", "idea", "Sector vs Nifty spread snaps back (weekly)",
        "When a sector is 2+ standard deviations cheap (rich) against the Nifty over 26 weeks, buy (sell) it and sell "
        "(buy) beta x Nifty; exit when the gap closes or after 8 weeks.", sorted(pooled), live=fired,
        extra={"fired": fired})
    if bank:
        bf = [(days[i], M.fwd(bank, i, H) - b * M.fwd(N, i, H) - M.COST_PAIR) for i in range(max(s0, 52), len(days) - H, H)
              if reg[i] == "flat" and (b := wbeta(bank, N, i)) and M.fwd(bank, i, H) is not None and M.fwd(N, i, H) is not None]
        add("bank_pair_flat", "idea", "Long Bank Nifty, short Nifty in a slow market (weekly)",
            "In a flat week, buy Bank Nifty and sell beta x Nifty for 4 weeks.", bf, live=reg[-1] == "flat")
    v = X.get("India VIX")
    if v:
        for key, wing, title in (("nifty_condor", None, "Monthly Nifty iron condor, 2-sigma wings"),
                                 ("nifty_condor_tight", M.TIGHT_WING, f"Narrow Nifty iron condor, wings {M.TIGHT_WING} points")):
            ct = []
            for i in range(s0, len(days) - H, H):
                if v[i] and N[i] and N[i + H]:
                    c = M.condor(N[i], v[i], T=H / PPY, wing=wing)
                    if c["max_loss"] > 0:
                        ct.append((days[i], M.condor_pnl(c, N[i + H], N[i]) / c["max_loss"]))
            add(key, "idea", title, "Sold every 4 weeks at the weekly close, priced off India VIX (Black-Scholes, "
                "15% haircut), settled 4 weeks later.", ct, live=True)
        # timing rules
    for idx in ("Nifty 50", "Nifty Bank", "Nifty Midcap 100"):
        if idx not in X:
            continue
        for rule, (title, src) in RULES.items():
            if rule == "fear_buy" and not v:
                continue
            o = rule_test(rule, days, X[idx], v, cut, s0)
            out.append({"key": f"{rule}:{idx}", "group": "timing", "title": f"{idx}: {title}", "plain": title,
                        "src": src, "sign": 1, "live": o.pop("on_today"), **o})
    M.holm(out)
    for o in out:
        o["verdict"] = M.verdict(o)
    return {"asof": days[-1], "from": days[s0], "oos_from": cut, "weeks": len(days) - s0, "regime": reg[-1],
            "regime_text": M.REGIME_TEXT.get(reg[-1], "Not enough history"), "results": out,
            "held": [o["key"] for o in out if o["verdict"] == "HOLDS"],
            "note": "Weekly candles from Dhan daily index history (close of each week's last session; the latest week "
                    "may still be open). Research software, not advice."}


def compare(w: dict, daily: dict) -> list:
    """Weekly verdict next to the daily verdict for the same key, where both exist."""
    dv = {b["key"]: b["verdict"] for b in daily.get("beliefs", []) + daily.get("ideas", [])}
    dv |= {t["key"].replace("trend200", "trend40").replace("breakout55", "breakout26"): t["verdict"] for t in daily.get("timing", [])}
    return [{"key": o["key"], "weekly": o["verdict"], "daily": dv.get(o["key"])} for o in w["results"]]


def markdown(w: dict) -> str:
    pc = lambda x: "n/a" if x is None else f"{x * 100:+.2f}%"
    L = [f"# Weekly re-test of every idea ({w['from']} to {w['asof']}, {w['weeks']} weeks)", "",
         f"Market type on weekly candles: **{w['regime_text']}**. Out of sample from {w['oos_from']}. "
         f"{len(w['held'])} of {len(w['results'])} hold after the many-ideas correction.", "",
         "| Idea | Verdict | Before: avg / right | Out of sample: avg / right | Months OOS | Daily verdict |",
         "|---|---|---|---|---|---|"]
    dv = {c["key"]: c["daily"] for c in w.get("compare", [])}
    for o in w["results"]:
        a, b = o["is"], o["oos"]
        L.append(f"| {o['title']} | {o['verdict']} | {pc(a.get('raw_mean'))} / {a['hit'] or 0:.0%} | "
                 f"{pc(b.get('raw_mean'))} / {b['hit'] or 0:.0%} | {b['months']} | {dv.get(o['key']) or '-'} |")
    L += ["", w["note"]]
    return "\n".join(L) + "\n"
