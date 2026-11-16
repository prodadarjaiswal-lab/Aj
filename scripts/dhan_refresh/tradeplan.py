"""Trade plan: one plan per stock whose new signal passed the out-of-sample back-test.

Research software, not advice. It prints levels to place by hand; it never sends orders.

  entry   last Dhan close (the back-test buys at the close of the day the signal appears), snapped to the tick
  stop    entry - stop_k x one day's volatility (docs/risklab.json vol[SYM].d1 when present, else ATR 14)
  target  entry x (1 + the signal's tested out-of-sample average excess move over horizon_days)
  odds    quant.bootstrap_paths on the stock's own daily returns (demeaned, plus the signal's tested drift),
          stop and target applied path by path on daily closes, net of round-trip charges
  size    floor(max_loss_per_trade / (entry - stop)), capped by capital and by stock_cap (config/portfolio.json)

Method ported from the trader-entry / trader-exit / trader-timemachine / trader-budget / trader-risk and
nse-day-trader skills (charges table, reward:risk floor, sizing limits, daily loss limit). Prices: Dhan only.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

import quant
from auction import tick_for

RATE_KEYS = ("brokerage_pct", "brokerage_cap_rs", "brokerage_min_rs", "stt_buy_pct", "stt_sell_pct", "stamp_buy_pct",
             "exchange_pct", "sebi_pct", "ipft_pct", "dp_sell_rs", "gst_pct")


def _j(p: Path, default):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return default


def snap(x: float, tick: float, how: str = "near") -> float:
    """Snap a price to a multiple of tick: down, up or nearest."""
    q = x / tick
    n = math.floor(q + 1e-9) if how == "down" else math.ceil(q - 1e-9) if how == "up" else round(q)
    return round(n * tick, 2)


def rates(cfg: dict) -> dict:
    """Plain {key: value} charge rates for the configured product."""
    block = (cfg.get("charges") or {}).get(cfg.get("product", "delivery")) or {}
    return {k: float((block.get(k) or {}).get("v", 0) if isinstance(block.get(k), dict) else block.get(k, 0) or 0) for k in RATE_KEYS}


def charges(buy_val, sell_val, r: dict):
    """Round-trip Indian equity charges in rupees for a buy of buy_val and a sell of sell_val (scalars or arrays)."""
    buy_val, sell_val = np.asarray(buy_val, float), np.asarray(sell_val, float)

    def brk(v):
        if r["brokerage_pct"] <= 0:
            return np.zeros_like(v)
        return np.maximum(r["brokerage_min_rs"], np.minimum(r["brokerage_cap_rs"], v * r["brokerage_pct"] / 100))

    turnover = buy_val + sell_val
    brokerage = brk(buy_val) + brk(sell_val)
    stt = buy_val * r["stt_buy_pct"] / 100 + sell_val * r["stt_sell_pct"] / 100
    stamp = buy_val * r["stamp_buy_pct"] / 100
    exch = turnover * r["exchange_pct"] / 100
    sebi = turnover * r["sebi_pct"] / 100
    ipft = turnover * r["ipft_pct"] / 100
    dp = np.where(sell_val > 0, r["dp_sell_rs"], 0.0)
    gst = (brokerage + exch + sebi + ipft + dp) * r["gst_pct"] / 100
    out = brokerage + stt + stamp + exch + sebi + ipft + dp + gst
    return float(out) if out.ndim == 0 else out


def size(entry: float, stop: float, cfg: dict, stock_cap: float) -> tuple[int, str]:
    """Whole shares within max loss per trade, capital and the position cap; and which limit decided."""
    cap = float(cfg["capital"])
    lim = {"max loss per trade": math.floor(float(cfg["max_loss_per_trade"]) / (entry - stop)) if entry > stop else 0,
           "capital": math.floor(cap / entry),
           f"position cap {stock_cap:.0%} of capital": math.floor(stock_cap * cap / entry)}
    by = min(lim, key=lim.get)
    return max(0, lim[by]), by


def simulate(close: list, entry: float, stop: float, target: float, qty: int, drift: float, days: int, r: dict,
             n: int = 10000) -> dict:
    """Bootstrap odds: share of paths that close at/above target first, at/below stop first; mean net rupees."""
    c = np.asarray([x for x in close[-501:] if x and x > 0], float)
    lr = np.diff(np.log(c))
    lr = lr - lr.mean() + drift
    paths = entry * np.exp(quant.bootstrap_paths(lr, days=days, n=n))
    hit_t, hit_s = paths >= target, paths <= stop
    big = days + 1
    ft = np.where(hit_t.any(1), hit_t.argmax(1), big)
    fs = np.where(hit_s.any(1), hit_s.argmax(1), big)
    tgt, stp = ft < fs, fs < ft
    exitp = np.where(tgt, target, np.where(stp, stop, paths[:, -1]))     # a stop can fill worse in a gap
    q = max(qty, 0)
    net = q * (exitp - entry) - (charges(q * entry, q * exitp, r) if q else 0.0)
    return {"p_target": round(float(tgt.mean()), 3), "p_stop": round(float(stp.mean()), 3),
            "exp_net_rs": round(float(np.mean(net)), 2) if q else None}


def regime_up(nifty: dict) -> bool:
    c = nifty.get("c") or []
    return len(c) < 200 or c[-1] > sum(c[-200:]) / 200


def best_signal(new: list, signals: dict, up: bool, horizon: int):
    """The new signal with the largest tested out-of-sample move for today's market regime (long side only)."""
    flag, side, hk = ("tested", "up", f"x{horizon}") if up else ("tested_weak", "weak", f"x{horizon}")
    best = None
    for k in new:
        s = signals.get(k) or {}
        o = (s.get("out") or {}).get(side) or {}
        if s.get(flag) and (o.get(hk) or 0) > 0 and (best is None or o[hk] > best[1][hk]):
            best = (k, o)
    return best


