"""Risk lab: the statistical proof layer of the Evidence Desk. Writes docs/risklab.json.

Nightly (fast):
  vol       GJR-GARCH(1,1) with skewed-t errors on percent returns, last 1,000 sessions; 1- and 5-day forecasts.
            Falls back to EWMA (lambda 0.94) when a fit fails or arch is missing, and says so in "model".
  var       1-day 95% / 99% VaR from the GARCH forecast (Nifty 50 stocks), back-tested on the last 250 sessions
            with parameters fitted only on earlier data (arch last_obs), Kupiec proportion-of-failures test.
  conformal 21-session forward-return interval at 90% (MAPIE split conformal, chronological split, no shuffling),
            coverage measured on the held-out last part next to the target.
Saturdays or with --full (slower; on other days the last full results are carried over):
  signals   stationary-bootstrap interval on each signal's mean out-of-sample excess return, and a data-snooping
            test across all signals together (Hansen SPA p-value for the family, Romano-Wolf StepM for which survive).
  track     bootstrap interval on each live score band's mean 21-day excess return (needs 30+ graded picks).
  pairs     Engle-Granger re-test (arch) of the pairs quant.pairs_scan considers. Counts only; never a trade.

Every arch / mapie / sklearn import is guarded: a missing library leaves a note and the module returns normally.
Prices are the Dhan closes passed in; nothing here fetches or trades.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import sys
import time
import warnings
from pathlib import Path

import numpy as np

LOOKBACK = 1000          # sessions of returns for GARCH
VAR_TEST = 250           # out-of-sample sessions in the VaR back-test
HORIZON = 21             # conformal forward window, sessions
CONF = 0.90
REPS = 1000              # bootstrap repetitions
MIN_DAYS = 30            # minimum out-of-sample days for a signal test / graded picks for a track interval
BAD_MOVE = 0.40          # a one-day move above 40% is a split or bad tick, not a market move (same rule as tech_model)
FULL_NOTE = "Last full run: "
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))


def _lib(name: str):
    """Import a module or return (None, reason)."""
    try:
        import importlib
        return importlib.import_module(name), None
    except Exception as e:          # ImportError, or a broken install
        return None, f"{name} unavailable ({type(e).__name__}: {str(e)[:80]})"


def _clean(c) -> np.ndarray:
    """Closes after the last one-day move above 40% (a split or bad tick would wreck any volatility fit)."""
    c = np.asarray(c, float)
    c = c[np.isfinite(c) & (c > 0)]
    if len(c) < 2:
        return c
    bad = np.nonzero(np.abs(c[1:] / c[:-1] - 1) > BAD_MOVE)[0]
    return c[bad[-1] + 1:] if len(bad) else c


def _pct(c) -> np.ndarray:
    return 100 * np.diff(c) / c[:-1]


def _ewma(r: np.ndarray, lam: float = 0.94) -> float:
    """Next-day variance (percent^2), RiskMetrics EWMA seeded with the first 30 days' variance."""
    s2 = float(np.var(r[:30])) if len(r) >= 30 else float(np.var(r))
    for x in r:
        s2 = lam * s2 + (1 - lam) * x * x
    return s2


def pof(x: int, n: int, p: float) -> dict:
    """Kupiec proportion-of-failures test, the same statistic as quant.kupiec, for an external VaR series."""
    if not n:
        return {}
    ph = x / n
    ll = lambda pp: (n - x) * math.log(1 - pp) + (x * math.log(pp) if x else 0)
    lr = -2 * (ll(p) - (ll(ph) if 0 < ph < 1 else 0))
    pval = math.erfc(math.sqrt(max(lr, 0) / 2))
    return {"days": n, "exceed": int(x), "expected": round(n * p, 1), "p_value": round(pval, 3), "ok": bool(pval > 0.05)}


