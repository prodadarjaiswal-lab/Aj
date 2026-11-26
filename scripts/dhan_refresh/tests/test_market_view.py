import datetime as dt
import random

import market_view as MV


def _series(n, seed, drift=0.0003, start=dt.date(2014, 1, 1)):
    rnd, p, d, c = random.Random(seed), 100.0, [], []
    day = start
    while len(d) < n:
        day += dt.timedelta(days=1)
        if day.weekday() >= 5:
            continue
        p *= 1 + drift + rnd.gauss(0, 0.01)
        d.append(day.isoformat())
        c.append(p)
    return {"d": d, "c": c}


def _data():
    names = ["Nifty 50", "Nifty Bank", "Nifty IT", "Nifty FMCG", "Nifty Pharma", "Nifty Metal", "India VIX"]
    series = {k: _series(2600, 10 + i) for i, k in enumerate(names)}
    cap = {"BSE": _series(1500, 50), "MCX": _series(2600, 51)}
    cap["BSE"]["d"] = series["Nifty 50"]["d"][-1500:]
    return series, cap


def test_regimes_classify():
    up = [100 * 1.002 ** i for i in range(300)]
    assert MV.regimes(up)[-1] == "rising"
    down = [100 * 0.998 ** i for i in range(300)]
    assert MV.regimes(down)[-1] == "falling"
    flat = [100 + (i % 2) * 0.1 for i in range(300)]
    assert MV.regimes(flat)[-1] == "flat"
    assert MV.regimes(up)[50] is None


def test_monthly_clusters_and_holm():
    cases = [(f"2020-{m:02d}-0{d}", 0.01 + 0.001 * d) for m in range(1, 13) for d in range(1, 4)]
    s = MV.monthly(cases)
    assert s["months"] == 12 and s["n"] == 36 and s["hit"] == 1.0
    res = [{"oos": {"p": 0.001}}, {"oos": {"p": 0.04}}, {"oos": {"p": None}}]
    MV.holm(res)
    assert [r["pass_holm"] for r in res] == [True, True, False]
    res = [{"oos": {"p": 0.03}}, {"oos": {"p": 0.04}}]
    MV.holm(res)
    assert [r["pass_holm"] for r in res] == [False, False]


def test_verdict_rules():
    good = {"is": {"mean": 0.01, "t": 2.5, "months": 50}, "oos": {"mean": 0.01, "t": 3, "months": 36}, "pass_holm": True}
    assert MV.verdict(good) == "HOLDS"
    assert MV.verdict(good | {"oos": {"mean": -0.01, "t": -1, "months": 36}}) == "FAILS"
    assert MV.verdict(good | {"pass_holm": False}) == "UNPROVEN"
    assert MV.verdict(good | {"oos": {"mean": 0.01, "t": 3, "months": 5}}) == "UNPROVEN"


def test_build_on_random_data_finds_nothing_and_reports():
    series, cap = _data()
    v = MV.build(series, cap)
    assert v["regime"] in MV.REGIMES
    keys = {b["key"] for b in v["beliefs"]}
    assert {"bank_flat", "bank_always", "bank_leads", "capmkt_flat", "nifty_bounce", "sector_reversal",
            "sector_momentum", "laggard_catchup"} <= keys
    # pure noise: nothing should survive the many-ideas test
    assert all(b["verdict"] != "HOLDS" for b in v["beliefs"])
    assert v["rotation"]["stats"]["n"] > 20
    assert 0 <= v["next_day"]["accuracy"] <= 1
    md = MV.markdown(v)
    assert "Market type today" in md and "Bank Nifty" in md


def test_walk_rotation_uses_only_past():
    series, _ = _data()
    days, X = MV.align(series)
    reg = MV.regimes(X["Nifty 50"])
    rot = MV.walk_rotation(days, X, reg)
    # tamper with prices after the first forecast's window: its pick must not change
    i0 = days.index(rot["start"])
    X2 = {k: v[:i0 + MV.H + 1] + [x * 3 if x else x for x in v[i0 + MV.H + 1:]] for k, v in X.items()}
    b = MV.walk_rotation(days, X2, reg)
    assert b["record"][0] == rot["record"][0]
