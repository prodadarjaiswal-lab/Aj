"""Formula lab: search for a short, readable formula that predicts a stock's 10-day excess return over the Nifty.

Two halves:
  * write_sample(): called nightly by tech_model.py on the Dhan history it already holds. Writes
    data/formula-sample.csv, about 20,000 (stock, day) rows sampled evenly over time and stocks:
    the desk's indicator readouts that day and y = 10-session forward return minus the Nifty's (percent).
  * run(): weekly (quant-lab.yml). Splits the table by date (first 70% train, last 30% test, 10-session gap),
    lets PySR search for a formula on the train rows, scores every formula on the Pareto front on the test
    rows, and compares the chosen one with the desk's score. Writes docs/formula.json.

The formula is shown as evidence only. It NEVER replaces the live score automatically.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import math
import random
import sys
from pathlib import Path

import numpy as np

HORIZON = 10          # sessions ahead for y
GAP = 10              # sessions between the last train date and the first test date
FEATURES = ["rsi", "adx", "st", "macd", "vs50", "vs200", "hi52", "rs3", "volx", "atr_pct", "mkt"]
WARN = {"extended", "downtrend"}


# ---------------------------------------------------------------- nightly: write the training table

def sample_rows(data: dict, nifty: dict, signals: dict | None = None, n: int = 20000, seed: int = 7) -> list[dict]:
    """About n rows spread evenly over each stock's history; only rows whose 10-session future is known."""
    import tech_model as M
    from setups import rolling_mean
    nmap = dict(zip(nifty["d"], nifty["c"]))
    nm200 = dict(zip(nifty["d"], rolling_mean(nifty["c"], 200)))
    signals = signals or {}
    ok = {s: {k for k, v in signals.items() if v.get(f) and k not in WARN} for s, f in ((1, "tested"), (0, "tested_weak"))}
    bad_sig = {s: {k for k, v in signals.items() if v.get(f) and k in WARN} for s, f in ((1, "tested"), (0, "tested_weak"))}
    syms = [s for s in sorted(data) if sum(d in nmap for d in data[s]["d"]) >= 252 + HORIZON + 5]
    per = math.ceil(n / max(1, len(syms)))
    rows = []
    for sym in syms:
        o = data[sym]
        keep = [i for i, d in enumerate(o["d"]) if d in nmap]
        d = [o["d"][i] for i in keep]
        cols = {k: [o[k][i] for i in keep] for k in ("o", "h", "l", "c")}
        v = [o["v"][i] for i in keep] if o.get("v") else None
        nc = [nmap[x] for x in d]
        c = cols["c"]
        T = M.Tech(cols["o"], cols["h"], cols["l"], c, v, nc)
        bad = [k for k in range(1, len(c)) if c[k - 1] and abs(c[k] / c[k - 1] - 1) > 0.40]   # splits / bad ticks
        lo, hi = 252, len(c) - 1 - HORIZON                 # hi: last index whose y is known
        if hi < lo:
            continue
        rng = random.Random(f"{seed}:{sym}")
        step = (hi - lo + 1) / per
        for j in range(per):                               # one random day inside each equal slice of history
            i = lo + int(j * step + rng.random() * step)
            if i > hi or i + HORIZON > len(c) - 1:
                continue
            if any(i - 10 <= k <= i + HORIZON for k in bad):
                continue
            r = M.readout(T, i)
            mkt = 1 if nm200.get(d[i]) is not None and nc[i] > nm200[d[i]] else 0
            row = {"date": d[i], "rsi": r.get("rsi"), "adx": r.get("adx"), "st": 1 if r.get("st") == "up" else 0,
                   "macd": 1 if r.get("macd") == "above signal" else 0, "vs50": r.get("vs50"), "vs200": r.get("vs200"),
                   "hi52": r.get("hi52"), "rs3": r.get("rs3"), "volx": r.get("volx"), "atr_pct": r.get("atr_pct"), "mkt": mkt}
            if signals:                                    # technical part of research.py's score: +2 per tested signal
                new = T.flags(i) & set().union(*(T.flags(k) - T.flags(k - 1) for k in range(i - 2, i + 1)))
                row["score"] = 2 * len(new & ok[mkt]) - 2 * len(new & bad_sig[mkt])
            row["y"] = round(((c[i + HORIZON] / c[i] - 1) - (nc[i + HORIZON] / nc[i] - 1)) * 100, 3)
            rows.append(row)
    if len(rows) > n:
        rows = random.Random(seed).sample(rows, n)
    rows.sort(key=lambda x: x["date"])
    return rows


