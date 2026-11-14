"""Quantitative modules on Dhan daily history (the same data the nightly technical back-test downloads).

  Monte Carlo    10,000 x 21-day paths by block-bootstrapping the stock's own daily returns (5-day
                 blocks keep short-term autocorrelation); percentile bands, P(up), P(target before stop).
                 Checked: how often the realised 21-day return fell inside the 90% band (should be ~90%).
  Markowitz      Nifty 50, 1-year covariance shrunk 30% toward its diagonal, mean returns shrunk 50% toward
                 the cross-section; long-only, max 15% per stock; minimum variance, maximum Sharpe, frontier.
                 Checked: walk-forward (fit 252 days, hold 63) against an equal-weight portfolio.
  Black-Scholes  price and Greeks (delta, gamma, theta per day, vega and rho per 1%), implied volatility,
                 spot x volatility surface; compared with Dhan's option chain.
  VaR            historical, parametric (normal) and Monte Carlo (bootstrap) VaR at 95% and 99%, 1 and 10 days,
                 with Expected Shortfall. Checked: Kupiec test of exceedances over the last 2 years.
  Pairs          Engle-Granger cointegration within an industry (OLS hedge ratio, ADF on the spread),
                 half-life, z-score; enter at |z| > 2, exit at |z| < 0.5, stop at |z| > 3.5 or 30 days;
                 0.1% cost per leg per side. Checked: walk-forward, formation 252 days, trading the next 126.
All money figures are per Rs 1,00,000 unless stated. Nothing here is a forecast of a single outcome.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

SEED = 7


# ------------------------------------------------------------------ helpers
def logret(c) -> np.ndarray:
    c = np.asarray(c, dtype=float)
    return np.diff(np.log(c))


def _norm_cdf(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def _norm_pdf(x):
    return math.exp(-0.5 * x * x) / math.sqrt(2 * math.pi)


def _z(p):
    """Inverse normal CDF (Acklam's approximation, |error| < 1.2e-9)."""
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02, 1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02, 6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00, -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00, 3.754408661907416e+00]
    if p < 0.02425:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    if p > 1 - 0.02425:
        return -_z(1 - p)
    q = p - 0.5
    r = q * q
    return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1)


# ------------------------------------------------------------------ Monte Carlo
def bootstrap_paths(r: np.ndarray, days: int = 21, n: int = 10000, block: int = 5, seed: int = SEED) -> np.ndarray:
    """Cumulative log-return paths, shape (n, days), from a block bootstrap of r."""
    rng = np.random.default_rng(seed)
    r = np.asarray(r, dtype=float)
    nb = math.ceil(days / block)
    starts = rng.integers(0, len(r) - block + 1, size=(n, nb))
    idx = (starts[:, :, None] + np.arange(block)[None, None, :]).reshape(n, nb * block)[:, :days]
    return np.cumsum(r[idx], axis=1)


def monte_carlo(close, atr: float | None = None, days: int = 21, n: int = 10000, lookback: int = 500, fan: bool = False) -> dict:
    c = np.asarray(close, dtype=float)
    r = logret(c[-lookback - 1:])
    if len(r) < 120:
        return {}
    paths = bootstrap_paths(r, days, n)
    last = c[-1]
    final = last * np.exp(paths[:, -1])
    pct = np.percentile(final, [5, 25, 50, 75, 95])
    out = {"last": round(float(last), 2), "days": days, "paths": n,
           "p5": round(float(pct[0]), 2), "p25": round(float(pct[1]), 2), "p50": round(float(pct[2]), 2),
           "p75": round(float(pct[3]), 2), "p95": round(float(pct[4]), 2),
           "p_up": round(float((final > last).mean()), 3), "exp_ret": round(float(final.mean() / last - 1), 4)}
    if atr:
        price = last * np.exp(paths)
        hit_t = (price >= last + 3 * atr)
        hit_s = (price <= last - 2 * atr)
        ft = np.where(hit_t.any(1), hit_t.argmax(1), days + 1)
        fs = np.where(hit_s.any(1), hit_s.argmax(1), days + 1)
        out["p_target_first"] = round(float((ft < fs).mean()), 3)
        out["p_stop_first"] = round(float((fs < ft).mean()), 3)
    if fan:
        prices = last * np.exp(paths)
        out["fan"] = [[round(float(x), 2) for x in np.percentile(prices[:, d], [5, 25, 50, 75, 95])] for d in range(days)]
        h, e = np.histogram(final / last - 1, bins=30)
        out["hist"] = {"counts": h.tolist(), "edges": [round(float(x), 4) for x in e]}
    return out


