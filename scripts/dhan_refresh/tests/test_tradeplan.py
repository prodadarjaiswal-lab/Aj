import json
import math
import shutil
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import tradeplan as TP  # noqa: E402

REPO = Path(__file__).resolve().parents[3]
CFG = json.loads((REPO / "config/trading.json").read_text(encoding="utf-8"))


def intraday():
    return TP.rates({**CFG, "product": "intraday"})


def series(n=600, start=1000.0, seed=1, drift=0.0005, sd=0.015):
    rng = np.random.default_rng(seed)
    c = start * np.exp(np.cumsum(rng.normal(drift, sd, n)))
    return [round(float(x), 2) for x in c]


def test_snap_to_tick():
    assert TP.snap(1003.37, 5, "down") == 1000.0
    assert TP.snap(1003.37, 5, "up") == 1005.0
    assert TP.snap(1003.37, 5) == 1005.0
    assert TP.snap(99.99, 0.05, "down") == 99.95
    assert TP.snap(100.0, 0.05, "down") == 100.0          # an exact tick is kept, not pushed down
    assert TP.tick_for(1000.0) == 1                      # auction.tick_for: ~0.1% of price


def test_charges_hand_checked_intraday():
    # 100 shares bought at 1,000 and sold at 1,010, Groww intraday rates from the nse-day-trader skill:
    # brokerage 20 + 20 = 40; STT 0.025% x 101,000 = 25.25; NSE 0.00297% x 201,000 = 5.9697;
    # SEBI 0.201; IPFT 0.201; stamp 0.003% x 100,000 = 3.00; GST 18% x (40 + 5.9697 + 0.201 + 0.201) = 8.3469
    got = TP.charges(100000, 101000, intraday())
    assert got == pytest.approx(82.9686, abs=0.001)


def test_charges_small_order_uses_pct_and_min():
    r = intraday()
    # 0.1% of 3,000 = 3 < min 5, so brokerage is 5 per side
    assert TP.charges(3000, 3000, r) - TP.charges(3000, 3000, {**r, "brokerage_pct": 0}) == pytest.approx(10 * 1.18)


def test_size_caps():
    cfg = {"capital": 100000, "max_loss_per_trade": 1000}
    assert TP.size(100, 98, cfg, 1.0) == (500, "max loss per trade")
    q, by = TP.size(1000, 990, cfg, 0.10)                 # loss allows 100, cap allows 10
    assert q == 10 and by.startswith("position cap")
    assert TP.size(1000, 999.5, cfg, 5.0) == (100, "capital")
    assert TP.size(100, 100, cfg, 1.0)[0] == 0           # no stop distance, no shares


def test_odds_fall_when_stop_tightened():
    c = series()
    r = TP.rates(CFG)
    wide = TP.simulate(c, 1000, 940, 1060, 10, 0.0, 21, r, n=4000)
    tight = TP.simulate(c, 1000, 985, 1060, 10, 0.0, 21, r, n=4000)
    for s in (wide, tight):
        assert 0 < s["p_target"] < 1 and 0 < s["p_stop"] < 1
    assert tight["p_target"] < wide["p_target"]
    assert tight["p_stop"] > wide["p_stop"]


def _root(tmp_path, today, signals, feeds=None, risklab=None):
    (tmp_path / "config").mkdir()
    (tmp_path / "docs").mkdir()
    shutil.copy(REPO / "config/trading.json", tmp_path / "config/trading.json")
    (tmp_path / "config/portfolio.json").write_text(json.dumps({"stock_cap": 0.10, "min_traded_cr": 1.0}))
    (tmp_path / "docs/tech-model.json").write_text(json.dumps({"signals": signals}))
    (tmp_path / "docs/tech-today.json").write_text(json.dumps({"asof": "2026-11-13", "stocks": today}))
    (tmp_path / "docs/nse-feeds.json").write_text(json.dumps(feeds or {"events": {}}))
    if risklab is not None:
        (tmp_path / "docs/risklab.json").write_text(json.dumps(risklab))
    return tmp_path