def write_sample(data: dict, nifty: dict, root: Path, signals: dict | None = None, n: int = 20000, seed: int = 7) -> str:
    rows = sample_rows(data, nifty, signals, n, seed)
    cols = ["date"] + FEATURES + (["score"] if signals else []) + ["y"]
    p = Path(root) / "data/formula-sample.csv"
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows({k: ("" if r.get(k) is None else r[k]) for k in cols} for r in rows)
    return f"formula sample: {len(rows)} rows, {p.stat().st_size // 1024} KB"


# ---------------------------------------------------------------- weekly: search and test

def load(path: Path):
    """dates (list), X (rows x features), y, score (or None). Rows with a missing readout or y are dropped."""
    with Path(path).open(encoding="utf-8") as fh:
        rd = list(csv.DictReader(fh))
    has_score = bool(rd) and "score" in rd[0]
    num = lambda s: float(s) if s not in ("", None) else math.nan
    dates, X, y, sc = [], [], [], []
    for r in rd:
        xs = [num(r.get(f)) for f in FEATURES]
        yy = num(r.get("y"))
        if math.isnan(yy) or any(math.isnan(x) for x in xs):
            continue
        dates.append(r["date"])
        X.append(xs)
        y.append(yy)
        sc.append(num(r.get("score")) if has_score else math.nan)
    o = sorted(range(len(dates)), key=lambda i: dates[i])
    sc = np.array([sc[i] for i in o]) if has_score else None
    return [dates[i] for i in o], np.array([X[i] for i in o]).reshape(-1, len(FEATURES)), np.array([y[i] for i in o]), sc


def split_by_date(dates: list, train_frac: float = 0.7, gap: int = GAP):
    """Masks: train = first 70% of distinct dates, test = dates after a gap of `gap` sessions. No date in both."""
    u = sorted(set(dates))
    cut = int(len(u) * train_frac)
    train_d, test_d = set(u[:cut]), set(u[cut + gap:])
    d = np.array(dates)
    return np.isin(d, list(train_d)), np.isin(d, list(test_d))


def evaluate(pred, y, dates, top: float = 0.2, seed: int = 7) -> dict:
    """Each day: rank rows by pred, take the top fifth. Excess of a pick = its y minus that day's average y.
    t = t-statistic of those excesses; hit = share of picks beating the day's average."""
    pred, y = np.asarray(pred, float), np.asarray(y, float)
    rng = np.random.default_rng(seed)
    by = {}
    for i, d in enumerate(dates):
        by.setdefault(d, []).append(i)
    ex = []
    for d, idx in by.items():
        idx = np.array(idx)
        idx = idx[np.isfinite(pred[idx])]
        if len(idx) < 5 or np.ptp(pred[idx]) == 0:        # a day needs at least 5 rows and some spread to rank
            continue
        idx = idx[rng.permutation(len(idx))]               # ties broken at random, not by row order
        k = max(1, int(round(len(idx) * top)))
        pick = idx[np.argsort(-pred[idx], kind="stable")[:k]]
        ex.extend(y[pick] - y[idx].mean())
    ex = np.array(ex)
    if len(ex) < 2 or ex.std(ddof=1) == 0:
        return {"n": int(len(ex)), "mean": None, "t": 0.0, "hit": None}
    return {"n": int(len(ex)), "mean": round(float(ex.mean()), 3),
            "t": round(float(ex.mean() / (ex.std(ddof=1) / math.sqrt(len(ex)))), 2), "hit": round(float((ex > 0).mean()), 3)}


def choose(results: list) -> int:
    """Index of the simplest equation whose test t is within 10% of the best test t."""
    best = max(r["t"] for r in results)
    ok = [i for i, r in enumerate(results) if r["t"] >= best - 0.1 * abs(best)]
    return min(ok, key=lambda i: (results[i]["complexity"], -results[i]["t"]))


def verdict(t_chosen: float, t_base: float | None) -> str:
    if t_chosen >= 2 and t_chosen > (t_base if t_base is not None else -math.inf):
        return "beats_score"
    return "no_better" if t_chosen > 0 else "failed"


