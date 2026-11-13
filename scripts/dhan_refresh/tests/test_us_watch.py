import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import us_watch as U  # noqa: E402

CFG = {"NVDA": {"name": "Nvidia", "below": [150, 135], "above": [180], "move_pct": 3, "why": {"150": "Buy level"}}}


def q(p, prev=166.19):
    return {"price": p, "prev": prev, "high": max(p, prev), "low": min(p, prev), "t": 0}


def test_parse_yahoo():
    d = {"chart": {"result": [{"meta": {"regularMarketPrice": 161.88, "chartPreviousClose": 166.19,
                                          "regularMarketDayHigh": 170, "regularMarketDayLow": 158.39, "regularMarketTime": 1794595674}}]}}
    assert U.parse_yahoo(d) == {"price": 161.88, "prev": 166.19, "high": 170.0, "low": 158.39, "t": 1794595674}


def test_levels_and_moves_fire_once():
    w = U.Watch(CFG)
    assert w.check("NVDA", q(162), "x") == []                 # -2.5%: nothing
    m = w.check("NVDA", q(160), "x")
    assert len(m) == 1 and "-3.7%" in m[0]                    # first 3% step
    m = w.check("NVDA", q(149), "x")
    assert any("$150" in x and "Buy level" in x for x in m) and any("-10.3%" in x for x in m)
    assert w.check("NVDA", q(149.5), "x") == []               # no repeats
    m = U.Watch(CFG).check("NVDA", q(181, 175), "x")
    assert any("$180" in x for x in m)


def test_restart_keeps_sent():
    w = U.Watch(CFG, ["NVDA:below:150", "NVDA:move:-9"])
    assert w.check("NVDA", q(149), "x") == []


def test_config_file_is_valid():
    c = U.config()
    assert "NVDA" in c and all(isinstance(x, (int, float)) for x in c["NVDA"]["below"])