# ------------------------------------------------------------------ 1. volatility
def fit_vol(r: np.ndarray, arch_model=None) -> tuple[dict, object]:
    """r: percent returns. Returns, as fractions of price, ({d1, d5, ann, persistence, model}, fitted result or None)."""
    reason = "arch missing"
    if arch_model is not None:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                res = arch_model(r, mean="Constant", vol="GARCH", p=1, o=1, q=1, dist="skewt").fit(disp="off", show_warning=False)
            p = res.params
            pers = float(p["alpha[1]"] + p["gamma[1]"] / 2 + p["beta[1]"])
            if res.convergence_flag != 0:
                raise ValueError("did not converge")
            if not (np.isfinite(pers) and 0 <= pers < 1):
                raise ValueError(f"persistence {pers:.3f} outside [0, 1)")
            v = res.forecast(horizon=5, reindex=False).variance.values[-1]
            d1 = math.sqrt(v[0]) / 100                 # fit in percent, report as a fraction of price
            return ({"d1": round(d1, 5), "d5": round(math.sqrt(float(v.sum())) / 100, 5), "ann": round(d1 * math.sqrt(252), 4),
                     "persistence": round(pers, 4), "model": "GJR-GARCH(1,1) skew-t"}, res)
        except Exception as e:
            reason = f"GARCH failed: {str(e)[:60]}"
    d1 = math.sqrt(_ewma(r)) / 100
    return ({"d1": round(d1, 5), "d5": round(d1 * math.sqrt(5), 5), "ann": round(d1 * math.sqrt(252), 4),
             "persistence": None, "model": f"EWMA 0.94 ({reason})"}, None)


# ------------------------------------------------------------------ 2. VaR
def garch_var(r: np.ndarray, full_res, arch_model) -> dict:
    """Live 1-day VaR (loss as a fraction of price) from the full-sample fit; back-test on the last VAR_TEST sessions with
    parameters fitted on earlier data only, each forecast made from data up to the day before."""
    q_levels = [0.01, 0.05]
    am_full = full_res.model
    shape = full_res.params.values[-2:]
    f = full_res.forecast(horizon=1, reindex=False)
    mu, sd = float(f.mean.values[-1, 0]), math.sqrt(float(f.variance.values[-1, 0]))
    q99, q95 = am_full.distribution.ppf(q_levels, shape)
    split = len(r) - VAR_TEST
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        am = arch_model(r, mean="Constant", vol="GARCH", p=1, o=1, q=1, dist="skewt")
        res = am.fit(disp="off", show_warning=False, last_obs=split)
        fb = res.forecast(start=split - 1, horizon=1, reindex=False)
    m = fb.mean.values[:-1, 0]                       # origins split-1 .. n-2 -> forecasts for days split .. n-1
    s = np.sqrt(fb.variance.values[:-1, 0])
    b99, b95 = am.distribution.ppf(q_levels, res.params.values[-2:])
    real = r[split:]
    k99, k95 = pof(int((real < m + s * b99).sum()), len(real), 0.01), pof(int((real < m + s * b95).sum()), len(real), 0.05)
    return {"garch95": round(-(mu + sd * q95) / 100, 5), "garch99": round(-(mu + sd * q99) / 100, 5),
            "kupiec_ok": bool(k95.get("ok") and k99.get("ok"))}


# ------------------------------------------------------------------ 3. conformal
def _features(lc: np.ndarray, i: int):
    """Volatility-scaled momentum features at index i of log closes, and the 21-day vol used for scaling."""
    dr = np.diff(lc[i - 21:i + 1])
    v = float(dr.std())
    if v <= 0:
        return None, None
    return [(lc[i] - lc[i - 21]) / (v * math.sqrt(21)), (lc[i] - lc[i - 63]) / (v * math.sqrt(63)),
            (lc[i] - lc[i - 5]) / (v * math.sqrt(5))], v