def mc_calibration(series: dict, days: int = 21, step: int = 21, test_days: int = 500, n: int = 2000) -> dict:
    """Share of realised 21-day outcomes that fell inside the bootstrap's 90% and 50% bands."""
    in90 = in50 = tot = 0
    for c in series.values():
        c = np.asarray(c, dtype=float)
        if len(c) < 500 + test_days + days:
            continue
        for t in range(len(c) - test_days - days, len(c) - days, step):
            r = logret(c[t - 500:t + 1])
            fin = c[t] * np.exp(bootstrap_paths(r, days, n, seed=t)[:, -1])
            lo, q1, q3, hi = np.percentile(fin, [5, 25, 75, 95])
            real = c[t + days]
            in90 += lo <= real <= hi
            in50 += q1 <= real <= q3
            tot += 1
    return {"cases": tot, "inside_90": round(in90 / tot, 3) if tot else None, "inside_50": round(in50 / tot, 3) if tot else None}


# ------------------------------------------------------------------ Markowitz
def _project(w, cap):
    """Project onto {w >= 0, sum w = 1, w <= cap} by bisection on the shift."""
    lo, hi = -1.0, 1.0
    for _ in range(80):
        mid = (lo + hi) / 2
        s = np.clip(w - mid, 0, cap).sum()
        lo, hi = (mid, hi) if s > 1 else (lo, mid)
    return np.clip(w - (lo + hi) / 2, 0, cap)


def _solve(mu, cov, cap, mode, target=None, rf=0.0, iters=3000):
    n = len(mu)
    w = np.full(n, 1 / n)
    lr = 0.5 / (np.linalg.norm(cov, 2) + 1e-12)
    for _ in range(iters):
        if mode == "minvar":
            g = 2 * cov @ w
        elif mode == "target":
            g = 2 * cov @ w + 200 * (w @ mu - target) * mu
        else:                                                 # max Sharpe: ascend (mu-rf)/sigma
            s = math.sqrt(max(w @ cov @ w, 1e-12))
            ex = w @ mu - rf
            g = -((mu - rf) / s - ex * (cov @ w) / s ** 3)
        w = _project(w - lr * g * (1 if mode != "maxsharpe" else 50), cap)
    return w


def markowitz(rets: np.ndarray, names: list, rf: float, cap: float = 0.15) -> dict:
    """rets: (days, assets) daily log returns. Annualised with 252 days."""
    mu = rets.mean(0) * 252
    mu = 0.5 * mu + 0.5 * mu.mean()
    cov = np.cov(rets.T) * 252
    cov = 0.7 * cov + 0.3 * np.diag(np.diag(cov))
    stats = lambda w: (float(w @ mu), float(math.sqrt(w @ cov @ w)))
    wmin = _solve(mu, cov, cap, "minvar")
    wsh = _solve(mu, cov, cap, "maxsharpe", rf=rf)
    pts = []
    rmin, rmax = stats(wmin)[0], min(float(np.sort(mu)[-int(1 / cap) - 1:].mean()), float(mu.max()))
    for tgt in np.linspace(rmin, rmax, 12):
        w = _solve(mu, cov, cap, "target", target=float(tgt), iters=1500)
        r_, v_ = stats(w)
        pts.append([round(v_, 4), round(r_, 4)])
    pack = lambda w: {"ret": round(stats(w)[0], 4), "vol": round(stats(w)[1], 4),
                      "sharpe": round((stats(w)[0] - rf) / stats(w)[1], 2) if stats(w)[1] else None,
                      "weights": {names[i]: round(float(w[i]), 4) for i in np.argsort(-w) if w[i] >= 0.005}}
    assets = [[round(math.sqrt(cov[i, i]), 4), round(float(mu[i]), 4), names[i]] for i in range(len(names))]
    return {"min_variance": pack(wmin), "max_sharpe": pack(wsh), "frontier": pts, "assets": assets, "rf": rf, "cap": cap}


