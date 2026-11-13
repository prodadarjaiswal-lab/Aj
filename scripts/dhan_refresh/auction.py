"""Order-flow and auction analysis from Dhan data.

What each module is built from, and how exact it is:
  EXACT (from Dhan 1-minute bars)  VWAP and anchored VWAP with deviation bands, Initial Balance,
                                   TPO / Market Profile (30-minute brackets), single prints, tails.
  DERIVED (bar approximation)      Volume Profile: a bar's volume is spread evenly over its high-low
                                   range, because Dhan gives no volume-at-price.
  ESTIMATE (no bid/ask trades)     Delta and cumulative delta: each 1-minute bar's volume is split
                                   by where it closed in its range. Dhan's feed sends snapshots, not
                                   every trade, so true bid/ask footprint and a full trade tape
                                   cannot be built from it. Named "est" everywhere.
  DERIVED (option chain)           Gamma exposure (GEX), gamma flip and strike walls, under the usual
                                   assumption that dealers are long calls and short puts.
Nothing here invents data: where an input is missing the field is None.
"""
from __future__ import annotations

import datetime as dt
import math

IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
OPEN_MIN = 9 * 60 + 15


def tick_for(price: float) -> float:
    """Profile bin size: about 0.1% of price, rounded to a tidy step."""
    raw = price * 0.001
    for step in (0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10, 25, 50, 100):
        if step >= raw:
            return step
    return 100.0


def sessions(bars: dict) -> dict:
    """Split {t,o,h,l,c,v} 1-minute arrays into {date: [(minute_of_day, o, h, l, c, v), ...]}."""
    out = {}
    for t, o, h, l, c, v in zip(bars["t"], bars["o"], bars["h"], bars["l"], bars["c"], bars["v"]):
        d = dt.datetime.fromtimestamp(t, IST)
        out.setdefault(d.date().isoformat(), []).append((d.hour * 60 + d.minute, o, h, l, c, v or 0))
    return out


# ---------------------------------------------------------------- volume profile
def volume_profile(rows: list, tick: float) -> dict:
    """DERIVED. Volume at price from bars; each bar's volume spread evenly across its range."""
    vol = {}
    for _, _, h, l, _, v in rows:
        lo, hi = int(math.floor(l / tick)), int(math.floor(h / tick))
        share = v / (hi - lo + 1)
        for k in range(lo, hi + 1):
            vol[k] = vol.get(k, 0.0) + share
    return _value_area(vol, tick)


def _value_area(hist: dict, tick: float, pct: float = 0.70) -> dict:
    if not hist or sum(hist.values()) <= 0:
        return {"poc": None, "vah": None, "val": None, "hvn": [], "lvn": [], "hist": {}}
    keys = sorted(hist)
    poc = max(keys, key=lambda k: (hist[k], -abs(k - (keys[0] + keys[-1]) / 2)))
    total, got = sum(hist.values()), hist[poc]
    lo = hi = poc
    while got < pct * total and (lo > keys[0] or hi < keys[-1]):      # standard two-row expansion
        up = hist.get(hi + 1, 0) + hist.get(hi + 2, 0) if hi < keys[-1] else -1
        dn = hist.get(lo - 1, 0) + hist.get(lo - 2, 0) if lo > keys[0] else -1
        if up >= dn:
            got += up
            hi = min(hi + 2, keys[-1])
        else:
            got += dn
            lo = max(lo - 2, keys[0])
    mean = total / len(keys)
    full = [hist.get(k, 0.0) for k in range(keys[0], keys[-1] + 1)]
    peaks, troughs = [], []
    for i in range(2, len(full) - 2):
        w = full[i - 2:i + 3]
        k = keys[0] + i
        if full[i] == max(w) and full[i] > 1.3 * mean and k != poc:
            peaks.append(k)
        if full[i] == min(w) and full[i] < 0.5 * mean and lo <= k <= hi + 0:
            troughs.append(k)
    px = lambda k: round((k + 0.5) * tick, 2)
    return {"poc": px(poc), "vah": round((hi + 1) * tick, 2), "val": round(lo * tick, 2),
            "hvn": [px(k) for k in peaks[:5]], "lvn": [px(k) for k in troughs[:5]],
            "hist": {px(k): round(v) for k, v in hist.items()}}


