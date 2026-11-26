"""Trading Terminal back-test: the desk's picks bought at 09:30, 12:30 and 15:00 IST over the last month.

Research software, not advice. Never places orders.

For each session D of the last ~22 sessions and each Nifty 500 stock:
  pick      the stock had a NEW daily signal on one of the 3 closes up to D-1 that is tested for that day's market
            (docs/tech-model.json: 'tested' when the Nifty was above its 200-day average, else 'tested_weak'),
            and 20-day average turnover of Rs 5 crore or more.
  entry     close of the 5-minute Dhan bar ending at the checkpoint (09:30, 12:30, 15:00), long only.
  exits     day   : the 15:25 bar close, same day (intraday, 0.06% round-trip cost)
            plan  : stop entry - 0.5 x ATR14, target entry + 1.0 x ATR14 on 5-minute bars, else the 15:25 close
                    (stop counted first when a bar touches both)
            next  : next session's close (overnight hold, 0.25% delivery cost)
  excess    each return minus the Nifty 50's return over the same window.
  rupees    shares = floor(max_loss_per_trade / (0.5 x ATR)) capped by capital (config/trading.json), plan exit,
            at most 5 picks per checkpoint per day (most signals first, then strongest vs the Nifty at entry).

Intraday filters known at the checkpoint (no look-ahead) are tested on the picks and on all stocks, to find a
better screener: above session VWAP, up from the open, stronger than the Nifty since the previous close,
volume pace >= 1.5x the same time on the last 10 sessions, above the 09:15-09:30 range.
A rule "passes the one-month test" when n >= 30, mean net excess > 0 in both halves of the month and t >= 2.
One month is a short sample: a pass is a lead to watch, not proof.

Also writes the markets board (indices, ETFs, MCX futures) with 60 sessions of closes.
Outputs docs/terminal/backtest.json, docs/terminal/markets.json, docs/terminal/watch.json.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import os
import statistics as st
import sys
from pathlib import Path

CHECKS = {"09:30": 9 * 60 + 25, "12:30": 12 * 60 + 25, "15:00": 14 * 60 + 55}   # 5-min bar start; entry = its close
LAST_BAR = 15 * 60 + 20
COST_DAY, COST_NEXT = 0.0006, 0.0025
STOP_ATR, TGT_ATR = 0.5, 1.0
SESSIONS = 22
MAX_PER_CHECK = 5          # rupee P&L: at most this many picks per checkpoint per day (more signals, then stronger vs Nifty)
MIN_TURNOVER_CR = 5.0      # picks need 20-day average turnover of Rs 5 crore or more

INDICES = ["Nifty 50", "Nifty Bank", "Nifty IT", "Nifty Midcap 100", "Nifty Financial Services", "Nifty Auto",
           "Nifty Pharma", "Nifty FMCG", "Nifty Metal", "Nifty Energy", "Nifty PSU Bank", "Nifty Realty", "India VIX"]
IDX_IDS = {"Nifty 50": 13, "Nifty IT": 29, "Nifty Bank": 25, "Nifty FMCG": 28, "Nifty Pharma": 32, "Nifty Auto": 14,
           "Nifty Metal": 31, "Nifty Realty": 34, "Nifty Energy": 42, "Nifty PSU Bank": 33,
           "Nifty Financial Services": 27, "Nifty Midcap 100": 37, "India VIX": 21}
ETFS = {"NIFTYBEES": "Nifty 50 ETF", "BANKBEES": "Bank Nifty ETF", "JUNIORBEES": "Nifty Next 50 ETF",
        "ITBEES": "Nifty IT ETF", "PSUBNKBEES": "PSU Bank ETF", "CPSEETF": "CPSE ETF", "MON100": "Nasdaq 100 ETF",
        "GOLDBEES": "Gold ETF", "SILVERBEES": "Silver ETF", "LIQUIDBEES": "Liquid ETF"}

FILTERS = {
    "any": "No intraday filter",
    "vwap": "Above session VWAP",
    "up_open": "Up from today's open",
    "rs": "Stronger than the Nifty since yesterday's close",
    "volx": "Volume pace 1.5x usual for this time",
    "orb": "Above the 09:15-09:30 range",
    "vwap_rs": "Above VWAP and stronger than the Nifty",
    "vwap_rs_volx": "Above VWAP, stronger than the Nifty, volume 1.5x",
}


# ---------------------------------------------------------------- pure helpers (tested offline)
def bar_at(rows: list, minute: int):
    """Index of the 5-minute bar starting at `minute` (or the last bar before it)."""
    k = None
    for i, r in enumerate(rows):
        if r[0] <= minute:
            k = i
        else:
            break
    return k


def features(rows: list, i: int, prev_close: float, n_ret: float, pace: float | None) -> dict:
    """Intraday state at bar i using only bars 0..i."""
    c = rows[i][4]
    pv = sum((r[2] + r[3] + r[4]) / 3 * r[5] for r in rows[:i + 1])
    vol = sum(r[5] for r in rows[:i + 1])
    vwap = pv / vol if vol else c
    orb = [r for r in rows if r[0] < 9 * 60 + 30]
    orb_h = max(r[2] for r in orb) if orb else None
    r_prev = c / prev_close - 1 if prev_close else 0.0
    f = {"vwap": c > vwap, "up_open": c > rows[0][1], "rs": r_prev - n_ret > 0,
         "volx": bool(pace and pace >= 1.5), "orb": bool(orb_h and rows[i][0] >= 9 * 60 + 30 and c > orb_h)}
    f["any"] = True
    f["vwap_rs"] = f["vwap"] and f["rs"]
    f["vwap_rs_volx"] = f["vwap_rs"] and f["volx"]
    return f


def plan_exit(rows: list, i: int, atr: float) -> tuple[float, str]:
    """Exit price and reason for stop/target on bars after i, else the last bar's close."""
    e = rows[i][4]
    s, t = e - STOP_ATR * atr, e + TGT_ATR * atr
    last = rows[i][4]
    for r in rows[i + 1:]:
        if r[0] > LAST_BAR:
            break
        if r[3] <= s:
            return s, "stop"
        if r[2] >= t:
            return t, "target"
        last = r[4]
    return last, "close"


