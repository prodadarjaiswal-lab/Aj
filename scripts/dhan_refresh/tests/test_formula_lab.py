import csv
import datetime as dt
import json
import random
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import formula_lab as F  # noqa: E402


def _days(n):
    return [(dt.date(2020, 1, 1) + dt.timedelta(days=i)).isoformat() for i in range(n)]


def _table(n_days=300, per_day=20, seed=1):
    """y = 0.5*x0 - x1 + noise; x0 is the rsi column, x1 the adx column."""
    rng = np.random.default_rng(seed)
    dates = [d for d in _days(n_days) for _ in range(per_day)]
    X = rng.normal(size=(len(dates), len(F.FEATURES)))
    y = 0.5 * X[:, 0] - X[:, 1] + rng.normal(scale=1.0, size=len(dates))
    return dates, X, y


def test_split_by_date_has_no_overlap_and_keeps_the_gap():
    dates = [d for d in _days(200) for _ in range(3)]
    tr, te = F.split_by_date(dates)
    dtr, dte = sorted({d for d, k in zip(dates, tr) if k}), sorted({d for d, k in zip(dates, te) if k})
    assert not set(dtr) & set(dte)
    assert dtr[-1] < dte[0]
    u = sorted(set(dates))
    assert u.index(dte[0]) - u.index(dtr[-1]) - 1 == F.GAP
    assert len(dtr) == 140 and len(dte) == 200 - 140 - F.GAP


def test_evaluation_ranks_the_true_formula_above_noise():
    dates, X, y = _table()
    true = F.evaluate(0.5 * X[:, 0] - X[:, 1], y, dates)
    noise = F.evaluate(np.random.default_rng(9).normal(size=len(y)), y, dates)
    assert true["t"] > 5 and true["t"] > noise["t"] + 3
    assert true["hit"] > 0.6


def test_verdict_for_all_three_outcomes():
    assert F.verdict(2.5, 1.0) == "beats_score"
    assert F.verdict(2.5, 3.0) == "no_better"
    assert F.verdict(1.2, None) == "no_better"
    assert F.verdict(-0.4, -1.0) == "failed"
    assert F.verdict(0.0, None) == "failed"


def test_choose_takes_the_simplest_within_ten_percent():
    r = [{"complexity": 1, "t": 0.0}, {"complexity": 5, "t": 9.5}, {"complexity": 9, "t": 10.0}, {"complexity": 13, "t": 8.0}]
    assert F.choose(r) == 1


def _stub(Xtr, ytr, names, minutes, seed):
    """Stands in for PySR: a fixed equation table."""
    return [{"complexity": 1, "loss": 1.0, "equation": "0.01", "latex": "0.01", "predict": lambda Z: np.full(len(Z), 0.01)},
            {"complexity": 5, "loss": 0.8, "equation": "(rsi * 0.5) - adx", "latex": r"0.5 rsi - adx",
             "predict": lambda Z: 0.5 * Z[:, 0] - Z[:, 1]},
            {"complexity": 9, "loss": 0.79, "equation": "((rsi * 0.5) - adx) + (vs50 * 0.01)", "latex": "",
             "predict": lambda Z: 0.5 * Z[:, 0] - Z[:, 1] + 0.01 * Z[:, 4]}]


def test_run_with_stub_writes_the_contract(tmp_path):
    dates, X, y = _table()
    (tmp_path / "data").mkdir()
    with (tmp_path / "data/formula-sample.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["date"] + F.FEATURES + ["y"])
        for d, x, yy in zip(dates, X, y):
            w.writerow([d] + [round(v, 4) for v in x] + [round(yy, 4)])
    out = F.run(tmp_path, minutes=0.1, search_fn=_stub)
    j = json.loads((tmp_path / "docs/formula.json").read_text())
    assert set(j) == {"asof", "rows_train", "rows_test", "features", "front", "chosen", "baseline", "verdict"}
    assert set(j["chosen"]) == {"equation", "latex", "t_oos", "hit_oos"}
    assert set(j["baseline"]) == {"name", "t_oos", "hit_oos"}
    assert all(set(f) == {"complexity", "loss", "equation"} for f in j["front"])
    assert j["chosen"]["equation"] == "(rsi * 0.5) - adx"
    assert j["baseline"]["name"] in ("-adx", "rsi")           # no score column: best single readout on train
    assert j["verdict"] == "beats_score" and out["rows_train"] > out["rows_test"] > 0


def _walk(days, seed):
    rnd = random.Random(seed)
    c, o, h, l, v = [100.0], [], [], [], []
    for _ in days:
        p = c[-1]
        cl = p * (1 + rnd.gauss(0, 0.02))
        o.append(p)
        h.append(max(p, cl) * 1.005)
        l.append(min(p, cl) * 0.995)
        c.append(cl)
        v.append(rnd.randint(1000, 5000))
    return {"d": days, "o": o, "h": h, "l": l, "c": c[1:], "v": v}


def test_sample_writer_excludes_rows_without_y(tmp_path):
    days = _days(420)
    nifty = {"d": days, "c": _walk(days, 0)["c"]}
    data = {f"S{i}": _walk(days, i + 1) for i in range(4)}
    msg = F.write_sample(data, nifty, tmp_path, signals={"trend": {"tested": True}}, n=200)
    rows = list(csv.DictReader((tmp_path / "data/formula-sample.csv").open()))
    assert rows and "rows" in msg
    assert list(rows[0]) == ["date"] + F.FEATURES + ["score", "y"]
    assert all(r["y"] != "" for r in rows)
    assert max(r["date"] for r in rows) <= days[-1 - F.HORIZON]
    assert min(r["date"] for r in rows) >= days[252]
    assert len(rows) <= 200
    first = (tmp_path / "data/formula-sample.csv").read_text()      # same seed, same table
    F.write_sample(data, nifty, tmp_path, signals={"trend": {"tested": True}}, n=200)
    assert (tmp_path / "data/formula-sample.csv").read_text() == first