def turnover_cr(o: dict, days: int = 20) -> float | None:
    c, v = o.get("c") or [], o.get("v") or []
    if not c or not v:
        return None
    k = min(days, len(c), len(v))
    return sum(c[-i] * v[-i] for i in range(1, k + 1)) / k / 1e7


def events_in(feeds: dict, sym: str, asof: str, horizon: int) -> list:
    import datetime as dt
    try:
        d0 = dt.date.fromisoformat(asof[:10])
    except ValueError:
        return []
    cal = math.ceil(horizon * 7 / 5)
    out = []
    for e in (feeds.get("events") or {}).get(sym) or []:
        p = (e.get("p") or "").lower()
        try:
            dd = (dt.date.fromisoformat(e.get("d", "")) - d0).days
        except ValueError:
            continue
        if 0 <= dd <= cal and any(w in p for w in ("result", "board", "financial")):
            out.append(e)
    return out


def plan_one(sym: str, o: dict, td: dict, sig: tuple, cfg: dict, r: dict, vol: dict, stock_cap: float, min_cr: float,
             feeds: dict, asof: str, up: bool) -> dict | None:
    key, st = sig
    h = int(cfg.get("horizon_days", 21))
    last = float(td.get("c") or o["c"][-1])
    tick = tick_for(last)
    entry = snap(last, tick)
    v = (vol.get(sym) or {}).get("d1")
    if v:
        v = float(v) / 100 if float(v) >= 0.5 else float(v)                # accept a percent or a fraction
        vol_rs, vol_src = v * entry, "risklab daily vol"
    elif td.get("atr"):
        vol_rs, vol_src = float(td["atr"]), "ATR 14"
    else:
        return None
    stop = snap(entry - float(cfg.get("stop_k", 1.5)) * vol_rs, tick, "down")
    move = float(st[f"x{h}"])
    target = snap(entry * (1 + move), tick, "down")
    if stop <= 0 or stop >= entry:
        return None
    rr = round((target - entry) / (entry - stop), 2)
    qty, by = size(entry, stop, cfg, stock_cap)
    sim = simulate(o["c"], entry, stop, target, qty, math.log1p(move) / h, h, r, int(cfg.get("paths", 10000)))
    ch = round(charges(qty * entry, qty * entry, r), 2) if qty else 0.0
    risk = round(qty * (entry - stop), 2)
    to = turnover_cr(o)
    ev = events_in(feeds, sym, asof, h)
    mrr = float(cfg.get("min_reward_risk", 1.5))
    checks = [
        {"rule": "reward to risk", "ok": rr >= mrr, "note": f"{rr} vs floor {mrr}"},
        {"rule": "expected value after charges", "ok": bool(sim["exp_net_rs"] and sim["exp_net_rs"] > 0),
         "note": f"Rs {sim['exp_net_rs']} average over {cfg.get('paths', 10000)} replays" if qty else "no shares fit, so no rupee value"},
        {"rule": "turnover", "ok": to is not None and to >= min_cr,
         "note": f"Rs {to:.1f} Cr a day (20-day average), floor Rs {min_cr:g} Cr" if to is not None else "no volume data"},
        {"rule": "position cap", "ok": qty >= 1, "note": f"{qty} shares, Rs {qty * entry:,.0f}; set by {by}"},
        {"rule": "daily loss limit", "ok": 0 < risk <= float(cfg["daily_loss_limit"]),
         "note": f"loss at stop Rs {risk:,.0f} of the Rs {float(cfg['daily_loss_limit']):,.0f} daily limit"},
        {"rule": "no results or board meeting while held", "ok": not ev,
         "note": "; ".join(f"{e['d']} {e.get('p', '')}" for e in ev) or f"none in the next {h} sessions (NSE calendar)"},
    ]
    side = "rising" if up else "weak"
    return {"signal": key, "entry": entry, "stop": stop, "target": target, "rr": rr, "tick": tick, "vol_src": vol_src,
            "p_target": sim["p_target"], "p_stop": sim["p_stop"], "exp_net_rs": sim["exp_net_rs"], "charges_rs": ch,
            "qty": qty, "risk_rs": risk, "checks": checks, "event": ev[0] if ev else None,
            "basis": {"entry": "derived", "stop": "derived", "target": "derived", "rr": "derived", "tick": "derived",
                      "p_target": "estimate", "p_stop": "estimate", "exp_net_rs": "estimate", "charges_rs": "derived",
                      "qty": "derived", "risk_rs": "derived",
                      "test": f"Passed out of sample in {side} markets: {st.get('n')} cases, average {h}-day move "
                              f"{move * 100:+.1f}% beyond Nifty, {round((st.get(f'hit{h}') or 0) * 100)}% beat it"}}


