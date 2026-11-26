import json

import market_view as MV
import weekly_view as WV
from tests.test_market_view import _data, _series


def test_weekly_bars_take_each_weeks_last_close():
    s = _series(30, 1)
    days, X = WV.weekly(s["d"], {"x": s["c"]})
    assert len(days) in (6, 7)
    for d, c in zip(days, X["x"]):
        assert c == s["c"][s["d"].index(d)]


def test_weekly_build_on_random_data_finds_nothing():
    series, cap = _data()
    series["India VIX"]["c"] = [16 + (x % 1) for x in series["India VIX"]["c"]]   # fair for 1% daily moves
    w = WV.build(series, cap, years=8)
    keys = {o["key"] for o in w["results"]}
    assert {"bank_flat", "pair_revert", "nifty_condor", "trend40:Nifty 50", "fear_buy:Nifty 50"} <= keys
    assert w["held"] == []
    assert w["from"] >= series["Nifty 50"]["d"][0]
    v = MV.build(series, cap)
    w["compare"] = WV.compare(w, v)
    assert any(c["daily"] for c in w["compare"])
    json.dumps(w)
    assert "Weekly re-test" in WV.markdown(w)


def test_weekly_trend_rule_follows_the_average():
    up = [100 * 1.01 ** i for i in range(60)]
    assert WV.positions("trend40", up, None)[-1] == 1
    down = [100 * 0.99 ** i for i in range(60)]
    assert WV.positions("trend40", down, None)[-1] == 0