def conformal(closes: dict, cal: list, SCR, LinearRegression, step: int = 5) -> dict:
    """Pooled split-conformal interval on the 21-session forward log return scaled by each stock's 21-day vol.
    Chronological split on the calendar: train 60%, conformalize 20%, test 20%, with a 21-session gap before each
    boundary so no training target overlaps a later period. Interval returned as simple-return fractions."""
    pos = {d: k for k, d in enumerate(cal)}
    X, y, t, today = [], [], [], {}
    for sym, (d, c) in closes.items():
        lc = np.log(np.asarray(c, float))
        n = len(lc)
        if n < 64:
            continue
        jump = np.abs(np.diff(lc)) > math.log(1 + BAD_MOVE)
        f, v = _features(lc, n - 1)
        if f is not None and not jump[-63:].any():
            today[sym] = (f, v)
        for i in range(max(63, n - LOOKBACK), n - HORIZON, step):
            if d[i] not in pos or jump[i - 63:i + HORIZON].any():
                continue
            f, v = _features(lc, i)
            if f is None:
                continue
            X.append(f)
            y.append((lc[i + HORIZON] - lc[i]) / (v * math.sqrt(HORIZON)))
            t.append(pos[d[i]])
    out = {"coverage_target": CONF, "coverage_measured": None, "by_sym": {}}
    if len(X) < 200:
        return out
    X, y, t = np.array(X), np.array(y), np.array(t)
    t0, t1 = t.min(), t.max()
    b1, b2 = t0 + 0.6 * (t1 - t0), t0 + 0.8 * (t1 - t0)
    tr, ca, te = t < b1 - HORIZON, (t >= b1) & (t < b2 - HORIZON), t >= b2
    m = SCR(LinearRegression(), confidence_level=CONF, prefit=False).fit(X[tr], y[tr]).conformalize(X[ca], y[ca])
    _, iv = m.predict_interval(X[te])
    out["coverage_measured"] = round(float(((y[te] >= iv[:, 0, 0]) & (y[te] <= iv[:, 1, 0])).mean()), 4)
    if today:
        syms = sorted(today)
        _, iv = m.predict_interval(np.array([today[s][0] for s in syms]))
        for k, s in enumerate(syms):
            sc = today[s][1] * math.sqrt(HORIZON)
            out["by_sym"][s] = [round(math.expm1(float(iv[k, 0, 0]) * sc), 4), round(math.expm1(float(iv[k, 1, 0]) * sc), 4)]
    return out


# ------------------------------------------------------------------ 4. signals
def _daily(series: dict) -> list:
    """{date: [excess returns of that day's cases]} -> [(date, mean)] in date order."""
    return [(d, float(np.mean(v))) for d, v in sorted(series.items()) if v]


def signal_tests(series: dict, keys: list, B) -> dict:
    """series: {key: {date: [10-day excess returns of cases first flagged that day, out-of-sample]}}.
    CI: stationary bootstrap (block length from optimal_block_length) on the mean daily excess return.
    Joint test: losses = -excess on the common calendar (0 on days without a case), benchmark = 0.
    spa_p is Hansen's SPA consistent p-value for the whole family (same for every signal); survives is True only
    for signals StepM puts in its superior set at 5%."""
    import pandas as pd
    out, cols = {}, {}
    for k in keys:
        s = _daily(series.get(k) or {})
        row = {"ci_lo": None, "ci_hi": None, "spa_p": None, "survives": False}
        if len(s) >= MIN_DAYS:
            x = np.array([v for _, v in s])
            bl = max(1.0, float(B.optimal_block_length(x)["stationary"].iloc[0]))
            bs = B.StationaryBootstrap(bl, x, seed=0)
            try:
                ci = bs.conf_int(lambda a: np.array([a.mean()]), reps=REPS, method="bca")
            except Exception:
                ci = bs.conf_int(lambda a: np.array([a.mean()]), reps=REPS, method="percentile")
            row["ci_lo"], row["ci_hi"] = round(float(ci[0, 0]), 5), round(float(ci[1, 0]), 5)
            cols[k] = dict(s)
        out[k] = row
    if len(cols) >= 1:
        dates = sorted(set().union(*[set(v) for v in cols.values()]))
        M = pd.DataFrame({k: [v.get(d, 0.0) for d in dates] for k, v in cols.items()}, index=dates)
        bl = max(1, int(round(float(B.optimal_block_length(M.values)["stationary"].mean()))))
        bench = np.zeros(len(M))
        spa = B.SPA(bench, -M, block_size=bl, reps=REPS, bootstrap="stationary", seed=0)
        spa.compute()
        p = round(float(spa.pvalues["consistent"]), 4)
        sm = B.StepM(bench, -M, size=0.05, block_size=bl, reps=REPS, bootstrap="stationary", seed=0)
        sm.compute()
        sup = set(sm.superior_models or [])
        for k in cols:
            out[k]["spa_p"] = p
            out[k]["survives"] = bool(k in sup and p < 0.05)
    return out


# ------------------------------------------------------------------ 5. track record
def track_bands(log: dict, B) -> dict:
    out = {}
    for kind in sorted({p["kind"] for p in log.get("picks", [])}):
        ps = sorted((p for p in log["picks"] if p["kind"] == kind and "x21" in p), key=lambda p: p["d"])
        xs = np.array([p["x21"] for p in ps], float)
        row = {"mean": round(float(xs.mean()), 5) if len(xs) else None, "ci_lo": None, "ci_hi": None, "n": len(xs)}
        if len(xs) >= MIN_DAYS and B is not None:
            bl = max(1.0, float(B.optimal_block_length(xs)["stationary"].iloc[0]))
            ci = B.StationaryBootstrap(bl, xs, seed=0).conf_int(lambda a: np.array([a.mean()]), reps=REPS, method="percentile")
            row["ci_lo"], row["ci_hi"] = round(float(ci[0, 0]), 5), round(float(ci[1, 0]), 5)
        out[kind] = row
    return out


