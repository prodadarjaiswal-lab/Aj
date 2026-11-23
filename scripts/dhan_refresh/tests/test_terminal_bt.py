import datetime as dt
import math
import random

import terminal_bt as TB


def _rows(base, drift=0.0, seed=0):
    rnd = random.Random(seed)
    rows, p = [], base
    for m in range(9 * 60 + 15, 15 * 60 + 30, 5):
        o = p
        p = p * (1 + drift + rnd.uniform(-0.002, 0.002))
        rows.append((m, o, max(o, p) * 1.001, min(o, p) * 0.999, p, 1000))
    return rows


def test_bar_at_and_close():
    rows = _rows(100)
    i = TB.bar_at(rows, 9 * 60 + 25)
    assert rows[i][0] == 9 * 60 + 25
    assert TB.close_at(rows) == rows[TB.bar_at(rows, TB.LAST_BAR)][4]


def test_plan_exit_stop_first():
    rows = [(555, 100, 100, 100, 100, 1), (560, 100, 102, 98, 100, 1)]
    px, why = TB.plan_exit(rows, 0, 2.0)          # stop 99, target 102: both touched -> stop
    assert why == "stop" and px == 99


def test_features_no_lookahead():
    rows = _rows(100, 0.001)
    i = TB.bar_at(rows, 12 * 60 + 25)
    f1 = TB.features(rows, i, 99.0, 0.0, 2.0)
    f2 = TB.features(rows[:i + 1], i, 99.0, 0.0, 2.0)
    assert f1 == f2 and f1["up_open"] and f1["rs"] and f1["volx"]


def test_summarize_pass_rule():
    days = [f"2026-10-{d:02d}" for d in range(1, 23)]
    xs = [(0.004 + (k % 3) * 0.001, 0.005, days[k % 22]) for k in range(60)]
    s = TB.summarize(xs, days)
    assert s["n"] == 60 and s["pass"] and s["h1"] > 0 and s["h2"] > 0
    assert TB.summarize([], days) == {"n": 0}


def test_backtest_runs_on_synthetic_data():
    start = dt.date(2024, 1, 1)
    ds = [(start + dt.timedelta(days=k)).isoformat() for k in range(700) if (start + dt.timedelta(days=k)).weekday() < 5]
    c = [100 * (1.0006 ** k) * (1 + 0.01 * math.sin(k / 5)) for k in range(len(ds))]
    daily = {"AAA": {"d": ds, "o": c, "h": [x * 1.01 for x in c], "l": [x * 0.99 for x in c], "c": c, "v": [1e6] * len(ds)}}
    nifty_d = {"d": ds, "c": [100 * (1.0003 ** k) for k in range(len(ds))]}
    last = ds[-25:]
    intra = {"AAA": {d: _rows(c[ds.index(d)], 0.0002, k) for k, d in enumerate(last)}}
    nifty_i = {d: _rows(100, 0.0, k + 99) for k, d in enumerate(last)}
    res = TB.backtest(daily, intra, nifty_d, nifty_i, {"trend", "don55", "brk20", "flag", "nr7"}, {"capital": 100000, "max_loss_per_trade": 1000})
    assert len(res["days"]) == 22
    assert res["grid"]["all"]["09:30"]["any"]["day"]["n"] > 0
    assert set(res["equity"]) == set(TB.CHECKS)