# ---------------------------------------------------------------- market profile (TPO)
def market_profile(rows: list, tick: float, bracket: int = 30, ib_minutes: int = 60) -> dict:
    """EXACT. TPO profile: one letter per 30-minute bracket at every price traded in it."""
    if not rows:
        return {}
    periods = {}
    for m, _, h, l, _, _ in rows:
        p = (m - OPEN_MIN) // bracket
        a = periods.setdefault(p, [l, h])
        a[0], a[1] = min(a[0], l), max(a[1], h)
    tpo = {}
    for p, (l, h) in periods.items():
        for k in range(int(math.floor(l / tick)), int(math.floor(h / tick)) + 1):
            tpo.setdefault(k, set()).add(p)
    counts = {k: len(v) for k, v in tpo.items()}
    va = _value_area(counts, tick)
    keys = sorted(counts)
    ib = [r for r in rows if r[0] < OPEN_MIN + ib_minutes]
    ib_h, ib_l = (max(r[2] for r in ib), min(r[3] for r in ib)) if ib else (None, None)
    hi, lo, close = max(r[2] for r in rows), min(r[3] for r in rows), rows[-1][4]
    # single prints: a run of 2+ prices visited by exactly one bracket, away from the day's extremes
    singles, run = [], []
    for k in keys + [None]:
        if k is not None and counts[k] == 1 and (not run or k == run[-1] + 1):
            run.append(k)
            continue
        if len(run) >= 2 and run[0] != keys[0] and run[-1] != keys[-1]:
            singles.append([round(run[0] * tick, 2), round((run[-1] + 1) * tick, 2)])
        run = [k] if k is not None and counts[k] == 1 else []
    # tails (excess): 2+ single-bracket prices at an extreme; without one the extreme is "poor"
    def tail(seq):
        n = 0
        for k in seq:
            if counts[k] == 1:
                n += 1
            else:
                break
        return n
    top, bot = tail(reversed(keys)), tail(keys)
    ext = None
    if ib_h is not None:
        ext = "both" if hi > ib_h and lo < ib_l else "up" if hi > ib_h else "down" if lo < ib_l else "none"
    return {"tpo_poc": va["poc"], "tpo_vah": va["vah"], "tpo_val": va["val"], "ib_high": round(ib_h, 2) if ib_h is not None else None, "ib_low": round(ib_l, 2) if ib_l is not None else None,
            "ib_extension": ext, "single_prints": singles[:6],
            "excess_high": top >= 2, "excess_low": bot >= 2, "poor_high": top < 2, "poor_low": bot < 2,
            "high": round(hi, 2), "low": round(lo, 2), "close": round(close, 2), "brackets": len(periods)}


# ---------------------------------------------------------------- VWAP
def vwap(rows: list, anchor_minute: int | None = None) -> dict:
    """EXACT (on 1-minute typical price). Session or anchored VWAP with volume-weighted 1 and 2 sigma bands."""
    pv = vv = pv2 = 0.0
    path = []
    for m, _, h, l, c, v in rows:
        if anchor_minute is not None and m < anchor_minute:
            continue
        tp = (h + l + c) / 3
        pv, vv, pv2 = pv + tp * v, vv + v, pv2 + tp * tp * v
        if vv > 0:
            path.append((m, pv / vv, c))
    if not path:
        return {"vwap": None}
    w = pv / vv
    sd = math.sqrt(max(pv2 / vv - w * w, 0.0))
    last = path[-1][2]
    # reclaim / rejection: last cross of price through VWAP, and how long price has held that side
    side = [1 if c >= x else -1 for _, x, c in path]
    held = 1
    for i in range(len(side) - 2, -1, -1):
        if side[i] != side[-1]:
            break
        held += 1
    crossed = held < len(side)
    state = ("reclaimed" if side[-1] > 0 else "lost") if crossed and held <= 30 else ("above" if side[-1] > 0 else "below")
    return {"vwap": round(w, 2), "sd": round(sd, 2), "up1": round(w + sd, 2), "dn1": round(w - sd, 2),
            "up2": round(w + 2 * sd, 2), "dn2": round(w - 2 * sd, 2),
            "dev_sd": round((last - w) / sd, 2) if sd else 0.0, "state": state, "minutes_on_side": held}