# ------------------------------------------------------------------ 6. pairs
def _groups(closes: dict, board_rows: list) -> dict:
    """The same industry groups quant.run hands to quant.pairs_scan."""
    ind = {}
    for r in board_rows:
        if r.get("s") in closes and r.get("ind"):
            ind.setdefault(r["ind"], []).append(r)
    groups = {}
    for k, rows in ind.items():
        rows = sorted(rows, key=lambda r: -(r.get("turn_cr") or 0))[:8]
        Lg = min(len(closes[r["s"]]) for r in rows) if rows else 0
        if len(rows) >= 2 and Lg >= 800:
            groups[k] = {r["s"]: closes[r["s"]][-Lg:] for r in rows}
    return groups


def pairs_retest(groups: dict, engle_granger, form: int = 252) -> dict:
    tested = coint = 0
    for members in groups.values():
        syms = list(members)
        for i in range(len(syms)):
            for j in range(i + 1, len(syms)):
                a = np.log(np.asarray(members[syms[i]], float)[-form:])
                b = np.log(np.asarray(members[syms[j]], float)[-form:])
                try:
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        pv = float(engle_granger(a, b, trend="c").pvalue)
                except Exception:
                    continue
                tested += 1
                coint += pv < 0.05
    chance = 0.05 * tested
    tail = sum(math.comb(tested, k) * 0.05 ** k * 0.95 ** (tested - k) for k in range(coint, tested + 1)) if tested else 1.0
    verdict = (f"{coint} of {tested} same-industry pairs test as cointegrated over the last year at 5%; "
               f"chance alone gives about {chance:.0f}, so this is "
               + ("more than chance." if tested and tail < 0.05 else "no more than chance."))
    return {"tested": tested, "cointegrated": int(coint), "verdict": verdict}