def markowitz_walkforward(prices: np.ndarray, names: list, rf: float, fit: int = 252, hold: int = 63) -> dict:
    """Out-of-sample: refit every `hold` days on the previous `fit` days; compare with equal weight."""
    r = np.diff(np.log(prices), axis=0)
    out = {k: [] for k in ("min_variance", "max_sharpe", "equal")}
    for t in range(fit, len(r) - hold + 1, hold):
        m = markowitz(r[t - fit:t], names, rf)
        ws = {k: np.array([m[k]["weights"].get(n, 0.0) for n in names]) for k in ("min_variance", "max_sharpe")}
        ws["equal"] = np.full(len(names), 1 / len(names))
        seg = np.exp(r[t:t + hold]) - 1                      # simple daily returns, weights drift-free
        for k, w in ws.items():
            out[k] += list(seg @ (w / w.sum()))
    res = {}
    for k, d in out.items():
        d = np.array(d)
        if len(d) < 40:
            continue
        eq = np.cumprod(1 + d)
        res[k] = {"days": len(d), "ann_ret": round(float(eq[-1] ** (252 / len(d)) - 1), 4),
                  "ann_vol": round(float(d.std() * math.sqrt(252)), 4),
                  "sharpe": round(float((d.mean() * 252 - rf) / (d.std() * math.sqrt(252))), 2) if d.std() else None,
                  "max_dd": round(float((eq / np.maximum.accumulate(eq) - 1).min()), 4)}
    return res


# ------------------------------------------------------------------ Black-Scholes
def black_scholes(S, K, T, r, sigma, kind="call", q=0.0) -> dict:
    """T in years, r and sigma as decimals. theta per calendar day; vega and rho per 1 percentage point."""
    if T <= 0 or sigma <= 0:
        intrinsic = max(S - K, 0) if kind == "call" else max(K - S, 0)
        return {"price": intrinsic, "delta": (1.0 if S > K else 0.0) if kind == "call" else (-1.0 if S < K else 0.0),
                "gamma": 0.0, "theta": 0.0, "vega": 0.0, "rho": 0.0}
    sq = sigma * math.sqrt(T)
    d1 = (math.log(S / K) + (r - q + 0.5 * sigma * sigma) * T) / sq
    d2 = d1 - sq
    df, dq = math.exp(-r * T), math.exp(-q * T)
    if kind == "call":
        price = S * dq * _norm_cdf(d1) - K * df * _norm_cdf(d2)
        delta = dq * _norm_cdf(d1)
        theta = (-S * dq * _norm_pdf(d1) * sigma / (2 * math.sqrt(T)) - r * K * df * _norm_cdf(d2) + q * S * dq * _norm_cdf(d1)) / 365
        rho = K * T * df * _norm_cdf(d2) / 100
    else:
        price = K * df * _norm_cdf(-d2) - S * dq * _norm_cdf(-d1)
        delta = -dq * _norm_cdf(-d1)
        theta = (-S * dq * _norm_pdf(d1) * sigma / (2 * math.sqrt(T)) + r * K * df * _norm_cdf(-d2) - q * S * dq * _norm_cdf(-d1)) / 365
        rho = -K * T * df * _norm_cdf(-d2) / 100
    return {"price": price, "delta": delta, "gamma": dq * _norm_pdf(d1) / (S * sq),
            "theta": theta, "vega": S * dq * _norm_pdf(d1) * math.sqrt(T) / 100, "rho": rho}


def implied_vol(price, S, K, T, r, kind="call") -> float | None:
    lo, hi = 0.005, 3.0
    if price <= max(S - K, 0) * (kind == "call") + max(K - S, 0) * (kind != "call"):
        return None
    for _ in range(100):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if black_scholes(S, K, T, r, mid, kind)["price"] < price else (lo, mid)
    return (lo + hi) / 2


