import datetime as dt
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import gold_desk as G  # noqa: E402


def _fake(n=700, drift=0.0004):
    d0 = dt.date(2023, 1, 2)
    days = [d0 + dt.timedelta(days=i) for i in range(n * 7 // 5 + 10) if (d0 + dt.timedelta(days=i)).weekday() < 5][:n]
    c = 100 * np.exp(np.cumsum(np.full(n, drift)))
    return days, c


def test_verdict_thresholds():
    assert G.verdict([("a", True), ("b", True), ("c", True), ("d", False)]) == "Good to buy"
    assert G.verdict([("a", True), ("b", False), ("c", False), ("d", False)]) == "Avoid"
    assert G.verdict([("a", True), ("b", True), ("c", False), ("d", False)]) == "Wait"
    assert G.verdict([("a", True), ("b", None), ("c", None)]) == "Not enough data"


def test_merge_keeps_old_mcx_and_contract():
    old = {"bees": {"2026-01-01": 1}, "mcx": {"2026-01-01": 10}, "mcx_contract": {"2026-01-01": "OLD"}}
    m = G.merge(old, {"bees": {"2026-01-02": 2}, "nifty": {}, "mcx": {"2026-01-02": 11}, "mcx_contract": "NEW"})
    assert m["mcx"] == {"2026-01-01": 10, "2026-01-02": 11}
    assert m["mcx_contract"] == {"2026-01-01": "OLD", "2026-01-02": "NEW"}
    assert m["bees"] == {"2026-01-01": 1, "2026-01-02": 2}


def test_level_check_and_build_on_steady_uptrend():
    days, c = _fake()
    bees = {d.isoformat(): float(v) for d, v in zip(days, c)}
    w = [[d.isoformat(), None, float(v) * 1200, None, None] for d, v in zip(days, c) if d.weekday() == 4]
    hist = {"w": w}
    mcx = {k: v * 1200 for k, v in list(bees.items())[-100:]}
    L = G.level_check(mcx, bees, w)
    assert abs(L["k"] - 1200) < 1e-6 and L["ok"] and L["days"] == 60
    out = G.build(hist, {"bees": bees, "mcx": mcx, "nifty": {k: 1.0 for k in bees}}, "x")
    assert abs(out["level"]["prem"]) < 1e-6 and abs(out["mcx"]["gap"]) < 1e-6
    assert [h["v"] for h in out["horizons"]] == ["Good to buy"] * 3  # RSI 100 fails, 4 of 5 still pass on 3 months
    assert out["proof"]["1 year"]["all"]["up"] == 1.0
    assert out["f"]["vs200"] > 0 and out["f"]["cross"] > 0


def test_sma_and_rsi():
    a = np.arange(1.0, 31.0)
    assert G.sma(a, 5)[-1] == 28.0
    assert G.rsi(a)[-1] == 100


def test_trend_gauge_up_then_down():
    import datetime as dt
    d0 = dt.date(2005, 1, 7)
    px = [100 * 1.003 ** i for i in range(400)] + [100 * 1.003 ** 399 * 0.99 ** i for i in range(1, 60)]
    rows = [[(d0 + dt.timedelta(weeks=i)).isoformat(), p] for i, p in enumerate(px)]
    T = G.trend_gauge(rows)
    assert T["now"] == "below" and T["dist"] < 0
    assert T["rule"]["maxdd"] > T["hold"]["maxdd"]  # the rule side-steps part of the fall


def test_risk_stats_shapes():
    c = np.array([100 * 1.0004 ** i * (1 + 0.01 * np.sin(i / 7)) for i in range(900)])
    R = G.risk_stats(c, None)
    assert [r["lab"] for r in R] == ["1 year", "3 years", "Since 2009"]
    assert all(r["mdd"] <= 0 and r["var95"] < 0 and r["cvar95"] <= r["var95"] for r in R)