# ------------------------------------------------------------------ nightly run
def run(data: dict, nifty: dict, root, series: dict | None = None, full: bool | None = None,
        n50: list | None = None, board_rows: list | None = None) -> str:
    """data: {sym: {d, o, h, l, c, v}} Dhan daily bars; nifty: {d, c}; series: per-signal out-of-sample excess returns
    from tech_model.backtest(series=...). Never raises for a missing library."""
    root = Path(root)
    if full is None:
        full = "--full" in sys.argv or dt.datetime.now(IST).weekday() == 5
    notes, tm = [], {}
    out = {"asof": nifty["d"][-1], "vol": {}, "var": {},
           "conformal": {"coverage_target": CONF, "coverage_measured": None, "by_sym": {}},
           "signals": {}, "track": {}, "pairs": {}, "notes": notes}
    arch, why = _lib("arch")
    if why:
        notes.append(why)
    arch_model = arch.arch_model if arch else None

    t = time.time()
    rets = {}
    for s, o in data.items():
        c = _clean(o.get("c") or [])
        if len(c) >= 301:
            rets[s] = _pct(c[-(LOOKBACK + 1):])
    fits = {}
    for s, r in rets.items():
        out["vol"][s], fits[s] = fit_vol(r, arch_model)
    fb = sum(v["model"].startswith("EWMA") for v in out["vol"].values())
    if fb:
        notes.append(f"vol: {fb} of {len(out['vol'])} stocks use the EWMA fallback (see each 'model').")
    tm["vol"] = time.time() - t

    t = time.time()
    if n50 is None:
        try:
            import refresh as R
            n50 = list(R.read_nset((root / "docs/nse-terminal.html").read_text(encoding="utf-8")).get("stocks", {}))
        except Exception as e:
            n50 = []
            notes.append(f"var: Nifty 50 list unavailable ({str(e)[:60]})")
    if arch_model is not None:
        for s in n50:
            if fits.get(s) is not None and len(rets[s]) >= VAR_TEST + 250:
                try:
                    out["var"][s] = garch_var(rets[s], fits[s], arch_model)
                except Exception as e:
                    notes.append(f"var {s}: {str(e)[:60]}")
        ok = sum(v["kupiec_ok"] for v in out["var"].values())
        notes.append(f"var: Kupiec passed at both 95% and 99% for {ok} of {len(out['var'])} Nifty 50 stocks "
                     f"(last {VAR_TEST} sessions, parameters fitted on earlier data only).")
    else:
        notes.append("var: skipped, needs arch.")
    tm["var"] = time.time() - t

    t = time.time()
    mapie, w1 = _lib("mapie.regression")
    sk, w2 = _lib("sklearn.linear_model")
    if mapie and sk:
        try:
            cl = {s: (list(o["d"]), o["c"]) for s, o in data.items() if len(o.get("c") or []) > 63 + HORIZON}
            out["conformal"] = conformal(cl, list(nifty["d"]), mapie.SplitConformalRegressor, sk.LinearRegression)
        except Exception as e:
            notes.append(f"conformal failed: {str(e)[:120]}")
    else:
        notes.append("conformal: skipped, " + "; ".join(x for x in (w1, w2) if x))
    tm["conformal"] = time.time() - t

    prev = {}
    try:
        prev = json.loads((root / "docs/risklab.json").read_text(encoding="utf-8"))
    except Exception:
        pass
    if full:
        B, wb = _lib("arch.bootstrap")
        t = time.time()
        try:
            keys = list(json.loads((root / "docs/tech-model.json").read_text(encoding="utf-8")).get("signals", {}))
        except Exception:
            keys = sorted(series or {})
        if B is None:
            notes.append("signals / track: skipped, " + wb)
        elif not series:
            notes.append("signals: no out-of-sample series passed in.")
        else:
            try:
                out["signals"] = signal_tests(series, keys, B)
            except Exception as e:
                notes.append(f"signals failed: {str(e)[:120]}")
        tm["signals"] = time.time() - t
        t = time.time()
        try:
            log = json.loads((root / "docs/track-record.json").read_text(encoding="utf-8"))
            out["track"] = track_bands(log, B)
        except FileNotFoundError:
            notes.append("track: no docs/track-record.json yet.")
        except Exception as e:
            notes.append(f"track failed: {str(e)[:120]}")
        tm["track"] = time.time() - t
        t = time.time()
        if arch is not None:
            try:
                from arch.unitroot.cointegration import engle_granger
                if board_rows is None:
                    board_rows = json.loads((root / "docs/n500.json").read_text(encoding="utf-8")).get("rows", [])
                closes = {s: o["c"] for s, o in data.items() if len(o.get("c", [])) >= 300}
                out["pairs"] = pairs_retest(_groups(closes, board_rows), engle_granger)
            except Exception as e:
                notes.append(f"pairs failed: {str(e)[:120]}")
        else:
            notes.append("pairs: skipped, needs arch.")
        tm["pairs"] = time.time() - t
        full_asof = out["asof"]
    else:
        for k in ("signals", "track", "pairs"):
            out[k] = prev.get(k) or {}
        full_asof = next((n[len(FULL_NOTE):].split(" ")[0] for n in prev.get("notes") or [] if n.startswith(FULL_NOTE)), "none")
    notes.append(f"{FULL_NOTE}{full_asof} (signals, track and pairs re-run on Saturdays or with --full).")
    notes += ["Units (fractions, 0.02 = 2%): vol d1 and d5 are one standard deviation of the 1- and 5-day move, ann "
              "the same for a year; VaR is the one-day loss not exceeded on 95% / 99% of days; conformal by_sym is the 21-session return range "
              "(fraction) that held 90% of the time out of sample; signal and track numbers are mean 10-day / 21-day "
              "excess returns over the Nifty 50.",
              "Tags: tested, cointegrated and n are exact counts; every other number is an estimate from a model.",
              "Joint signal test asks 'does this signal beat zero excess return after allowing for testing all "
              "signals at once'; warning signals (expected to lag) are tested the same way and so do not survive."]
    (root / "docs/risklab.json").write_text(json.dumps(out, separators=(",", ":")), encoding="utf-8")
    tim = ", ".join(f"{k} {v:.1f}s" for k, v in tm.items())
    surv = [k for k, v in out["signals"].items() if v.get("survives")]
    return (f"risklab: vol {len(out['vol'])} ({fb} EWMA), VaR {len(out['var'])}, conformal coverage "
            f"{out['conformal'].get('coverage_measured')} vs {CONF}, signals surviving {len(surv)}"
            f"{' (full)' if full else ''}; {tim}")