# ---------------------------------------------------------------- delta (estimate)
def delta_est(rows: list) -> dict:
    """ESTIMATE. Bar delta = volume x (2 x close-location - 1). Not true bid/ask delta."""
    cum, path, buy, sell = 0.0, [], 0.0, 0.0
    for m, _, h, l, c, v in rows:
        loc = (c - l) / (h - l) if h > l else 0.5
        d = v * (2 * loc - 1)
        cum += d
        buy, sell = buy + v * loc, sell + v * (1 - loc)
        path.append((m, c, cum))
    if not path:
        return {}
    tot = buy + sell
    # divergence: price at a new session extreme in the last 30 bars while cumulative delta is not
    div = None
    if len(path) > 60:
        px, cd = [p[1] for p in path], [p[2] for p in path]
        if max(px[-30:]) >= max(px) and max(cd[-30:]) < max(cd[:-30]):
            div = "bearish: price at the high, estimated buying is not"
        elif min(px[-30:]) <= min(px) and min(cd[-30:]) > min(cd[:-30]):
            div = "bullish: price at the low, estimated selling is not"
    # absorption proxy: the heaviest-volume bars that barely moved price
    vols = sorted(r[5] for r in rows)
    big = vols[int(0.98 * (len(vols) - 1))] if vols else 0
    rng = sorted((r[2] - r[3]) for r in rows)
    small = rng[len(rng) // 4] if rng else 0
    absorb = [{"minute": r[0], "price": r[4], "volume": r[5]} for r in rows if r[5] >= big > 0 and (r[2] - r[3]) <= small][:5]
    return {"cum_delta_est": round(cum), "buy_share_est": round(buy / tot, 3) if tot else None,
            "divergence_est": div, "absorption_est": absorb}


# ---------------------------------------------------------------- gamma exposure
def _bs_gamma(s, k, iv, t):
    if s <= 0 or k <= 0 or iv <= 0 or t <= 0:
        return 0.0
    d1 = (math.log(s / k) + 0.5 * iv * iv * t) / (iv * math.sqrt(t))
    return math.exp(-0.5 * d1 * d1) / math.sqrt(2 * math.pi) / (s * iv * math.sqrt(t))


def gex(spot: float, rows: list, days: float) -> dict:
    """DERIVED. rows: [(strike, call{oi,iv}, put{oi,iv})]. Units: OI x gamma x spot^2 x 1% (per 1% move),
    in rupees per share of underlying OI (multiply by nothing: Dhan OI is already in shares/units).
    Assumes dealers are long calls and short puts; if that is wrong the sign flips."""
    t = max(days, 0.5) / 365
    legs = [(k, (c or {}).get("oi") or 0, ((c or {}).get("iv") or 0) / 100, (p or {}).get("oi") or 0, ((p or {}).get("iv") or 0) / 100)
            for k, c, p in rows]
    legs = [x for x in legs if (x[1] and x[2]) or (x[3] and x[4])]
    if len(legs) < 5:
        return {"net_gex": None}

    def net(s):
        tot = 0.0
        for k, coi, civ, poi, piv in legs:
            tot += (coi * _bs_gamma(s, k, civ, t) - poi * _bs_gamma(s, k, piv, t)) * s * s * 0.01
        return tot
    per = {k: (coi * _bs_gamma(spot, k, civ, t) - poi * _bs_gamma(spot, k, piv, t)) * spot * spot * 0.01 for k, coi, civ, poi, piv in legs}
    total = sum(per.values())
    flip = None
    grid = [spot * (0.90 + 0.0025 * i) for i in range(81)]
    vals = [net(s) for s in grid]
    best = None
    for i in range(1, len(grid)):
        if vals[i - 1] == 0 or vals[i - 1] * vals[i] < 0:
            x = grid[i - 1] + (grid[i] - grid[i - 1]) * (-vals[i - 1]) / ((vals[i] - vals[i - 1]) or 1)
            if best is None or abs(x - spot) < abs(best - spot):
                best = x
    flip = round(best, 2) if best else None
    pos = sorted(((v, k) for k, v in per.items() if v > 0), reverse=True)[:3]
    neg = sorted(((v, k) for k, v in per.items() if v < 0))[:3]
    regime = None
    if total is not None:
        regime = "positive gamma: dealers trade against moves, ranges tend to hold" if total > 0 else \
                 "negative gamma: dealers trade with moves, swings tend to extend"
    return {"net_gex": round(total), "regime": regime, "gamma_flip": flip,
            "flip_vs_spot_pct": round((flip / spot - 1) * 100, 2) if flip else None,
            "call_gamma_strikes": [k for _, k in pos], "put_gamma_strikes": [k for _, k in neg],
            "by_strike": {k: round(v) for k, v in per.items()}}


# ---------------------------------------------------------------- one session read-out and auction context
def analyse(bars: dict, composite_days: int = 5) -> dict:
    """Latest session's profile, TPO, VWAP and delta estimate, plus prior-session and composite levels."""
    ses = sessions(bars)
    days = sorted(ses)
    if not days:
        return {}
    d = days[-1]
    rows = ses[d]
    tick = tick_for(rows[-1][4])
    out = {"date": d, "tick": tick, "bars": len(rows), "close": round(rows[-1][4], 2)}
    vp = volume_profile(rows, tick)
    out["vp"] = {k: vp[k] for k in ("poc", "vah", "val", "hvn", "lvn")}
    out["tpo"] = market_profile(rows, tick)
    out["vwap"] = vwap(rows)
    out["delta"] = delta_est(rows)
    if len(days) >= 2:
        prev = ses[days[-2]]
        pv = volume_profile(prev, tick)
        out["prev"] = {"date": days[-2], "poc": pv["poc"], "vah": pv["vah"], "val": pv["val"], "close": prev[-1][4]}
    if len(days) >= 2 and pv["vah"] is not None:
        o = rows[0][1]
        where = "above value" if o > pv["vah"] else "below value" if o < pv["val"] else "inside value"
        c = rows[-1][4]
        if where == "inside value":
            read = "balance: opened and stayed in yesterday's value" if pv["val"] <= c <= pv["vah"] else \
                   ("breakout above yesterday's value" if c > pv["vah"] else "breakdown below yesterday's value")
        elif where == "above value":
            read = "acceptance above yesterday's value" if c > pv["vah"] else "rejection: opened above value, closed back inside or below"
        else:
            read = "acceptance below yesterday's value" if c < pv["val"] else "rejection: opened below value, closed back inside or above"
        out["auction"] = {"open_vs_prev_value": where, "read": read}
    comp = [r for x in days[-composite_days:] for r in ses[x]]
    cv = volume_profile(comp, tick)
    out["composite"] = {"days": min(composite_days, len(days)), "poc": cv["poc"], "vah": cv["vah"], "val": cv["val"],
                        "hvn": cv["hvn"], "lvn": cv["lvn"]}
    return out


# ---------------------------------------------------------------- nightly job
def intraday(dhan, sid: str, segment: str, instrument: str, days: int = 8) -> dict:
    """1-minute bars from Dhan for the last `days` calendar days."""
    end = dt.datetime.now(IST)
    start = end - dt.timedelta(days=days)
    r = dhan.post("/charts/intraday", {"securityId": str(sid), "exchangeSegment": segment, "instrument": instrument,
                                       "interval": "1", "oi": False,
                                       "fromDate": start.strftime("%Y-%m-%d 09:00:00"), "toDate": end.strftime("%Y-%m-%d 16:00:00")})
    return {"t": r.get("timestamp") or [], "o": r.get("open") or [], "h": r.get("high") or [], "l": r.get("low") or [],
            "c": r.get("close") or [], "v": r.get("volume") or []}


def run(dhan, scrip_csv: str, root, symbols: list, indexes=("Nifty 50", "Nifty Bank")) -> str:
    """Write docs/auction.json (levels per symbol) and docs/auction-desk.md for the pinned chat."""
    import json
    from pathlib import Path
    import refresh as R
    root = Path(root)
    eq, ix = R.build_maps(scrip_csv, symbols, list(indexes))
    out, errs = {}, 0
    for name, sid, seg, inst in [(n, ix[n], "IDX_I", "INDEX") for n in indexes if n in ix] + [(s, eq[s], "NSE_EQ", "EQUITY") for s in symbols if s in eq]:
        try:
            bars = intraday(dhan, sid, seg, inst)
            if len(bars["t"]) < 100:
                continue
            a = analyse(bars)
            if seg == "IDX_I" or not sum(bars["v"][-375:]):      # an index has no traded volume: keep only the TPO read
                for k in ("vp", "vwap", "delta", "composite", "prev", "auction"):
                    a.pop(k, None)
                a["note"] = "index: no traded volume, so no volume profile, VWAP or delta"
            out[name] = a
        except Exception as e:
            errs += 1
            if errs <= 3:
                print(f"  auction {name}: {str(e)[:80]}")
    if not out:
        return "auction: no data"
    day = max(v["date"] for v in out.values())
    (root / "docs/auction.json").write_text(json.dumps({"asof": day, "symbols": out}, separators=(",", ":")), encoding="utf-8")
    (root / "docs/auction-desk.md").write_text(desk(day, out), encoding="utf-8")
    return f"auction: {len(out)} symbols for {day}, {errs} errors"


def desk(day: str, out: dict) -> str:
    L = [f"# Auction and order-flow desk · session {day}", "",
         "Built from Dhan 1-minute bars. **Exact:** VWAP, Initial Balance, TPO profile, single prints, tails. "
         "**Derived:** volume profile (bar volume spread across its range). **Estimate:** delta and absorption "
         "(from where each bar closed; Dhan has no bid/ask trade tape). "
         "These levels are context only: none has passed the back-test yet, so they do not change a verdict.", ""]
    for s in sorted(out):
        a = out[s]
        t = a.get("tpo", {})
        L.append(f"## {s} · close {a['close']}")
        if a.get("vp"):
            v, w, d = a["vp"], a["vwap"], a["delta"]
            L.append(f"- Volume profile (derived): POC {v['poc']}, value {v['val']} to {v['vah']}; high-volume {v['hvn'] or '-'}, low-volume {v['lvn'] or '-'}")
            L.append(f"- VWAP {w['vwap']} (bands {w['dn1']} to {w['up1']}); price is {w['dev_sd']} sd from VWAP, state: {w['state']} for {w['minutes_on_side']} min")
            L.append(f"- Delta (estimate): cumulative {d.get('cum_delta_est')}, buy share {d.get('buy_share_est')}"
                     + (f"; divergence {d['divergence_est']}" if d.get("divergence_est") else ""))
        if a.get("prev"):
            p = a["prev"]
            L.append(f"- Yesterday's value {p['val']} to {p['vah']}, POC {p['poc']}. Open was {a['auction']['open_vs_prev_value']}: {a['auction']['read']}")
        if a.get("composite"):
            c = a["composite"]
            L.append(f"- {c['days']}-day composite: POC {c['poc']}, value {c['val']} to {c['vah']}")
        if t:
            L.append(f"- TPO: POC {t['tpo_poc']}, value {t['tpo_val']} to {t['tpo_vah']}; Initial Balance {t['ib_low']} to {t['ib_high']}, "
                     f"extension {t['ib_extension']}; single prints {t['single_prints'] or '-'}; "
                     f"{'excess' if t['excess_high'] else 'poor'} high, {'excess' if t['excess_low'] else 'poor'} low")
        if a.get("note"):
            L.append(f"- {a['note']}")
        L.append("")
    return "\n".join(L)