SIG = {"flag": {"tested": True, "tested_weak": False,
                "out": {"up": {"n": 2000, "x21": 0.06, "hit21": 0.56}, "weak": {"n": 1500, "x21": 0.004}}},
       "trend": {"tested": False, "out": {"up": {"n": 900, "x21": 0.01}}}}


def test_run_writes_plans_and_failing_checks(tmp_path):
    c = series()
    data = {"AAA": {"c": c, "v": [200000] * len(c)},          # ~Rs 20+ Cr a day
            "BBB": {"c": c, "v": [10] * len(c)},              # thin: turnover check fails
            "CCC": {"c": c, "v": [200000] * len(c)}}          # untested signal only
    today = {s: {"c": c[-1], "atr": 0.02 * c[-1], "new": ["flag"]} for s in ("AAA", "BBB")}
    today["CCC"] = {"c": c[-1], "atr": 20.0, "new": ["trend"]}
    nifty = {"c": [100 + i * 0.1 for i in range(300)]}            # above its 200-day average: rising
    feeds = {"events": {"AAA": [{"d": "2026-11-20", "p": "Financial Results"}]}}
    root = _root(tmp_path, today, SIG, feeds)
    msg = TP.run(data, nifty, root)
    assert "vol from ATR" in msg
    out = json.loads((root / "docs/tradeplan.json").read_text())
    assert set(out) == {"asof", "config_assumed", "charges", "plans"}
    assert out["config_assumed"] is True
    assert set(out["plans"]) == {"AAA", "BBB"}
    p = out["plans"]["AAA"]
    assert set(p) == {"signal", "entry", "stop", "target", "rr", "tick", "vol_src", "p_target", "p_stop", "exp_net_rs",
                      "charges_rs", "qty", "risk_rs", "checks", "event", "basis"}
    assert p["vol_src"] == "ATR 14" and p["signal"] == "flag"
    assert p["stop"] < p["entry"] < p["target"]
    for k in ("entry", "stop", "target"):
        assert abs(p[k] / p["tick"] - round(p[k] / p["tick"])) < 1e-6
    assert p["qty"] == math.floor(min(1000 / (p["entry"] - p["stop"]), 0.10 * 100000 / p["entry"], 100000 / p["entry"]))
    ck = {x["rule"]: x for x in p["checks"]}
    assert len(ck) >= 6
    assert ck["no results or board meeting while held"]["ok"] is False and p["event"]["d"] == "2026-11-20"
    assert ck["turnover"]["ok"] is True
    assert {x["rule"]: x for x in out["plans"]["BBB"]["checks"]}["turnover"]["ok"] is False


def test_risklab_vol_used_when_present(tmp_path):
    c = series()
    data = {"AAA": {"c": c, "v": [200000] * len(c)}}
    today = {"AAA": {"c": c[-1], "atr": 0.02 * c[-1], "new": ["flag"]}}
    root = _root(tmp_path, today, SIG, risklab={"vol": {"AAA": {"d1": 0.01}}})
    TP.run(data, {"c": [100.0] * 10}, root)
    p = json.loads((root / "docs/tradeplan.json").read_text())["plans"]["AAA"]
    assert p["vol_src"] == "risklab daily vol"
    assert p["entry"] - p["stop"] == pytest.approx(1.5 * 0.01 * p["entry"], abs=p["tick"] + 0.01)


def test_weak_market_uses_weak_flag(tmp_path):
    c = series()
    data = {"AAA": {"c": c, "v": [200000] * len(c)}}
    today = {"AAA": {"c": c[-1], "atr": 20.0, "new": ["flag"]}}
    root = _root(tmp_path, today, SIG)
    TP.run(data, {"c": [300 - i * 0.5 for i in range(300)]}, root)      # falling: below its 200-day average
    assert json.loads((root / "docs/tradeplan.json").read_text())["plans"] == {}