def bs_surface(S, K, T, r, sigma, kind="call") -> dict:
    spots = [round(S * (0.9 + 0.025 * i), 2) for i in range(9)]
    vols = [round(max(0.05, sigma * m), 4) for m in (0.6, 0.8, 1.0, 1.2, 1.4)]
    return {"spots": spots, "vols": vols, "price": [[round(black_scholes(s, K, T, r, v, kind)["price"], 2) for s in spots] for v in vols]}


# ------------------------------------------------------------------ VaR
def var_report(r: np.ndarray, value: float = 100000.0, n: int = 10000) -> dict:
    r = np.asarray(r, dtype=float)[-500:]
    simple = np.exp(r) - 1
    mu, sd = simple.mean(), simple.std()
    out = {"value": value, "days_used": len(r)}
    paths10 = np.exp(bootstrap_paths(r, 10, n)[:, -1]) - 1
    one = np.exp(bootstrap_paths(r, 1, n, block=1)[:, -1]) - 1
    for cl in (0.95, 0.99):
        k = str(int(cl * 100))
        q = np.quantile(simple, 1 - cl)
        es = simple[simple <= q].mean()
        zc = _z(cl)
        out[k] = {"hist_1d": round(-q * value), "es_1d": round(-es * value),
                  "param_1d": round(-(mu - zc * sd) * value), "param_10d": round(-(10 * mu - zc * sd * math.sqrt(10)) * value),
                  "mc_1d": round(-np.quantile(one, 1 - cl) * value), "mc_10d": round(-np.quantile(paths10, 1 - cl) * value),
                  "mc_es_10d": round(-paths10[paths10 <= np.quantile(paths10, 1 - cl)].mean() * value)}
    h, e = np.histogram(paths10, bins=30)
    out["loss_hist_10d"] = {"counts": h.tolist(), "edges": [round(float(x), 4) for x in e]}
    return out


def kupiec(r: np.ndarray, cl: float = 0.99, window: int = 250, test: int = 500) -> dict:
    """Rolling historical VaR; count days the next loss exceeded it; Kupiec proportion-of-failures test."""
    simple = np.exp(np.asarray(r, dtype=float)) - 1
    x = n = 0
    for t in range(max(window, len(simple) - test), len(simple)):
        v = np.quantile(simple[t - window:t], 1 - cl)
        x += simple[t] < v
        n += 1
    if not n:
        return {}
    p, ph = 1 - cl, x / n
    ll = lambda pp: (n - x) * math.log(1 - pp) + (x * math.log(pp) if x else 0)
    lr = -2 * (ll(p) - (ll(ph) if 0 < ph < 1 else 0))
    pval = math.erfc(math.sqrt(max(lr, 0) / 2))             # chi-square with 1 degree of freedom
    return {"days": n, "exceed": int(x), "expected": round(n * p, 1), "rate": round(ph, 4), "p_value": round(pval, 3),
            "ok": bool(pval > 0.05)}


# ------------------------------------------------------------------ Pairs
def ols(y, x):
    X = np.column_stack([np.ones(len(x)), x])
    b = np.linalg.lstsq(X, y, rcond=None)[0]
    return b[0], b[1], y - X @ b


def adf_t(e) -> float:
    """ADF t-statistic with one lag and a constant, on the spread."""
    e = np.asarray(e, dtype=float)
    de = np.diff(e)
    y, xl, dl = de[1:], e[1:-1], de[:-1]
    X = np.column_stack([np.ones(len(y)), xl, dl])
    b, res, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ b
    s2 = resid @ resid / (len(y) - 3)
    cov = s2 * np.linalg.inv(X.T @ X)
    return float(b[1] / math.sqrt(cov[1, 1]))


def half_life(e) -> float | None:
    e = np.asarray(e, dtype=float)
    b = np.polyfit(e[:-1], np.diff(e), 1)[0]
    return -math.log(2) / b if b < 0 else None


EG_CRIT = -3.34                                               # Engle-Granger 5%, two series, constant