def run(data: dict, nifty: dict, root) -> str:
    root = Path(root)
    cfg = _j(root / "config/trading.json", {})
    pf = _j(root / "config/portfolio.json", {})
    model = _j(root / "docs/tech-model.json", {})
    today = _j(root / "docs/tech-today.json", {})
    feeds = _j(root / "docs/nse-feeds.json", {})
    vol = (_j(root / "docs/risklab.json", {}) or {}).get("vol") or {}
    r = rates(cfg)
    up = regime_up(nifty)
    h = int(cfg.get("horizon_days", 21))
    asof = str(today.get("asof") or "")
    plans = {}
    for sym, td in (today.get("stocks") or {}).items():
        o = data.get(sym)
        sig = best_signal(td.get("new") or [], model.get("signals") or {}, up, h)
        if not o or not sig or len(o.get("c") or []) < 60:
            continue
        p = plan_one(sym, o, td, sig, cfg, r, vol, float(pf.get("stock_cap", 0.10)), float(pf.get("min_traded_cr", 1.0)),
                     feeds, asof, up)
        if p:
            plans[sym] = p
    out = {"asof": asof, "config_assumed": bool(cfg.get("_assumed", True)),
           "charges": {"product": cfg.get("product", "delivery"), **r,
                       "assumed": sorted(k for k, x in ((cfg.get("charges") or {}).get(cfg.get("product", "delivery")) or {}).items()
                                         if isinstance(x, dict) and x.get("_assumed"))},
           "plans": plans}
    (root / "docs/tradeplan.json").write_text(json.dumps(out, separators=(",", ":")), encoding="utf-8")
    ok = sum(all(c["ok"] for c in p["checks"]) for p in plans.values())
    return f"trade plan: {len(plans)} plans ({ok} pass every check), regime {'rising' if up else 'weak'}, vol from {'risklab' if vol else 'ATR'}"