def close_at(rows: list, minute: int = LAST_BAR) -> float | None:
    k = bar_at(rows, minute)
    return rows[k][4] if k is not None else None


def summarize(xs: list, days: list) -> dict:
    """xs: [(net_excess, net_ret, day)] -> stats with the two halves of the month."""
    if not xs:
        return {"n": 0}
    ex = [x[0] for x in xs]
    m = sum(ex) / len(ex)
    sd = st.pstdev(ex) if len(ex) > 1 else 0.0
    t = m / (sd / math.sqrt(len(ex))) if sd > 0 else 0.0
    mid = days[len(days) // 2] if days else ""
    a = [x[0] for x in xs if x[2] < mid]
    b = [x[0] for x in xs if x[2] >= mid]
    mean = lambda v: sum(v) / len(v) if v else None
    out = {"n": len(xs), "ex": round(m * 100, 3), "ret": round(mean([x[1] for x in xs]) * 100, 3),
           "hit": round(sum(x[1] > 0 for x in xs) / len(xs), 3), "t": round(t, 2),
           "h1": round(mean(a) * 100, 3) if a else None, "h2": round(mean(b) * 100, 3) if b else None}
    out["pass"] = bool(out["n"] >= 30 and t >= 2 and a and b and mean(a) > 0 and mean(b) > 0)
    return out


def atr14(h, l, c, i):
    if i < 15:
        return None
    tr = [max(h[k] - l[k], abs(h[k] - c[k - 1]), abs(l[k] - c[k - 1])) for k in range(i - 13, i + 1)]
    return sum(tr) / 14


def regime_up(nc: list, i: int) -> bool:
    """Nifty above its 200-day average at index i (the desk's rule in tradeplan.regime_up)."""
    return i < 200 or nc[i] > sum(nc[i - 199:i + 1]) / 200


def turnover_ok(c, v, i) -> bool:
    if not v:
        return True
    k = range(max(0, i - 19), i + 1)
    return sum(c[j] * (v[j] or 0) for j in k) / len(k) / 1e7 >= MIN_TURNOVER_CR


def backtest(daily: dict, intra: dict, nifty_d: dict, nifty_i: dict, tested, cfg: dict) -> dict:
    """daily[sym] = {d,o,h,l,c,v}; intra[sym] = {date: rows}; nifty_d = {d,c}; nifty_i = {date: rows}."""
    import tech_model as TM
    days = sorted(d for d in nifty_i if len(nifty_i[d]) >= 60)[-SESSIONS:]
    nclose = dict(zip(nifty_d["d"], nifty_d["c"]))
    t_up, t_weak = tested if isinstance(tested, tuple) else (set(tested), set(tested))
    npos = {d: i for i, d in enumerate(nifty_d["d"])}
    cand = {}
    cap, maxloss = float(cfg.get("capital", 100000)), float(cfg.get("max_loss_per_trade", 1000))
    res = {(pop, ck, f, ex): [] for pop in ("picks", "all") for ck in CHECKS for f in FILTERS for ex in ("day", "plan", "next")}
    trades, by_signal, daily_pnl = [], {}, {d: {ck: 0.0 for ck in CHECKS} for d in days}
    picks_by_day = {}
    for sym, o in daily.items():
        if sym not in intra:
            continue
        keep = [i for i, d in enumerate(o["d"]) if d in nclose]
        if len(keep) < 300:
            continue
        d_ = [o["d"][i] for i in keep]
        col = {k: [o[k][i] for i in keep] for k in ("o", "h", "l", "c")}
        v = [o["v"][i] for i in keep] if o.get("v") else None
        T = TM.Tech(col["o"], col["h"], col["l"], col["c"], v, [nclose[x] for x in d_])
        pos = {d: i for i, d in enumerate(d_)}
        sess = intra[sym]
        sdays = sorted(sess)
        flag_cache = {}

        def flags(i):
            if i not in flag_cache:
                flag_cache[i] = T.flags(i)
            return flag_cache[i]
        for D in days:
            prev = [x for x in d_ if x < D]
            if not prev or D not in sess or D not in nifty_i:
                continue
            ip = pos[prev[-1]]
            if ip < 260:
                continue
            new = set().union(*(flags(k) - flags(k - 1) for k in range(ip - 2, ip + 1))) & flags(ip)
            up = regime_up(nifty_d["c"], npos[prev[-1]]) if prev[-1] in npos else True
            sig = sorted(new & (t_up if up else t_weak)) if turnover_ok(col["c"], v, ip) else []
            is_pick = bool(sig)
            if is_pick:
                picks_by_day.setdefault(D, []).append(sym)
            rows, nrows = sess[D], nifty_i[D]
            pc = col["c"][ip]
            a = atr14(col["h"], col["l"], col["c"], ip)
            if not a or not pc:
                continue
            nprev = nclose.get(prev[-1])
            n_close = close_at(nrows)
            nxt = [x for x in d_ if x > D]
            nxt_c = col["c"][pos[nxt[0]]] if nxt else None
            nxt_n = nclose.get(nxt[0]) if nxt else None
            hist = [x for x in sdays if x < D][-10:]
            for ck, m in CHECKS.items():
                i = bar_at(rows, m)
                j = bar_at(nrows, m)
                if i is None or j is None or rows[i][0] < m - 10:
                    continue
                e, ne = rows[i][4], nrows[j][4]
                cumv = sum(r[5] for r in rows[:i + 1])
                usual = [sum(r[5] for r in sess[x] if r[0] <= m) for x in hist]
                pace = cumv / (sum(usual) / len(usual)) if usual and sum(usual) else None
                f = features(rows, i, pc, ne / nprev - 1 if nprev else 0.0, pace)
                c_day = close_at(rows)
                n_ret_day = n_close / ne - 1 if n_close and ne else 0.0
                px, why = plan_exit(rows, i, a)
                outs = {"day": (c_day / e - 1 - COST_DAY, n_ret_day), "plan": (px / e - 1 - COST_DAY, n_ret_day)}
                if nxt_c and nxt_n and ne:
                    outs["next"] = (nxt_c / e - 1 - COST_NEXT, nxt_n / ne - 1)
                for pop in (("picks", "all") if is_pick else ("all",)):
                    for fk, on in f.items():
                        if not on:
                            continue
                        for ex, (r, nr) in outs.items():
                            res[(pop, ck, fk, ex)].append((r - nr, r, D))
                if is_pick:
                    qty = min(math.floor(maxloss / (STOP_ATR * a)), math.floor(cap / e))
                    pnl = qty * (px - e) - qty * e * COST_DAY
                    cand.setdefault((D, ck), []).append((len(sig), (e / pc - 1) - (ne / nprev - 1 if nprev else 0), pnl))
                    trades.append({"d": D, "ck": ck, "s": sym, "sig": sig, "e": round(e, 2), "x": round(px, 2), "why": why,
                                   "qty": qty, "pnl": round(pnl), "ret": round((px / e - 1 - COST_DAY) * 100, 2),
                                   "f": [k for k in ("vwap", "up_open", "rs", "volx", "orb") if f[k]]})
                    for s_ in sig:
                        by_signal.setdefault((s_, ck), []).append((outs["plan"][0] - outs["plan"][1], outs["plan"][0], D))
    for (D, ck), xs in cand.items():
        daily_pnl[D][ck] = sum(x[2] for x in sorted(xs, key=lambda x: (-x[0], -x[1]))[:MAX_PER_CHECK])
    out = {"days": days, "checks": list(CHECKS), "filters": FILTERS, "grid": {}, "signals": {}, "equity": {}}
    for (pop, ck, fk, ex), xs in res.items():
        out["grid"].setdefault(pop, {}).setdefault(ck, {}).setdefault(fk, {})[ex] = summarize(xs, days)
    for (s_, ck), xs in by_signal.items():
        out["signals"].setdefault(s_, {})[ck] = summarize(xs, days)
    for ck in CHECKS:
        run, eq = 0.0, []
        for D in days:
            run += daily_pnl[D][ck]
            eq.append(round(run))
        out["equity"][ck] = eq
    out["picks_per_day"] = {D: len(picks_by_day.get(D, [])) for D in days}
    out["trades"] = sorted(trades, key=lambda t: (t["d"], t["ck"]))[-400:]
    best = []
    for ck in CHECKS:
        for pop in ("picks", "all"):
            for fk in FILTERS:
                for ex in ("day", "plan", "next"):
                    s_ = out["grid"][pop][ck][fk][ex]
                    if s_.get("pass"):
                        best.append({"pop": pop, "ck": ck, "f": fk, "exit": ex, **s_})
    out["passing"] = sorted(best, key=lambda b: -b["t"])
    return out


def watchlist(daily: dict, nifty_d: dict, tested, cfg: dict) -> list:
    """Picks for the next session: new tested signal on the last 3 closes, with ATR plan levels."""
    import tech_model as TM
    nclose = dict(zip(nifty_d["d"], nifty_d["c"]))
    t_up, t_weak = tested if isinstance(tested, tuple) else (set(tested), set(tested))
    tested = t_up if regime_up(nifty_d["c"], len(nifty_d["c"]) - 1) else t_weak
    out = []
    for sym, o in daily.items():
        keep = [i for i, d in enumerate(o["d"]) if d in nclose]
        if len(keep) < 300:
            continue
        col = {k: [o[k][i] for i in keep] for k in ("o", "h", "l", "c")}
        v = [o["v"][i] for i in keep] if o.get("v") else None
        T = TM.Tech(col["o"], col["h"], col["l"], col["c"], v, [nclose[o["d"][i]] for i in keep])
        i = len(keep) - 1
        new = set().union(*(T.flags(k) - T.flags(k - 1) for k in range(i - 2, i + 1))) & T.flags(i)
        sig = sorted(new & tested) if turnover_ok(col["c"], v, i) else []
        a = atr14(col["h"], col["l"], col["c"], i)
        if sig and a:
            c = col["c"][i]
            out.append({"s": sym, "sig": sig, "c": round(c, 2), "atr": round(a, 2), "stop_atr": STOP_ATR, "tgt_atr": TGT_ATR,
                        "qty_rule": math.floor(float(cfg.get("max_loss_per_trade", 1000)) / (STOP_ATR * a))})
    return sorted(out, key=lambda r: (-len(r["sig"]), r["s"]))


# ---------------------------------------------------------------- Dhan fetch
def find_ids(scrip_csv: str, symbols: list) -> dict:
    """NSE cash ids for stocks and ETFs (ETFs are not always flagged EQUITY in Dhan's list)."""
    import csv
    import io
    want, out = set(symbols), {}
    for r in csv.DictReader(io.StringIO(scrip_csv)):
        if r.get("SEM_EXM_EXCH_ID") != "NSE" or r.get("SEM_SEGMENT") != "E":
            continue
        sym = r.get("SEM_TRADING_SYMBOL", "")
        if sym in want and (sym not in out or r.get("SEM_SERIES") == "EQ"):
            out[sym] = r["SEM_SMST_SECURITY_ID"]
    return out


def series(resp: dict, ist) -> dict:
    ts = resp.get("timestamp") or []
    return {"d": [dt.datetime.fromtimestamp(t, ist).date().isoformat() for t in ts], "o": list(resp.get("open") or []),
            "h": list(resp.get("high") or []), "l": list(resp.get("low") or []), "c": list(resp.get("close") or []),
            "v": list(resp.get("volume") or []) or None}


def intraday5(dhan, sid, seg, inst, days=40) -> dict:
    import auction as A
    import refresh as R
    end = dt.datetime.now(R.IST)
    s = end - dt.timedelta(days=days)
    r = dhan.post("/charts/intraday", {"securityId": str(sid), "exchangeSegment": seg, "instrument": inst, "interval": "5",
                                       "oi": False, "fromDate": s.strftime("%Y-%m-%d 09:00:00"),
                                       "toDate": end.strftime("%Y-%m-%d 16:00:00")})
    return A.sessions({k: r.get(n) or [] for k, n in (("t", "timestamp"), ("o", "open"), ("h", "high"), ("l", "low"),
                                                      ("c", "close"), ("v", "volume"))} | {"v": r.get("volume") or [0] * len(r.get("timestamp") or [])})


def markets(dhan, scrip_csv: str, now) -> dict:
    import markets as MK
    import refresh as R
    start = now.date() - dt.timedelta(days=3 * 365 + 20)
    out = {"asof": now.strftime("%Y-%m-%d %H:%M"), "groups": {"Indices": [], "ETFs": [], "MCX": []}, "missing": [],
           "live_ids": {"IDX_I": {}, "NSE_EQ": {}, "MCX_COMM": {}}}

    def row(name, label, seg, inst, sid, extra=None):
        try:
            s = series(dhan.daily(sid, seg, inst, start, now.date()), R.IST)
            pairs = [(d, x) for d, x in zip(s["d"], s["c"]) if x]
            c = [x for _, x in pairs]
            if len(c) < 2:
                raise ValueError("no history")
            r = {"k": name, "name": label, "sid": int(sid), "seg": seg, "last": c[-1], "prev": c[-2],
                 "chg": round(c[-1] / c[-2] - 1, 5), "r5": round(c[-1] / c[-6] - 1, 4) if len(c) > 5 else None,
                 "r21": round(c[-1] / c[-22] - 1, 4) if len(c) > 21 else None, "d": s["d"][-1], "spark": c[-60:],
                 "hist": {"d": [d for d, _ in pairs[-760:]], "c": c[-760:]}}
            r.update(extra or {})
            out["live_ids"][seg][str(sid)] = name
            return r
        except Exception as e:
            out["missing"].append(f"{name}: {str(e)[:60]}")
            return None
    for name in INDICES:
        r = row(name, name, "IDX_I", "INDEX", IDX_IDS[name])
        r and out["groups"]["Indices"].append(r)
    ids = find_ids(scrip_csv, list(ETFS))
    for sym, label in ETFS.items():
        if sym not in ids:
            out["missing"].append(f"{sym}: not in Dhan's list")
            continue
        r = row(sym, label, "NSE_EQ", "EQUITY", ids[sym])
        r and out["groups"]["ETFs"].append(r)
    fut = MK.pick_futures(scrip_csv, now.date())
    for name in MK.COMMODITIES:
        if name not in fut:
            out["missing"].append(f"{name}: no live MCX contract")
            continue
        seg, sid, sym, exp = fut[name]
        r = row(name, MK.NAMES[name], seg, "FUTCOM", sid, {"contract": sym, "expiry": exp.isoformat()})
        r and out["groups"]["MCX"].append(r)
    add_today_close(dhan, out, now)
    return out


def add_today_close(dhan, out: dict, now) -> int:
    """Dhan's daily history gets today's bar only hours after the close, so an evening run would show
    yesterday's close. Like refresh.append_today, add today's close from the quote API after 15:35 IST."""
    import refresh as R
    day = now.date().isoformat()
    if now.weekday() >= 5 or now.timetz().replace(tzinfo=None) < R.CLOSE_DONE:
        return 0
    rows = [r for g in ("Indices", "ETFs") for r in out["groups"][g] if r.get("d", day) < day]
    if not rows:
        return 0
    try:
        qs = R.quotes(dhan, [r["sid"] for r in rows if r["seg"] == "NSE_EQ"], [r["sid"] for r in rows if r["seg"] == "IDX_I"])
    except Exception as e:
        print(f"  markets: could not add today's close from quotes: {str(e)[:120]}")
        return 0
    n = 0
    for r in rows:
        q = qs.get((r["seg"], str(r["sid"])))
        if not q or q[3] <= 0 or q[0] <= 0 or abs(q[3] / r["last"] - 1) < 1e-6:  # holiday: quote repeats last close
            continue
        ltp = q[3]
        c = list(r["spark"]) + [ltp]
        r.update(prev=r["last"], last=ltp, d=day, chg=round(ltp / r["last"] - 1, 5), spark=c[-60:])
        if r.get("hist"):
            r["hist"] = {"d": r["hist"]["d"] + [day], "c": r["hist"]["c"] + [ltp]}
        if len(c) > 5:
            r["r5"] = round(c[-1] / c[-6] - 1, 4)
        if len(c) > 21:
            r["r21"] = round(c[-1] / c[-22] - 1, 4)
        n += 1
    print(f"  markets: added today's close to {n} rows", flush=True)
    return n


def main() -> int:
    import requests
    import n500
    import refresh as R
    root = Path(sys.argv[sys.argv.index("--root") + 1]) if "--root" in sys.argv else Path(__file__).resolve().parents[2]
    outdir = root / "docs/terminal"
    outdir.mkdir(parents=True, exist_ok=True)
    cfg = json.loads((root / "config/trading.json").read_text(encoding="utf-8")) if (root / "config/trading.json").exists() else {}
    cfg = {k: (v.get("v") if isinstance(v, dict) else v) for k, v in cfg.items()}
    tm = json.loads((root / "docs/tech-model.json").read_text(encoding="utf-8"))
    tested = ({k for k, r in tm["signals"].items() if r.get("tested")}, {k for k, r in tm["signals"].items() if r.get("tested_weak")})
    cid, pin, sec = (os.environ[k] for k in ("DHAN_CLIENT_ID", "DHAN_PIN", "DHAN_TOTP_SECRET"))
    dhan = R.Dhan(cid, R.login(cid, pin, sec))
    now = dt.datetime.now(R.IST)
    scrip = requests.get(R.SCRIP_MASTER, timeout=60).text
    mk = markets(dhan, scrip, now)
    (outdir / "markets.json").write_text(json.dumps(mk, separators=(",", ":")), encoding="utf-8")
    print(f"markets: {sum(len(v) for v in mk['groups'].values())} rows; missing {mk['missing']}", flush=True)
    rows = [r for r in json.loads((root / "docs/n500.json").read_text(encoding="utf-8"))["rows"] if r.get("sid")]
    if "--limit" in sys.argv:
        rows = rows[:int(sys.argv[sys.argv.index("--limit") + 1])]
    start = now.date() - dt.timedelta(days=820)
    nifty_d = series(dhan.daily(13, "IDX_I", "INDEX", start, now.date()), R.IST)
    nifty_i = intraday5(dhan, 13, "IDX_I", "INDEX")
    daily, intra, skipped = {}, {}, []
    for n, r in enumerate(rows):
        try:
            daily[r["s"]] = series(dhan.daily(r["sid"], "NSE_EQ", "EQUITY", start, now.date()), R.IST)
            intra[r["s"]] = intraday5(dhan, r["sid"], "NSE_EQ", "EQUITY")
        except Exception as e:
            skipped.append(r["s"])
            print(f"  skip {r['s']}: {str(e)[:80]}")
        if n % 50 == 0:
            print(f"  fetched {n}/{len(rows)}", flush=True)
    res = backtest(daily, intra, nifty_d, nifty_i, tested, cfg)
    res.update({"asof": now.strftime("%Y-%m-%d %H:%M"), "stocks": len(daily), "skipped": skipped, "tested": {"rising": sorted(tested[0]), "weak": sorted(tested[1])},
                "signal_names": tm.get("names", {}), "cfg": {"capital": cfg.get("capital"), "max_loss": cfg.get("max_loss_per_trade")},
                "method": __doc__.split("\n\n", 1)[1].split("Also writes")[0].strip()})
    (outdir / "backtest.json").write_text(json.dumps(res, separators=(",", ":")), encoding="utf-8")
    wl = watchlist(daily, nifty_d, tested, cfg)
    (outdir / "watch.json").write_text(json.dumps({"asof": nifty_d["d"][-1], "rows": wl}, separators=(",", ":")), encoding="utf-8")
    print(f"backtest: {len(res['days'])} sessions {res['days'][:1]}..{res['days'][-1:]}, {len(res['trades'])} pick trades, "
          f"{len(res['passing'])} rules pass; watchlist {len(wl)}")
    for ck in CHECKS:
        g = res["grid"]["picks"][ck]["any"]
        print(f"  picks {ck}: day={g['day']} plan={g['plan']} next={g.get('next')}")
    for b in res["passing"][:10]:
        print(f"  PASS {b}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