def pair_trades(ly, lx, beta, mu, sd, cost=0.001, enter=2.0, exit_=0.5, stop=3.5, max_hold=30) -> list:
    """Trade a fixed hedge ratio on log prices; returns per-trade returns on gross capital (net of costs)."""
    s = ly - beta * lx
    z = (s - mu) / sd
    trades, pos, t0 = [], 0, 0
    for t in range(1, len(z)):
        if pos == 0 and abs(z[t]) > enter and abs(z[t]) < stop:
            pos, t0 = (-1 if z[t] > 0 else 1), t
        elif pos and (abs(z[t]) < exit_ or abs(z[t]) > stop or t - t0 >= max_hold or t == len(z) - 1):
            ry, rx = math.exp(ly[t] - ly[t0]) - 1, math.exp(lx[t] - lx[t0]) - 1
            gross = (ry - beta * rx) / (1 + abs(beta))
            trades.append(pos * gross - 4 * cost / 2)
            pos = 0
    return trades


def pairs_scan(groups: dict, form: int = 252, trade: int = 126, steps: int = 4) -> dict:
    """groups: {industry: {sym: closes (aligned, same length)}}. Walk-forward over the last `steps` x `trade` days."""
    oos, current = [], []
    for ind, members in groups.items():
        syms = list(members)
        for i in range(len(syms)):
            for j in range(i + 1, len(syms)):
                a, b = np.log(np.asarray(members[syms[i]], float)), np.log(np.asarray(members[syms[j]], float))
                L = len(a)
                if L < form + trade * steps + 1:
                    continue
                for k in range(steps, 0, -1):                     # walk-forward windows ending k*trade days ago
                    f0, f1 = L - k * trade - form, L - k * trade
                    alpha, beta, e = ols(a[f0:f1], b[f0:f1])
                    if beta <= 0 or adf_t(e) > EG_CRIT:
                        continue
                    hl = half_life(e)
                    if not hl or not 2 <= hl <= 60:
                        continue
                    oos += pair_trades(a[f1:f1 + trade] - alpha, b[f1:f1 + trade], beta, 0.0, e.std())
                alpha, beta, e = ols(a[-form:], b[-form:])        # today's formation for live signals
                if beta > 0 and adf_t(e) <= EG_CRIT:
                    hl = half_life(e)
                    if hl and 2 <= hl <= 60:
                        z = float(e[-1] / e.std())
                        current.append({"y": syms[i], "x": syms[j], "industry": ind, "beta": round(float(beta), 3),
                                        "adf_t": round(adf_t(e), 2), "half_life": round(hl, 1), "z": round(z, 2),
                                        "signal": ("short " + syms[i] + " / long " + syms[j]) if z > 2 else
                                                  ("long " + syms[i] + " / short " + syms[j]) if z < -2 else "no trade",
                                        "spread_z": [round(float(v / e.std()), 2) for v in e[-120:]]})
    o = np.array(oos) if oos else np.array([])
    strat = {"trades": len(o)}
    if len(o) >= 20:
        eq = np.cumprod(1 + o)
        strat.update({"avg": round(float(o.mean()), 4), "hit": round(float((o > 0).mean()), 3),
                      "t": round(float(o.mean() / (o.std() / math.sqrt(len(o)))), 2), "total": round(float(eq[-1] - 1), 4),
                      "max_dd": round(float((eq / np.maximum.accumulate(eq) - 1).min()), 4)})
    strat["tested"] = bool(strat.get("trades", 0) >= 30 and strat.get("avg", -1) > 0 and strat.get("t", 0) >= 2)
    current.sort(key=lambda p: -abs(p["z"]))
    return {"strategy_oos": strat, "current": current[:15], "rule": "enter |z|>2, exit |z|<0.5, stop |z|>3.5 or 30 days; 0.1% per leg per side"}