def baseline(Xtr, ytr, dtr, Xte, yte, dte, score_tr=None, score_te=None) -> dict:
    """The desk's score if the table has one with spread in the test period; else the single readout
    (either sign) that ranked best on the TRAIN period."""
    if score_te is not None and np.isfinite(score_te).any() and np.nanstd(score_te) > 0:
        e = evaluate(score_te, yte, dte)
        return {"name": "score", "t_oos": e["t"], "hit_oos": e["hit"]}
    best = None
    for j, f in enumerate(FEATURES):
        for sgn in (1, -1):
            t = evaluate(sgn * Xtr[:, j], ytr, dtr)["t"]
            if best is None or t > best[0]:
                best = (t, j, sgn)
    _, j, sgn = best
    e = evaluate(sgn * Xte[:, j], yte, dte)
    return {"name": ("" if sgn > 0 else "-") + FEATURES[j], "t_oos": e["t"], "hit_oos": e["hit"]}


def search(X, y, names, minutes: float = 20, seed: int = 7) -> list:
    """PySR search. Returns the Pareto front: [{complexity, loss, equation, latex, predict(X)}]."""
    from pysr import PySRRegressor
    m = PySRRegressor(binary_operators=["+", "-", "*", "/"], unary_operators=[], maxsize=15,
                      niterations=100000, timeout_in_seconds=int(minutes * 60),
                      elementwise_loss="L1DistLoss()",              # MAE: 10-day returns are heavy-tailed
                      random_state=seed, deterministic=True, parallelism="serial",
                      temp_equation_file=True, progress=False, verbosity=0, input_stream="devnull")
    m.fit(X, y, variable_names=list(names))
    eq = m.equations_
    out = []
    for i in range(len(eq)):
        try:
            lx = m.latex(i)
        except Exception:
            lx = ""
        out.append({"complexity": int(eq["complexity"].iloc[i]), "loss": float(eq["loss"].iloc[i]),
                    "equation": str(eq["equation"].iloc[i]), "latex": lx,
                    "predict": (lambda Z, i=i: m.predict(Z, index=i))})
    return out


def run(root: Path, minutes: float = 20, seed: int = 7, search_fn=search, max_train: int = 5000) -> dict:
    root = Path(root)
    dates, X, y, score = load(root / "data/formula-sample.csv")
    tr, te = split_by_date(dates)
    dtr, dte = [d for d, k in zip(dates, tr) if k], [d for d, k in zip(dates, te) if k]
    Xtr, ytr, Xte, yte = X[tr], y[tr], X[te], y[te]
    idx = np.arange(len(ytr))
    if len(idx) > max_train:                                 # even subsample of the train period, fixed seed
        idx = np.sort(np.random.default_rng(seed).choice(idx, max_train, replace=False))
    front = search_fn(Xtr[idx], ytr[idx], FEATURES, minutes, seed)
    res = []
    for e in front:
        p = np.asarray(e["predict"](Xte), float)
        res.append({**e, **evaluate(p, yte, dte)})
    k = choose(res)
    base = baseline(Xtr, ytr, dtr, Xte, yte, dte, score[tr] if score is not None else None,
                    score[te] if score is not None else None)
    ch = res[k]
    out = {"asof": dates[-1] if dates else dt.date.today().isoformat(), "rows_train": int(len(ytr)), "rows_test": int(len(yte)),
           "features": FEATURES,
           "front": [{"complexity": r["complexity"], "loss": round(r["loss"], 4), "equation": r["equation"]} for r in res],
           "chosen": {"equation": ch["equation"], "latex": ch.get("latex", ""), "t_oos": ch["t"], "hit_oos": ch["hit"]},
           "baseline": base, "verdict": verdict(ch["t"], base["t_oos"])}
    (root / "docs").mkdir(exist_ok=True)
    (root / "docs/formula.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Weekly formula search on data/formula-sample.csv")
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[2]))
    ap.add_argument("--minutes", type=float, default=20)
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args()
    if not (Path(a.root) / "data/formula-sample.csv").exists():
        print("no data/formula-sample.csv yet (tech_model.py writes it nightly); nothing to do")
        return 0
    o = run(Path(a.root), a.minutes, a.seed)
    print(f"formula: {o['chosen']['equation']}  t_oos={o['chosen']['t_oos']}  baseline {o['baseline']['name']} "
          f"t_oos={o['baseline']['t_oos']}  verdict={o['verdict']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