# ------------------------------------------------------------------ nightly run
def run(data: dict, nifty: dict, root, rf: float, n50: list, board_rows: list, opts: dict | None = None) -> str:
    root = Path(root)
    out = {"asof": nifty["d"][-1], "rf": rf}
    closes = {s: o["c"] for s, o in data.items() if len(o.get("c", [])) >= 300}
    atr = {}
    for s, o in data.items():
        h, l, c = (np.asarray(o[k], float) for k in ("h", "l", "c"))
        if len(c) > 20:
            tr = np.maximum(h[1:] - l[1:], np.maximum(abs(h[1:] - c[:-1]), abs(l[1:] - c[:-1])))
            atr[s] = float(tr[-14:].mean())
    out["mc"] = {s: monte_carlo(c, atr.get(s), fan=s in n50) for s, c in closes.items()}
    out["mc"] = {s: v for s, v in out["mc"].items() if v}
    out["mc_calibration"] = mc_calibration({s: closes[s] for s in n50 if s in closes})
    out["var"] = {s: var_report(logret(c)) for s, c in closes.items() if s in n50}
    if len(nifty.get("c", [])) >= 300:                     # the index itself, for the desk's NIFTY view
        m = monte_carlo(nifty["c"], None, fan=True)
        if m:
            out["mc"]["NIFTY"] = m
        out["var"]["NIFTY"] = var_report(logret(nifty["c"]))
    vk = [kupiec(logret(closes[s])) for s in n50 if s in closes]
    vk = [x for x in vk if x]
    out["var_backtest"] = {"stocks": len(vk), "passed": sum(x["ok"] for x in vk),
                           "avg_rate": round(float(np.mean([x["rate"] for x in vk])), 4) if vk else None, "expected": 0.01}
    names = [s for s in n50 if s in closes and len(closes[s]) >= 600]
    L = min(len(closes[s]) for s in names) if names else 0
    if len(names) >= 10 and L >= 600:
        P = np.column_stack([np.asarray(closes[s][-L:], float) for s in names])
        out["portfolio"] = markowitz(np.diff(np.log(P[-253:]), axis=0), names, rf)
        out["portfolio"]["walk_forward"] = markowitz_walkforward(P[-(252 + 63 * 8 + 1):], names, rf)
        w = out["portfolio"]["min_variance"]["weights"]
        pr = np.diff(np.log(P[-501:]), axis=0) @ np.array([w.get(s, 0) for s in names])
        out["portfolio"]["var"] = var_report(pr)
    ind = {}
    for r in board_rows:
        if r["s"] in closes and r.get("ind"):
            ind.setdefault(r["ind"], []).append(r)
    groups = {}
    for k, rows in ind.items():
        rows = sorted(rows, key=lambda r: -(r.get("turn_cr") or 0))[:8]
        Lg = min(len(closes[r["s"]]) for r in rows) if rows else 0
        if len(rows) >= 2 and Lg >= 800:
            groups[k] = {r["s"]: closes[r["s"]][-Lg:] for r in rows}
    out["pairs"] = pairs_scan(groups)
    out["bs"] = {}
    for u, o in (opts or {}).items():
        if u not in ("NIFTY", "BANKNIFTY") and u not in n50[:10]:
            continue
        if not o.get("atm") or not o.get("days") or not o.get("iv_call"):
            continue
        S, K, T = o["spot"], o["atm"], max(o["days"], 0.5) / 365
        sig = (o["iv_call"] + (o.get("iv_put") or o["iv_call"])) / 200
        c_, p_ = black_scholes(S, K, T, rf, sig, "call"), black_scholes(S, K, T, rf, sig, "put")
        out["bs"][u] = {"S": S, "K": K, "days": o["days"], "iv": round(sig, 4), "expiry": o.get("expiry"),
                        "call": {k: round(v, 4) for k, v in c_.items()}, "put": {k: round(v, 4) for k, v in p_.items()},
                        "market_straddle": o.get("straddle"), "model_straddle": round(c_["price"] + p_["price"], 2),
                        "surface": bs_surface(S, K, T, rf, sig)}
    (root / "docs/quant.json").write_text(json.dumps(out, separators=(",", ":")), encoding="utf-8")
    return (f"quant: MC {len(out['mc'])} stocks (90% band held {out['mc_calibration'].get('inside_90')}), "
            f"VaR {len(out['var'])} (Kupiec ok {out['var_backtest']['passed']}/{out['var_backtest']['stocks']}), "
            f"portfolio {'yes' if 'portfolio' in out else 'no'}, pairs OOS {out['pairs']['strategy_oos']}")
